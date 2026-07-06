#!/usr/bin/env python
"""Backfill score_history embeddings over the Turso HTTP API.

Same job as backfill_embeddings.py, but talks to Turso via /v2/pipeline instead of
the libsql sync client (which hangs on Windows). Idempotent/resumable: only touches
rows where embedding IS NULL.

Usage:
    TURSO_DATABASE_URL=… TURSO_AUTH_TOKEN=… OPENAI_API_KEY=… \
        python scripts/backfill_embeddings_http.py [--batch 512] [--limit N] [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.embeddings import EmbeddingError, embed_texts, embeddings_enabled, pack_embedding  # noqa: E402
from scripts import turso_http as t  # noqa: E402


def _missing_count() -> int:
    return t.execute(
        "SELECT COUNT(*) AS n FROM score_history "
        "WHERE embedding IS NULL AND idea_text IS NOT NULL AND length(idea_text) > 0"
    )[0]["n"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int, default=512, help="rows per embed+write cycle")
    ap.add_argument("--limit", type=int, default=0, help="max rows this run (0 = all)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not embeddings_enabled():
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        return 2

    total_missing = _missing_count()
    cap = total_missing if args.limit == 0 else min(total_missing, args.limit)
    est = cap * 40
    print(f"[http-backfill] {total_missing} rows missing embedding; will embed {cap} "
          f"(~{est:,} tokens, approx ${est / 1_000_000 * 0.02:.4f})")
    if args.dry_run:
        return 0

    done = 0
    started = time.time()
    while done < cap:
        take = min(args.batch, cap - done)
        rows = t.execute(
            "SELECT id, idea_text FROM score_history "
            "WHERE embedding IS NULL AND idea_text IS NOT NULL AND length(idea_text) > 0 "
            "ORDER BY id ASC LIMIT ?",
            [take],
        )
        if not rows:
            break
        ids = [r["id"] for r in rows]
        texts = [r["idea_text"] for r in rows]
        try:
            vectors = embed_texts(texts)
        except EmbeddingError as e:
            print(f"ERROR embedding batch (ids {ids[0]}..{ids[-1]}): {e}", file=sys.stderr)
            return 1
        writes = [
            ("UPDATE score_history SET embedding=? WHERE id=?", [pack_embedding(v), rid])
            for rid, v in zip(ids, vectors)
        ]
        t.execute_many(writes)
        done += len(rows)
        rate = done / max(time.time() - started, 0.001)
        print(f"[http-backfill] {done}/{cap} (ids {ids[0]}..{ids[-1]}) {rate:.0f} rows/s", flush=True)

    print(f"[http-backfill] done — embedded {done} rows in {time.time() - started:.1f}s; "
          f"remaining missing = {_missing_count()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
