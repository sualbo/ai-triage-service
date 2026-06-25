from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.config import settings
from app.logger import logger


CREATE_TICKETS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    client_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    text TEXT NOT NULL,
    category TEXT NOT NULL,
    confidence TEXT NOT NULL,
    escalate INTEGER NOT NULL,
    draft_reply TEXT NOT NULL,
    error TEXT
);
"""

CREATE_INDEXES_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_tickets_client_id ON tickets(client_id);",
    "CREATE INDEX IF NOT EXISTS idx_tickets_category ON tickets(category);",
]


def init_db() -> None:
    settings.ensure_runtime_dirs()
    with sqlite3.connect(settings.db_path) as conn:
        conn.execute(CREATE_TICKETS_TABLE_SQL)
        for statement in CREATE_INDEXES_SQL:
            conn.execute(statement)
        conn.commit()
    logger.info("SQLite initialized at %s", settings.db_path)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.db_path)
    try:
        conn.row_factory = sqlite3.Row
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
