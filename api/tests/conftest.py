import os
import tempfile
from datetime import date
from pathlib import Path

import pytest

from app.config import API_DIR
from app.scoring import load_rules

from .sample_data import DATA_DIR, load_sample

AS_OF = date(2026, 11, 25)
API_KEY = "test-key"


@pytest.fixture(scope="session")
def rules() -> dict:
    return load_rules(API_DIR / "rules.yaml")


@pytest.fixture(scope="session")
def sample() -> dict:
    return load_sample()


@pytest.fixture(scope="session")
def sample_files() -> list[tuple[str, bytes]]:
    return [(p.name, p.read_bytes()) for p in sorted(Path(DATA_DIR).glob("*.csv"))]


@pytest.fixture
def client():
    """API client on a freshly migrated, empty database. Needs TEST_DATABASE_URL."""
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set")

    os.environ.update(
        DATABASE_URL=url,
        API_KEY=API_KEY,
        AS_OF=AS_OF.isoformat(),
        MLFLOW_DIR=tempfile.mkdtemp(prefix="shiprisk-mlflow-"),
    )
    saved_keys = {name: os.environ.pop(name, None) for name in ("OPENAI_API_KEY", "GOOGLE_API_KEY")}
    from alembic import command
    from alembic.config import Config
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, text

    from app import config, db, main, rag

    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    main.get_rules.cache_clear()
    rag.set_store(None)

    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    engine.dispose()
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "alembic"))
    command.upgrade(cfg, "head")

    with TestClient(main.app, headers={"X-API-Key": API_KEY}) as c:
        yield c
    db.get_engine().dispose()
    rag.set_store(None)
    config.get_settings.cache_clear()
    for name, value in saved_keys.items():
        if value is not None:
            os.environ[name] = value
