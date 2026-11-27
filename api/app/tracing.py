"""LangSmith traces for fleet chat and RAGWire.

Tracing stays off until LANGSMITH_API_KEY is set. With a key, each chat is one
trace and the RAGWire retrieval and answer calls nest under it.
"""

import os

PROJECT = "ship-risk"


def _clean(name: str) -> str:
    return os.environ.get(name, "").split("#", 1)[0].strip()


def configure_tracing() -> bool:
    """Turn LangSmith on when an API key is present. Returns whether tracing is active."""
    key = _clean("LANGSMITH_API_KEY") or _clean("LANGCHAIN_API_KEY")
    if not key:
        return False
    flag = _clean("LANGSMITH_TRACING").lower() or _clean("LANGCHAIN_TRACING_V2").lower()
    if flag in ("0", "false", "no", "off"):
        return False
    project = _clean("LANGSMITH_PROJECT") or _clean("LANGCHAIN_PROJECT") or PROJECT
    os.environ["LANGSMITH_API_KEY"] = key
    os.environ["LANGCHAIN_API_KEY"] = key
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGSMITH_PROJECT"] = project
    os.environ["LANGCHAIN_PROJECT"] = project
    from langsmith.utils import get_env_var

    get_env_var.cache_clear()
    return True


def chat_inputs(inputs: dict) -> dict:
    return {key: value for key, value in inputs.items() if key in ("question", "vessel_id", "actor", "thread_id")}


def search_inputs(inputs: dict) -> dict:
    return {key: value for key, value in inputs.items() if key != "k"}


def answer_inputs(inputs: dict) -> dict:
    documents = inputs.get("docs") or []
    return {"query": inputs.get("query"), "documents": len(documents)}
