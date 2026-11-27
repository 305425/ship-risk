import os
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent

PROVIDER_KEYS = {"openai": "OPENAI_API_KEY", "gemini": "GOOGLE_API_KEY"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    qdrant_url: str
    api_key: str
    rules_path: Path
    as_of: date | None
    llm_provider: str
    reports_dir: Path

    def today(self) -> date:
        return self.as_of or date.today()

    @property
    def rag_config_path(self) -> Path:
        return API_DIR / "config" / f"{self.llm_provider}.yaml"

    def llm_key_missing(self) -> str | None:
        """Name of the provider's API key variable when it is not set, else None."""
        var = PROVIDER_KEYS.get(self.llm_provider)
        if var is None:
            return f"LLM_PROVIDER '{self.llm_provider}' (expected one of {', '.join(PROVIDER_KEYS)})"
        return None if os.environ.get(var, "").strip() else var


def _env(name: str, default: str) -> str:
    value = os.environ.get(name, "").split("#", 1)[0].strip()
    return value or default


@lru_cache
def get_settings() -> Settings:
    as_of = _env("AS_OF", "")
    return Settings(
        database_url=_env("DATABASE_URL", "postgresql+psycopg://shiprisk:shiprisk@localhost:5432/shiprisk"),
        qdrant_url=_env("QDRANT_URL", "http://localhost:6333"),
        api_key=os.environ.get("API_KEY", ""),
        rules_path=Path(_env("RULES_PATH", str(API_DIR / "rules.yaml"))),
        as_of=date.fromisoformat(as_of) if as_of else None,
        llm_provider=_env("LLM_PROVIDER", "openai").lower(),
        reports_dir=Path(_env("REPORTS_DIR", str(API_DIR / "reports"))),
    )
