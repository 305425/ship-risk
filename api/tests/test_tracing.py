import os

from langsmith.utils import get_env_var, tracing_is_enabled

from app.tracing import configure_tracing


def test_tracing_stays_off_without_a_key(monkeypatch):
    monkeypatch.delenv("LANGSMITH_API_KEY", raising=False)
    monkeypatch.delenv("LANGCHAIN_API_KEY", raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "true")

    assert configure_tracing() is False


def test_tracing_turns_on_for_a_key(monkeypatch):
    monkeypatch.setenv("LANGSMITH_API_KEY", "lsv2-test")
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.delenv("LANGSMITH_PROJECT", raising=False)

    try:
        assert configure_tracing() is True
        get_env_var.cache_clear()
        assert tracing_is_enabled() is True
        assert os.environ["LANGSMITH_PROJECT"] == "ship-risk"
    finally:
        for name in (
            "LANGSMITH_TRACING", "LANGCHAIN_TRACING_V2", "LANGSMITH_API_KEY", "LANGCHAIN_API_KEY",
            "LANGSMITH_PROJECT", "LANGCHAIN_PROJECT",
        ):
            os.environ.pop(name, None)
        get_env_var.cache_clear()
