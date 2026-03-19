"""Initialize Turso Cloud tables via HTTP API (libsql_client async)."""
import asyncio
import os
import libsql_client

TURSO_URL = os.environ.get("TURSO_DATABASE_URL", "").replace("libsql://", "https://", 1)
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "")

if not TURSO_URL or not TURSO_TOKEN:
    raise RuntimeError("Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN environment variables.")

TABLES = [
    """CREATE TABLE IF NOT EXISTS score_history (
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
    )""",
    "CREATE INDEX IF NOT EXISTS idx_idea_hash ON score_history(idea_hash)",
    """CREATE TABLE IF NOT EXISTS query_log (
        id INTEGER PRIMARY KEY,
        ip_hash TEXT,
        idea_hash TEXT,
        depth TEXT,
        score INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS reports (
        report_id TEXT PRIMARY KEY,
        idea_text TEXT,
        idea_hash TEXT,
        score INTEGER,
        report_data TEXT,
        language TEXT,
        stripe_session_id TEXT,
        buyer_email TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS page_views (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        page TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS subscribers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        idea_hash TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_sub_email ON subscribers(email)",
]


async def main():
    async with libsql_client.create_client(url=TURSO_URL, auth_token=TURSO_TOKEN) as client:
        for sql in TABLES:
            await client.execute(sql)
            print(f"OK: {sql.strip()[:60]}...")

        # Verify
        result = await client.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row[0] for row in result.rows]
        print(f"\nTables in Turso: {tables}")

        # Test insert + read + delete
        await client.execute(
            "INSERT INTO score_history (idea_hash, idea_text, score, breakdown, keywords) "
            "VALUES (?, ?, ?, ?, ?)",
            ["test_init", "test idea from init script", 42, "{}", "test"],
        )
        result = await client.execute("SELECT COUNT(*) FROM score_history")
        print(f"score_history count: {result.rows[0][0]}")

        await client.execute("DELETE FROM score_history WHERE idea_hash = 'test_init'")
        print("Test row cleaned up.")

    print("\n=== Turso Cloud ready! ===")


if __name__ == "__main__":
    asyncio.run(main())
