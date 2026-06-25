from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DB_PATH = Path(os.getenv("DB_PATH", "data/tickets.db"))

if not DB_PATH.exists():
    raise SystemExit(f"SQLite DB not found: {DB_PATH}. Run the service and send at least one request first.")

with sqlite3.connect(DB_PATH) as conn:
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, created_at, client_id, channel, category, confidence, escalate, error
        FROM tickets
        ORDER BY id DESC
        LIMIT 10;
        """
    ).fetchall()

if not rows:
    print("No tickets found yet.")
else:
    for row in rows:
        print(dict(row))
