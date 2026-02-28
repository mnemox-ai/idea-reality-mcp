"""Score history — SQLite storage layer.

KNOWN LIMITATION: Render free tier wipes filesystem on each deploy.
SQLite data will be lost on restart. For persistent storage, migrate to:
- Turso (SQLite cloud, free tier sufficient)
- Render PostgreSQL (90-day free tier)
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from typing import Any

DB_PATH = os.environ.get("SCORE_DB_PATH", "./score_history.db")


def _get_conn() -> sqlite3.Connection:
    """Get a SQLite connection with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create score_history table and index if they don't exist."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS score_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idea_hash TEXT NOT NULL,
            idea_text TEXT NOT NULL,
            score INTEGER NOT NULL,
            breakdown TEXT NOT NULL,
            keywords TEXT NOT NULL,
            depth TEXT DEFAULT 'quick',
            lang TEXT DEFAULT 'en',
            keyword_source TEXT DEFAULT 'dictionary',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_idea_hash ON score_history(idea_hash)"
    )
    conn.commit()
    conn.close()


def idea_hash(idea_text: str) -> str:
    """Compute SHA256 hash of normalised idea text."""
    return hashlib.sha256(idea_text.strip().lower().encode()).hexdigest()


def save_score(
    idea_text: str,
    score: int,
    breakdown: str,
    keywords: str,
    depth: str = "quick",
    lang: str = "en",
    keyword_source: str = "dictionary",
) -> int:
    """Insert a score record and return the row id."""
    h = idea_hash(idea_text)
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO score_history "
        "(idea_hash, idea_text, score, breakdown, keywords, depth, lang, keyword_source) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (h, idea_text, score, breakdown, keywords, depth, lang, keyword_source),
    )
    conn.commit()
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_history(hash_val: str) -> list[dict[str, Any]]:
    """Get all score records for a given idea hash, newest first."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM score_history WHERE idea_hash = ? ORDER BY created_at DESC",
        (hash_val,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
