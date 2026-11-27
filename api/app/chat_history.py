"""Chainlit thread tables in the application database.

Chainlit 2.12 stores past chats through its asyncpg data layer. The API keeps
its SQLAlchemy URL (postgresql+psycopg) and hands Chainlit the same database
with the driver prefix removed.
"""

from sqlalchemy import text

from .db import get_engine

_TABLES = """
CREATE TABLE IF NOT EXISTS "User" (
    id TEXT PRIMARY KEY,
    identifier TEXT NOT NULL UNIQUE,
    metadata TEXT NOT NULL DEFAULT '{}',
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS "Thread" (
    id TEXT PRIMARY KEY,
    name TEXT,
    "userId" TEXT REFERENCES "User"(id) ON DELETE SET NULL,
    tags TEXT[],
    metadata TEXT NOT NULL DEFAULT '{}',
    "createdAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
    "updatedAt" TIMESTAMPTZ NOT NULL DEFAULT now(),
    "deletedAt" TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS "Step" (
    id TEXT PRIMARY KEY,
    "threadId" TEXT REFERENCES "Thread"(id) ON DELETE CASCADE,
    "parentId" TEXT,
    input TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    name TEXT,
    output TEXT,
    type TEXT,
    "createdAt" TIMESTAMPTZ,
    "startTime" TIMESTAMPTZ,
    "endTime" TIMESTAMPTZ,
    "showInput" TEXT,
    "isError" BOOLEAN
);

CREATE TABLE IF NOT EXISTS "Element" (
    id TEXT PRIMARY KEY,
    "threadId" TEXT REFERENCES "Thread"(id) ON DELETE CASCADE,
    "stepId" TEXT,
    metadata TEXT NOT NULL DEFAULT '{}',
    mime TEXT,
    name TEXT,
    "objectKey" TEXT,
    url TEXT,
    "chainlitKey" TEXT,
    display TEXT,
    size TEXT,
    language TEXT,
    page INT,
    props TEXT NOT NULL DEFAULT '{}',
    "autoPlay" BOOLEAN,
    "playerConfig" TEXT
);

CREATE TABLE IF NOT EXISTS "Feedback" (
    id TEXT PRIMARY KEY,
    "stepId" TEXT,
    name TEXT,
    value DOUBLE PRECISION,
    comment TEXT
);

CREATE INDEX IF NOT EXISTS thread_user_updated_idx ON "Thread" ("userId", "updatedAt" DESC);
"""


def chainlit_database_url(sqlalchemy_url: str) -> str:
    """asyncpg accepts postgresql:// and rejects the SQLAlchemy +psycopg driver name."""
    prefix = "postgresql+psycopg://"
    if sqlalchemy_url.startswith(prefix):
        return "postgresql://" + sqlalchemy_url[len(prefix):]
    return sqlalchemy_url


def chat_layer(database_url: str):
    """Chainlit data layer that opens a connection on the current event loop.

    A shared asyncpg pool breaks here: the HTTP sidebar and the chat socket
    run on different loops, and a pool created on one cannot be used on the other.
    """
    import asyncpg
    from chainlit.data.chainlit_data_layer import ChainlitDataLayer

    class LoopSafeChatLayer(ChainlitDataLayer):
        async def connect(self):
            return None

        async def cleanup(self):
            self.pool = None

        async def execute_query(self, query: str, params: dict | None = None) -> list:
            connection = await asyncpg.connect(self.database_url)
            try:
                if params:
                    records = await connection.fetch(query, *params.values())
                else:
                    records = await connection.fetch(query)
                return [dict(record) for record in records]
            finally:
                await connection.close()

    return LoopSafeChatLayer(database_url=database_url)


def ensure_chat_tables() -> None:
    with get_engine().begin() as conn:
        for statement in _TABLES.split(";"):
            sql = statement.strip()
            if sql:
                conn.execute(text(sql))
