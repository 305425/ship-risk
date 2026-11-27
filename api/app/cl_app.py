"""Chainlit chat for the fleet assistant.

Mounted on the API at /chat. Questions can name any vessel.
Sign in with any username. The password is the dashboard API key. The OpenAI
key is also accepted, so a direct visit to /chat still works.
"""

import os
import secrets
import shutil
import tempfile
from pathlib import Path

import chainlit as cl

from app.assistant import fleet_template, format_chat_answer, run_fleet
from app.chat_history import chainlit_database_url, chat_layer, ensure_chat_tables
from app.guardrails import injection_match
from app.config import get_settings
from app.rag import ai_status, get_store

os.environ.setdefault("CHAINLIT_AUTH_SECRET", secrets.token_hex(32))


def _same(left: str, right: str) -> bool:
    a, b = left.encode(), right.encode()
    if len(a) != len(b):
        return False
    return secrets.compare_digest(a, b)


def _passwords() -> list[str]:
    """Dashboard API key first, then the OpenAI key for a direct visit to /chat."""
    found = []
    for name in ("API_KEY", "OPENAI_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value and value not in found:
            found.append(value)
    return found


@cl.password_auth_callback
async def auth(username: str, password: str) -> cl.User | None:
    if not password or not any(_same(password, expected) for expected in _passwords()):
        return None
    return cl.User(identifier=(username or "chat-user").strip()[:100] or "chat-user")


@cl.set_starters
async def starters(user: cl.User | None, language: str | None = None):
    return [
        cl.Starter(label="High risk vessels", message="Which vessels are High risk, and what are their scores?"),
        cl.Starter(label="Overdue maintenance", message="How many overdue maintenance jobs are there, by vessel?"),
        cl.Starter(label="Open fire deficiencies", message="Which vessels have open fire safety deficiencies?"),
        cl.Starter(label="Detentions", message="Why were vessels detained?"),
    ]


def _thread_id() -> str:
    session = cl.context.session
    return getattr(session, "thread_id", None) or session.id


@cl.data_layer
def chat_data_layer():
    """Persist threads in the application Postgres so the sidebar can list them."""
    ensure_chat_tables()
    return chat_layer(chainlit_database_url(get_settings().database_url))


@cl.on_chat_resume
async def resume(thread):
    cl.user_session.set("thread_id", thread.get("id") or _thread_id())


def _ingest_elements(elements) -> str:
    """Add dropped reports to the evidence index. CSV files stay on the Data upload page."""
    csvs = []
    blocked = []
    documents = []
    for element in elements or []:
        name = Path(getattr(element, "name", "") or "file").name
        source = getattr(element, "path", None)
        if not source:
            continue
        if name.lower().endswith(".csv"):
            csvs.append(name)
            continue
        raw = Path(source).read_bytes()
        if injection_match(raw.decode("utf-8", errors="ignore")):
            blocked.append(name)
        else:
            documents.append((name, source))
    lines = []
    if csvs:
        lines.append("CSV files are loaded from Data upload, not from chat: " + ", ".join(csvs) + ".")
    if blocked:
        lines.append(
            "These files were not added because they try to change the assistant's instructions: "
            + ", ".join(blocked) + "."
        )
    if not documents:
        return "\n".join(lines) or "No file was attached."
    store = get_store()
    if store is None or store.rag is None:
        lines.append("The evidence index is not available, so the documents were not added.")
        return "\n".join(lines)
    with tempfile.TemporaryDirectory() as temporary:
        for name, source in documents:
            shutil.copyfile(source, Path(temporary) / name)
        stats = store.rag.ingest_directory(temporary)
    lines.append(
        f"Added {stats.get('processed', 0)} document(s) to the evidence index "
        f"({stats.get('chunks_created', 0)} sections). {stats.get('failed', 0)} could not be read."
    )
    return "\n".join(lines)


@cl.on_chat_start
async def start():
    cl.user_session.set("thread_id", _thread_id())
    status = ai_status()
    if status["enabled"]:
        await cl.Message(content="Ask about one vessel or the whole fleet. Follow-up questions stay in this chat. "
                                  "Scores and counts come from the database.").send()
    else:
        await cl.Message(content=f"The model is switched off ({status['reason']}).\n\n{fleet_template()}").send()


def _actor() -> str:
    user = cl.user_session.get("user")
    return getattr(user, "identifier", None) or "chat"


@cl.on_message
async def on_message(message: cl.Message):
    if message.elements:
        notice = cl.Message(content="Reading the attached files...")
        await notice.send()
        notice.content = await cl.make_async(_ingest_elements)(message.elements)
        await notice.update()
        return

    reply = cl.Message(content="Thinking...")
    await reply.send()
    result = await cl.make_async(run_fleet)(
        message.content,
        _actor(),
        [cl.LangchainCallbackHandler()] if ai_status()["enabled"] else None,
        _thread_id(),
    )
    answer = result["answer"]
    if result.get("mode") == "assistant":
        answer = format_chat_answer(answer)
    reply.content = answer
    await reply.update()
