#!/usr/bin/env python
"""One-time / incremental backfill of semantic embeddings for score_history.

Reads every row that has no embedding yet, embeds its idea_text with
text-embedding-3-small, and writes the packed float32 BLOB back. Idempotent and
resumable: it only ever touches rows where embedding IS NULL, so re-running after
an interruption picks up where it left off, and running it on a cron keeps new
rows covered.

Usage:
    OPENAI_API_KEY=...  TURSO_DATABASE_URL=...  TURSO_AUTH_TOKEN=...  \
        python scripts/backfill_embeddings.py [--batch 256] [--dry-run] [--limit N]

Cost: ~$0.02 / 1M tokens. ~10k ideas x ~40 tokens ≈ 400k tokens ≈ $0.01.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

# Make `api` importable when run from repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import db  # noqa: E402
from api.embeddings import EmbeddingError, embed_texts, embeddings_enabled, pack_embedding  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill score_history embeddings.")
    ap.add_argument("--batch", type=int, default=256, help="rows embedded per API call")
    ap.add_argument("--limit", type=int, default=0, help="max rows this run (0 = all)")
    ap.add_argument("--dry-run", action="store_true", help="count only, no API calls / writes")
    args = ap.parse_args()

    if not embeddings_enabled():
        print("ERROR: OPENAI_API_KEY not set — cannot compute embeddings.", file=sys.stderr)
        return 2

    db.init_db()  # ensures the embedding column exists on the target DB

    total_done = 0
    started = time.time()
    while True:
        take = args.batch if args.limit == 0 else min(args.batch, args.limit - total_done)
        if take <= 0:
            break
        rows = db.rows_missing_embedding(limit=take)
        if not rows:
            break

        ids = [r["id"] for r in rows]
        texts = [r["idea_text"] for r in rows]
        print(f"[backfill] {len(rows)} rows (ids {ids[0]}..{ids[-1]})", flush=True)

        if args.dry_run:
            total_done += len(rows)
            continue

        try:
            vectors = embed_texts(texts)
        except EmbeddingError as e:
            print(f"ERROR embedding batch: {e}", file=sys.stderr)
            return 1

        for row_id, vec in zip(ids, vectors):
            db.set_embedding(row_id, pack_embedding(vec))
        total_done += len(rows)

        if args.limit and total_done >= args.limit:
            break

    elapsed = time.time() - started
    verb = "would embed" if args.dry_run else "embedded"
    print(f"[backfill] done — {verb} {total_done} rows in {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
