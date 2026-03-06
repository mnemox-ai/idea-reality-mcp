"""Import 847 Discord queries into Turso Cloud score_history table.

Discord embed format → score_history columns mapping:
  title:        "🟡 Signal 71/100"    → score = 71
  description:  idea text (truncated at 120 chars + "...")  → idea_text
  fields.Keywords:   "kw1, kw2, ..."   → keywords
  fields.Depth:      "quick" | "deep"  → depth
  fields.Lang:       "en" | "zh"       → lang
  fields.KW Source:  "llm" | "dict"    → keyword_source
  timestamp:    ISO datetime           → created_at
"""
import asyncio
import hashlib
import json
import re
import sys

import libsql_client

TURSO_URL = "https://idea-reality-zychenpeng.aws-us-east-1.turso.io"
TURSO_TOKEN = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJpYXQiOjE3NzI4MTg0MzIsImlkIjoiMDE5Y2M0MzUtM2YwMS03NTMwLThlNDMtZWU0NDYzYjFjZGU2IiwicmlkIjoiNDAxZWNiMzItNmYwZS00Y2I0LWI5YTAtNDk3ZjI4YzI4MjI3In0._8P0xeqxZS2ngtJr806OGmEeqbvsnK0cr6kS3VfMuYrCcZiK2DQc0vrQwF3dMLUu7qvZrR83r1oLBdYj1nxxDw"

DISCORD_JSON = "discord_all_queries.json"


def idea_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()


def parse_score(title: str) -> int:
    m = re.search(r"Signal (\d+)/100", title)
    return int(m.group(1)) if m else 0


async def main():
    with open(DISCORD_JSON, encoding="utf-8") as f:
        queries = json.load(f)

    print(f"Loaded {len(queries)} queries from {DISCORD_JSON}")

    async with libsql_client.create_client(url=TURSO_URL, auth_token=TURSO_TOKEN) as client:
        # Check existing count
        result = await client.execute("SELECT COUNT(*) FROM score_history")
        existing = result.rows[0][0]
        print(f"Existing rows in score_history: {existing}")

        if existing > 0:
            print("WARNING: score_history already has data. Skipping import to avoid duplicates.")
            print("To force re-import, run: DELETE FROM score_history")
            return

        imported = 0
        skipped = 0

        for q in queries:
            title = q.get("title", "")
            description = q.get("description", "")
            fields = q.get("fields", {})
            timestamp = q.get("timestamp", "")

            score = parse_score(title)
            idea_text = description
            keywords = fields.get("Keywords", "")
            depth = fields.get("Depth", "quick")
            lang = fields.get("Lang", "en")
            kw_source = fields.get("KW Source", "dictionary")

            # Skip empty descriptions
            if not idea_text or len(idea_text.strip()) < 3:
                skipped += 1
                continue

            h = idea_hash(idea_text)

            # Convert timestamp: "2026-03-06T11:50:29.110000+00:00" → "2026-03-06 11:50:29"
            created = timestamp[:19].replace("T", " ") if timestamp else ""

            # breakdown = empty JSON (not available from Discord)
            breakdown = "{}"

            await client.execute(
                "INSERT INTO score_history "
                "(idea_hash, idea_text, score, breakdown, keywords, depth, lang, keyword_source, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [h, idea_text, score, breakdown, keywords, depth, lang, kw_source, created],
            )
            imported += 1

            if imported % 100 == 0:
                print(f"  ... imported {imported}")

        # Final count
        result = await client.execute("SELECT COUNT(*) FROM score_history")
        total = result.rows[0][0]

        print(f"\nDone! Imported: {imported}, Skipped: {skipped}")
        print(f"Total rows in score_history: {total}")

        # Quick stats
        result = await client.execute(
            "SELECT depth, COUNT(*) as cnt FROM score_history GROUP BY depth"
        )
        print("\nBy depth:")
        for row in result.rows:
            print(f"  {row[0]}: {row[1]}")

        result = await client.execute(
            "SELECT lang, COUNT(*) as cnt FROM score_history GROUP BY lang"
        )
        print("\nBy language:")
        for row in result.rows:
            print(f"  {row[0]}: {row[1]}")


if __name__ == "__main__":
    asyncio.run(main())
