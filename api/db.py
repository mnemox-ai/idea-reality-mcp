"""Score history — Turso Cloud (persistent) + SQLite (local fallback).

Connection strategy (in order of preference):
1. TURSO_DATABASE_URL set → libsql_client (pure Python HTTP, works everywhere)
2. Not set → local sqlite3 (dev / tests)

libsql_client is wrapped in TursoConnection/TursoCursor to mimic the
sqlite3 API, so all downstream code works unchanged.
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
_turso_client = None  # lazy-init sync client


def _turso_url() -> str:
    """Convert libsql:// URL to https:// for HTTP API."""
    url = TURSO_DATABASE_URL or ""
    if url.startswith("libsql://"):
        return url.replace("libsql://", "https://", 1)
    return url


if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN:
    try:
        import libsql_client  # type: ignore[import-untyped]

        _use_turso = True
        logger.info("[DB] Turso HTTP mode: %s", _turso_url()[:60])
    except ImportError:
        logger.warning(
            "[DB] TURSO_DATABASE_URL set but libsql_client not installed. "
            "Falling back to local SQLite."
        )

if not _use_turso:
    logger.info("[DB] Local SQLite mode: %s", DB_PATH)


# ---------------------------------------------------------------------------
# Turso wrapper — mimics sqlite3.Connection / sqlite3.Cursor
# ---------------------------------------------------------------------------


class TursoCursor:
    """Wraps libsql_client.ResultSet to mimic sqlite3.Cursor."""

    def __init__(self, result):
        self._result = result
        self._rows = list(result.rows) if result.rows else []
        self._columns = list(result.columns) if result.columns else []
        self._index = 0

    @property
    def description(self):
        if self._columns:
            return [(col, None, None, None, None, None, None) for col in self._columns]
        return None

    @property
    def lastrowid(self):
        return getattr(self._result, "last_insert_rowid", None)

    def fetchall(self):
        return self._rows

    def fetchone(self):
        if self._index < len(self._rows):
            row = self._rows[self._index]
            self._index += 1
            return row
        return None


class TursoConnection:
    """Wraps libsql_client sync client to mimic sqlite3.Connection."""

    def __init__(self, client):
        self._client = client

    def execute(self, sql, params=()):
        result = self._client.execute(sql, list(params))
        return TursoCursor(result)

    def commit(self):
        pass  # Turso HTTP auto-commits

    def close(self):
        pass  # Persistent client, reused across calls

    def sync(self):
        pass  # HTTP mode, no local replica to sync


def _get_turso_client():
    """Get or create the Turso sync client (singleton)."""
    global _turso_client
    if _turso_client is None:
        import libsql_client

        _turso_client = libsql_client.create_client_sync(
            url=_turso_url(),
            auth_token=TURSO_AUTH_TOKEN,
        )
        logger.info("[DB] Turso client created: %s", _turso_url()[:60])
    return _turso_client


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------


def _get_conn():
    """Get a database connection.

    Turso: HTTP client wrapped in sqlite3-like API.
    SQLite: plain local file with Row factory.
    """
    if _use_turso:
        return TursoConnection(_get_turso_client())

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _sync_after_write(conn) -> None:
    """No-op for HTTP mode. Kept for API compatibility."""
    pass


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
    try:
        conn.execute("ALTER TABLE query_log ADD COLUMN country TEXT")
    except Exception:
        pass
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS funnel_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            event_name TEXT NOT NULL,
            ip_hash TEXT DEFAULT '',
            metadata TEXT DEFAULT '{}',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_fe_session ON funnel_events(session_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_fe_event ON funnel_events(event_name)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_fe_created ON funnel_events(created_at)"
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


def save_query_log(ip_hash: str, idea_hash: str, depth: str, score: int, country: str | None = None) -> int:
    """Insert a query log record and return the row id."""
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO query_log (ip_hash, idea_hash, depth, score, country) VALUES (?, ?, ?, ?, ?)",
        (ip_hash, idea_hash, depth, score, country),
    )
    conn.commit()
    _sync_after_write(conn)
    row_id = cur.lastrowid
    conn.close()
    return row_id


def get_unique_countries() -> int:
    """Return number of unique countries in query_log."""
    conn = _get_conn()
    count = conn.execute(
        "SELECT COUNT(DISTINCT country) FROM query_log WHERE country IS NOT NULL AND country != ''"
    ).fetchone()[0]
    conn.close()
    return count


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


# ---------------------------------------------------------------------------
# Crowd Intelligence — similar idea queries (for paid reports)
# ---------------------------------------------------------------------------


