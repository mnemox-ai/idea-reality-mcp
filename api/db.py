"""Score history — Turso Cloud (persistent) + SQLite (local fallback).

Connection strategy:
- TURSO_DATABASE_URL + TURSO_AUTH_TOKEN set → libsql_experimental embedded replica
  (local file synced with Turso Cloud — reads fast, writes persist remotely)
- Not set → local sqlite3 (dev / tests)
"""

from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Connection config
# ---------------------------------------------------------------------------

TURSO_DATABASE_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")
DB_PATH = os.environ.get("SCORE_DB_PATH", "./score_history.db")

_use_turso = False
_libsql = None

if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
    try:
        import libsql_experimental as _libsql  # type: ignore[import-untyped]

        _use_turso = True
        logger.info("[DB] Turso mode: %s", TURSO_DATABASE_URL[:60])
    except ImportError:
        logger.warning(
            "[DB] TURSO_DATABASE_URL set but libsql_experimental not installed. "
            "Falling back to local SQLite."
        )

if not _use_turso:
    logger.info("[DB] Local SQLite mode: %s", DB_PATH)


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------


def _get_conn():
    """Get a database connection.

    Turso: embedded replica (local file + remote sync).
    SQLite: plain local file with Row factory.
    """
    if _use_turso:
        conn = _libsql.connect(
            DB_PATH,
            sync_url=TURSO_DATABASE_URL,
            auth_token=TURSO_AUTH_TOKEN,
        )
        try:
            conn.sync()
        except Exception as exc:
            logger.warning("[DB] Turso sync on connect failed: %s", exc)
        return conn

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _sync_after_write(conn) -> None:
    """Sync embedded replica after writes so next read sees the change."""
    if _use_turso:
        try:
            conn.sync()
        except Exception as exc:
            logger.warning("[DB] Turso sync after write failed: %s", exc)


def _rows_to_dicts(cursor) -> list[dict[str, Any]]:
    """Convert cursor results to list of dicts (both backends)."""
    rows = cursor.fetchall()
    if not rows:
        return []
    # sqlite3.Row has .keys() → dict() works
    if hasattr(rows[0], "keys"):
        return [dict(row) for row in rows]
    # libsql returns tuples → use cursor.description
    if cursor.description:
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in rows]
    return []


def _row_to_dict(cursor) -> dict[str, Any] | None:
    """Fetch one row as dict, or None (both backends)."""
    row = cursor.fetchone()
    if row is None:
        return None
    if hasattr(row, "keys"):
        return dict(row)
    if cursor.description:
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))
    return None


# ---------------------------------------------------------------------------
# Schema init
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Create all tables and indexes if they don't exist."""
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS query_log (
            id INTEGER PRIMARY KEY,
            ip_hash TEXT,
            idea_hash TEXT,
            depth TEXT,
            score INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            report_id TEXT PRIMARY KEY,
            idea_text TEXT,
            idea_hash TEXT,
            score INTEGER,
            report_data TEXT,
            language TEXT,
            stripe_session_id TEXT,
            buyer_email TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS page_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            page TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            idea_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_sub_email ON subscribers(email)"
    )
    conn.commit()
    _sync_after_write(conn)
    conn.close()
    logger.info("[DB] All tables initialized.")


# Backward-compatible aliases (init_db now creates everything)
def init_subscribers_table() -> None:
    """Alias → init_db(). Kept for backward compatibility."""
    init_db()


def init_query_log_table() -> None:
    """Alias → init_db(). Kept for backward compatibility."""
    init_db()


def init_reports_table() -> None:
    """Alias → init_db(). Kept for backward compatibility."""
    init_db()


def init_page_views_table() -> None:
    """Alias → init_db(). Kept for backward compatibility."""
    init_db()


# ---------------------------------------------------------------------------
# Score history
# ---------------------------------------------------------------------------


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
    _sync_after_write(conn)
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_history(hash_val: str) -> list[dict[str, Any]]:
    """Get all score records for a given idea hash, newest first."""
    conn = _get_conn()
    cur = conn.execute(
        "SELECT * FROM score_history WHERE idea_hash = ? ORDER BY created_at DESC",
        (hash_val,),
    )
    result = _rows_to_dicts(cur)
    conn.close()
    return result


def get_all_scores() -> list[dict[str, Any]]:
    """Return all score records (for export), newest first.

    Excludes 'breakdown' column to keep payload small.
    """
    conn = _get_conn()
    cur = conn.execute(
        "SELECT id, idea_hash, idea_text, score, keywords, depth, lang, "
        "keyword_source, created_at FROM score_history ORDER BY created_at DESC"
    )
    result = _rows_to_dicts(cur)
    conn.close()
    return result


# ---------------------------------------------------------------------------
# Subscribers — email collection for report unlock (v0.4.0)
# ---------------------------------------------------------------------------


