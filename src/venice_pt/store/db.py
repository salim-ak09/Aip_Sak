from __future__ import annotations

import sqlite3
from pathlib import Path


def get_db_connection(db_path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                engagement_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                phase TEXT NOT NULL,
                actor TEXT NOT NULL,
                kind TEXT NOT NULL,
                tool TEXT,
                cmd TEXT,
                payload TEXT NOT NULL,
                parent_id TEXT,
                tokens_in INTEGER NOT NULL DEFAULT 0,
                tokens_out INTEGER NOT NULL DEFAULT 0,
                cost_usd REAL NOT NULL DEFAULT 0.0,
                duration_ms INTEGER NOT NULL DEFAULT 0
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_engagement_ts
            ON events (engagement_id, ts);
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_parent_id
            ON events (parent_id);
        """)