def search_similar_ideas(
    keywords: list[str],
    exclude_hash: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Search score_history for ideas matching any keyword (LIKE).

    Returns list of dicts with keys: idea_text, score, depth, lang, created_at.
    """
    words = [w for w in keywords if len(w) >= 3][:5]
    if not words:
        return []

    conditions = " OR ".join(["idea_text LIKE ?"] * len(words))
    params: list = [f"%{w}%" for w in words]

    sql = (
        "SELECT idea_text, score, depth, lang, created_at "
        "FROM score_history WHERE (" + conditions + ")"
    )
    if exclude_hash:
        sql += " AND idea_hash != ?"
        params.append(exclude_hash)

    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    conn = _get_conn()
    cur = conn.execute(sql, params)
    result = _rows_to_dicts(cur)
    conn.close()
    return result


# ---------------------------------------------------------------------------
# Funnel events
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Badge data & crowd intel helpers
# ---------------------------------------------------------------------------


def get_idea_by_hash(idea_hash: str) -> dict[str, Any] | None:
    """Return the first score_history row for a given idea_hash, or None."""
    conn = _get_conn()
    cur = conn.execute(
        "SELECT * FROM score_history WHERE idea_hash = ? LIMIT 1",
        (idea_hash,),
    )
    result = _row_to_dict(cur)
    conn.close()
    return result


def get_score_percentile(score: int) -> float:
    """Return the percentile rank of a score (0-100)."""
    conn = _get_conn()
    total = conn.execute("SELECT COUNT(*) FROM score_history").fetchone()[0]
    if total == 0:
        conn.close()
        return 0.0
    lte = conn.execute(
        "SELECT COUNT(*) FROM score_history WHERE score <= ?", (score,)
    ).fetchone()[0]
    conn.close()
    return round(lte / total * 100, 1)


def get_weekly_volume(weeks: int = 12) -> list[dict[str, Any]]:
    """Return weekly check counts for the last N weeks."""
    conn = _get_conn()
    cur = conn.execute(
        "SELECT strftime('%Y-W%W', created_at) as week, COUNT(*) as count "
        "FROM score_history GROUP BY week ORDER BY week"
    )
    result = _rows_to_dicts(cur)
    conn.close()
    return result[-weeks:] if len(result) > weeks else result


def get_top_keywords(limit: int = 20) -> list[dict[str, Any]]:
    """Parse all keywords JSON from score_history, return top N by frequency."""
    import json as _json

    conn = _get_conn()
    cur = conn.execute("SELECT keywords FROM score_history")
    rows = cur.fetchall()
    conn.close()

    freq: dict[str, int] = {}
    for row in rows:
        raw = row[0] if isinstance(row, (list, tuple)) else list(row)[0]
        try:
            kws = _json.loads(raw) if isinstance(raw, str) else []
            if isinstance(kws, list):
                for kw in kws:
                    if isinstance(kw, str) and kw.strip():
                        freq[kw.strip().lower()] = freq.get(kw.strip().lower(), 0) + 1
        except Exception:
            pass

    sorted_kws = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{"keyword": k, "count": c} for k, c in sorted_kws]


def get_country_distribution() -> list[dict[str, Any]]:
    """Return country counts from query_log, sorted by count desc."""
    conn = _get_conn()
    cur = conn.execute(
        "SELECT country, COUNT(*) as count FROM query_log "
        "WHERE country IS NOT NULL GROUP BY country ORDER BY count DESC"
    )
    result = _rows_to_dicts(cur)
    conn.close()
    return result


def get_recent_high_scores(limit: int = 10, min_score: int = 60) -> list[dict[str, Any]]:
    """Return recent high-scoring ideas, truncated to 60 chars."""
    conn = _get_conn()
    cur = conn.execute(
        "SELECT idea_text, score, created_at FROM score_history "
        "WHERE score >= ? ORDER BY created_at DESC LIMIT ?",
        (min_score, limit),
    )
    result = _rows_to_dicts(cur)
    conn.close()
    for row in result:
        if row.get("idea_text") and len(row["idea_text"]) > 60:
            row["idea_text"] = row["idea_text"][:60] + "..."
    return result


def get_category_distribution(limit: int = 10) -> list[dict[str, Any]]:
    """Parse all keywords JSON from score_history, count frequency, return top N."""
    import json as _json

    conn = _get_conn()
    cur = conn.execute("SELECT keywords FROM score_history")
    rows = cur.fetchall()
    conn.close()

    freq: dict[str, int] = {}
    for row in rows:
        raw = row[0] if isinstance(row, (list, tuple)) else list(row)[0]
        try:
            kws = _json.loads(raw) if isinstance(raw, str) else []
            if isinstance(kws, list):
                for kw in kws:
                    if isinstance(kw, str) and kw.strip():
                        freq[kw.strip().lower()] = freq.get(kw.strip().lower(), 0) + 1
        except Exception:
            pass

    sorted_kws = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:limit]
    return [{"keyword": k, "count": c} for k, c in sorted_kws]


def save_funnel_event(
    session_id: str,
    event_name: str,
    ip_hash: str = "",
    metadata: str = "{}",
) -> int:
    """Insert a single funnel event. Returns row id."""
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO funnel_events (session_id, event_name, ip_hash, metadata) "
        "VALUES (?, ?, ?, ?)",
        (session_id, event_name, ip_hash, metadata),
    )
    conn.commit()
    _sync_after_write(conn)
    row_id = cur.lastrowid
    conn.close()
    return row_id


def save_funnel_events_batch(
    events: list[tuple[str, str, str, str]],
) -> int:
    """Insert multiple funnel events in one transaction.

    Each tuple: (session_id, event_name, ip_hash, metadata).
    Returns count inserted.
    """
    if not events:
        return 0
    conn = _get_conn()
    count = 0
    for session_id, event_name, ip_hash, metadata in events:
        conn.execute(
            "INSERT INTO funnel_events (session_id, event_name, ip_hash, metadata) "
            "VALUES (?, ?, ?, ?)",
            (session_id, event_name, ip_hash, metadata),
        )
        count += 1
    conn.commit()
    _sync_after_write(conn)
    conn.close()
    return count


def get_funnel_stats(days: int = 7) -> dict[str, Any]:
    """Return funnel aggregates for the last N days.

    Returns unique_sessions, event counts, depth split, paypal click scores,
    hourly distribution, device breakdown, and computed funnel rates.
    """
    conn = _get_conn()
    cutoff_sql = f"datetime('now', '-{int(days)} days')"

    # Unique sessions
    sessions = 0
    row = conn.execute(
        f"SELECT COUNT(DISTINCT session_id) FROM funnel_events "
        f"WHERE created_at >= {cutoff_sql}"
    ).fetchone()
    if row:
        sessions = row[0] if isinstance(row, (list, tuple)) else list(row)[0]

    # Event counts
    event_counts: dict[str, int] = {}
    cur = conn.execute(
        f"SELECT event_name, COUNT(*) FROM funnel_events "
        f"WHERE created_at >= {cutoff_sql} GROUP BY event_name"
    )
    for r in cur.fetchall():
        vals = list(r) if not isinstance(r, (list, tuple)) else r
        event_counts[vals[0]] = vals[1]

    # Depth split from scan_complete metadata
    deep_count = 0
    quick_count = 0
    cur2 = conn.execute(
        f"SELECT metadata FROM funnel_events "
        f"WHERE event_name = 'scan_complete' AND created_at >= {cutoff_sql}"
    )
    import json as _json
    for r in cur2.fetchall():
        val = list(r)[0] if not isinstance(r, (list, tuple)) else r[0]
        try:
            m = _json.loads(val) if isinstance(val, str) else {}
            if m.get("depth") == "deep":
                deep_count += 1
            else:
                quick_count += 1
        except Exception:
            quick_count += 1

    # PayPal click scores
    paypal_scores: list[int] = []
    cur3 = conn.execute(
        f"SELECT metadata FROM funnel_events "
        f"WHERE event_name = 'paypal_click' AND created_at >= {cutoff_sql}"
    )
    for r in cur3.fetchall():
        val = list(r)[0] if not isinstance(r, (list, tuple)) else r[0]
        try:
            m = _json.loads(val) if isinstance(val, str) else {}
            s = m.get("score")
            if s is not None:
                paypal_scores.append(int(s))
        except Exception:
            pass

    # Hourly distribution (scan_start)
    hourly: dict[str, int] = {}
    cur4 = conn.execute(
        f"SELECT substr(created_at, 12, 2) AS hour, COUNT(*) FROM funnel_events "
        f"WHERE event_name = 'scan_start' AND created_at >= {cutoff_sql} "
        f"GROUP BY hour ORDER BY hour"
    )
    for r in cur4.fetchall():
        vals = list(r) if not isinstance(r, (list, tuple)) else r
        hourly[vals[0]] = vals[1]

    # Device breakdown (page_load metadata)
    devices: dict[str, int] = {}
    cur5 = conn.execute(
        f"SELECT metadata FROM funnel_events "
        f"WHERE event_name = 'page_load' AND created_at >= {cutoff_sql}"
    )
    for r in cur5.fetchall():
        val = list(r)[0] if not isinstance(r, (list, tuple)) else r[0]
        try:
            m = _json.loads(val) if isinstance(val, str) else {}
            d = m.get("ua_device", "unknown")
            devices[d] = devices.get(d, 0) + 1
        except Exception:
            devices["unknown"] = devices.get("unknown", 0) + 1

    conn.close()

    # Compute funnel rates
    page_loads = event_counts.get("page_load", 0)
    scans = event_counts.get("scan_start", 0)
    paypal_clicks = event_counts.get("paypal_click", 0)
    unlocks = event_counts.get("unlock_complete", 0)

    funnel_rates = {
        "visit_to_scan": round(scans / page_loads * 100, 1) if page_loads else 0,
        "scan_to_paypal": round(paypal_clicks / scans * 100, 1) if scans else 0,
        "paypal_to_unlock": round(unlocks / paypal_clicks * 100, 1) if paypal_clicks else 0,
        "overall_conversion": round(unlocks / page_loads * 100, 2) if page_loads else 0,
    }

    return {
        "period_days": days,
        "unique_sessions": sessions,
        "events": event_counts,
        "funnel_rates": funnel_rates,
        "depth_split": {"deep": deep_count, "quick": quick_count},
        "paypal_click_scores": paypal_scores,
        "hourly_distribution": hourly,
        "device_breakdown": devices,
    }