def save_subscriber(email: str, idea_hash_val: str) -> int:
    """Insert a subscriber record and return the row id."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO subscribers (email, idea_hash, created_at) VALUES (?, ?, ?)",
        (email, idea_hash_val, now),
    )
    conn.commit()
    _sync_after_write(conn)
    row_id = cur.lastrowid
    conn.close()
    logger.info("[SUBSCRIBE] %s | %s | %s", email, idea_hash_val, now)
    return row_id


def get_subscriber_count() -> int:
    """Return total number of subscribers."""
    conn = _get_conn()
    row = conn.execute("SELECT COUNT(*) FROM subscribers").fetchone()
    conn.close()
    return row[0]


# ---------------------------------------------------------------------------
# Query log — lightweight usage analytics (v0.5.0)
# ---------------------------------------------------------------------------


def save_query_log(ip_hash: str, idea_hash: str, depth: str, score: int) -> int:
    """Insert a query log record and return the row id."""
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO query_log (ip_hash, idea_hash, depth, score) VALUES (?, ?, ?, ?)",
        (ip_hash, idea_hash, depth, score),
    )
    conn.commit()
    _sync_after_write(conn)
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_query_stats() -> dict:
    """Return query usage stats: total_queries, unique_ips, return_rate."""
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM query_log").fetchone()[0]
    unique_ips = conn.execute(
        "SELECT COUNT(DISTINCT ip_hash) FROM query_log"
    ).fetchone()[0]
    if unique_ips > 0:
        returning = conn.execute(
            "SELECT COUNT(*) FROM "
            "(SELECT ip_hash FROM query_log GROUP BY ip_hash HAVING COUNT(*) > 1)"
        ).fetchone()[0]
        return_rate = round(returning / unique_ips * 100, 1)
    else:
        return_rate = 0.0
    conn.close()
    return {
        "total_queries": total,
        "unique_ips": unique_ips,
        "return_rate": return_rate,
    }


# ---------------------------------------------------------------------------
# Reports — paid report storage (v0.5.0)
# ---------------------------------------------------------------------------


def save_report(
    report_id: str,
    idea_text: str,
    idea_hash: str,
    score: int,
    report_data: str,
    language: str,
    stripe_session_id: str | None = None,
    buyer_email: str | None = None,
) -> None:
    """Insert a report record."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO reports "
        "(report_id, idea_text, idea_hash, score, report_data, language, stripe_session_id, buyer_email) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            report_id,
            idea_text,
            idea_hash,
            score,
            report_data,
            language,
            stripe_session_id,
            buyer_email,
        ),
    )
    conn.commit()
    _sync_after_write(conn)
    conn.close()


def get_report(report_id: str) -> dict[str, Any] | None:
    """Get a report by its ID. Returns dict or None if not found."""
    conn = _get_conn()
    cur = conn.execute(
        "SELECT * FROM reports WHERE report_id = ?",
        (report_id,),
    )
    result = _row_to_dict(cur)
    conn.close()
    return result


def get_report_by_stripe_session(stripe_session_id: str) -> dict[str, Any] | None:
    """Get a report by its Stripe/LemonSqueezy order ID."""
    conn = _get_conn()
    cur = conn.execute(
        "SELECT * FROM reports WHERE stripe_session_id = ?",
        (stripe_session_id,),
    )
    result = _row_to_dict(cur)
    conn.close()
    return result


def get_report_by_idea_hash(idea_hash_val: str) -> dict[str, Any] | None:
    """Get the most recent report for a given idea_hash."""
    conn = _get_conn()
    cur = conn.execute(
        "SELECT * FROM reports WHERE idea_hash = ? ORDER BY created_at DESC LIMIT 1",
        (idea_hash_val,),
    )
    result = _row_to_dict(cur)
    conn.close()
    return result


def update_report_data(report_id: str, report_data: str, language: str) -> None:
    """Update report_data and language for an existing report."""
    conn = _get_conn()
    conn.execute(
        "UPDATE reports SET report_data = ?, language = ? WHERE report_id = ?",
        (report_data, language, report_id),
    )
    conn.commit()
    _sync_after_write(conn)
    conn.close()


# ---------------------------------------------------------------------------
# Page views — lightweight visit tracking (v0.5.0)
# ---------------------------------------------------------------------------


def save_page_view(page: str) -> int:
    """Insert a page view record and return the row id."""
    conn = _get_conn()
    cur = conn.execute("INSERT INTO page_views (page) VALUES (?)", (page,))
    conn.commit()
    _sync_after_write(conn)
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_total_checks() -> int:
    """Return total number of score_history records."""
    conn = _get_conn()
    count = conn.execute("SELECT COUNT(*) FROM score_history").fetchone()[0]
    conn.close()
    return count


def get_last_check_time() -> str | None:
    """Return created_at of the most recent score_history record, or None."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT created_at FROM score_history ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return row[0] if row else None
