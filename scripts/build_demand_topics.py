"""Build the Demand Radar topic index (offline, safe).

Turns the ~10k query-log embeddings into ~100 "demand topics" so the online API can
answer "how hot is this demand space?" by comparing a query to ~100 centroids (<10ms,
<1MB) instead of full-scanning 10k rows (~6s). Also the data floor for the public
Demand Radar feed.

SAFETY (see docs/2026-07-06-demand-radar-offline-clustering.md §8):
- READS score_history in chunks (read-only). NEVER does big DDL / big UPDATE on it.
- WRITES only demand_topics (~100 tiny rows). All heavy compute is here, offline.
- sklearn is used ONLY here; the API stays light (numpy dot products only).

Env: TURSO_DATABASE_URL, TURSO_AUTH_TOKEN (reads/writes over the Turso HTTP client,
which is safe for small statements; each read chunk stays well under the 60s HTTP limit).

Usage:
  export TURSO_DATABASE_URL=... TURSO_AUTH_TOKEN=...
  python scripts/build_demand_topics.py --k 100 [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from collections import Counter
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "scripts")
import turso_http as t  # noqa: E402

WINDOW_DAYS = 90
_STOPWORDS = {
    "a", "an", "the", "to", "for", "of", "and", "or", "with", "that", "this", "app",
    "application", "tool", "platform", "system", "using", "based", "your", "you", "will",
    "can", "in", "on", "it", "is", "are", "be", "my", "we", "i", "want", "create", "build",
    "make", "idea", "users", "user", "people", "new", "like", "helps", "help", "into",
}


def _unpack(blob: bytes):
    return struct.unpack(f"<{len(blob) // 4}f", blob)


def _read_all_embedded(chunk: int = 1500):
    """Read (idea_text, created_at, embedding) for every embedded row, in rowid chunks."""
    rows, last = [], 0
    while True:
        batch = t.execute(
            "SELECT rowid AS rid, idea_text, created_at, embedding FROM score_history "
            "WHERE embedding IS NOT NULL AND rowid > ? ORDER BY rowid LIMIT ?",
            [last, chunk],
            timeout=90,
        )
        if not batch:
            break
        rows.extend(batch)
        last = batch[-1]["rid"]
        print(f"  read {len(rows)}...", flush=True)
    return rows


def _parse_ts(ts):
    if not ts:
        return None
    try:
        return datetime.strptime(str(ts)[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        try:  # tolerate ISO 'T' separator
            return datetime.strptime(str(ts)[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            return None


def _trend(cur: int, prev: int) -> str:
    if cur > prev * 1.25:
        return "rising"
    if cur < prev * 0.75:
        return "cooling"
    return "steady"


def _label(texts: list[str]) -> str:
    words: Counter = Counter()
    for tx in texts:
        for w in "".join(c.lower() if c.isalnum() else " " for c in (tx or "")).split():
            if len(w) > 2 and w not in _STOPWORDS:
                words[w] += 1
    top = [w for w, _ in words.most_common(4)]
    return " / ".join(top) if top else (texts[0][:40] if texts else "misc")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=100)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    import numpy as np
    from sklearn.cluster import MiniBatchKMeans

    print("reading embedded rows...", flush=True)
    rows = _read_all_embedded()
    n = len(rows)
    print(f"read {n} embedded rows", flush=True)
    if n < args.k:
        print(f"not enough rows ({n}) for k={args.k}; aborting")
        return

    mat = np.array([_unpack(r["embedding"]) for r in rows], dtype=np.float32)
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    mat = mat / norms  # L2 normalize -> euclidean kmeans approximates cosine

    print(f"clustering k={args.k}...", flush=True)
    km = MiniBatchKMeans(n_clusters=args.k, random_state=42, batch_size=1024, n_init=3)
    labels = km.fit_predict(mat)

    now = datetime.now(timezone.utc)
    cur_start = now - timedelta(days=WINDOW_DAYS)
    prev_start = now - timedelta(days=2 * WINDOW_DAYS)

    # aggregate per topic (in memory — no per-row writes to the big table)
    topics = []
    for tid in range(args.k):
        idx = np.where(labels == tid)[0]
        if len(idx) == 0:
            continue
        centroid = mat[idx].mean(axis=0)
        cn = np.linalg.norm(centroid)
        centroid = centroid / (cn if cn else 1.0)  # store unit-norm -> query-time dot == cosine
        # nearest members to centroid for labelling
        sims = mat[idx] @ centroid
        order = idx[np.argsort(-sims)]
        samples = [rows[i]["idea_text"] for i in order[:5] if rows[i]["idea_text"]]
        cur = prev = 0
        for i in idx:
            dt = _parse_ts(rows[i]["created_at"])
            if not dt:
                continue
            if dt >= cur_start:
                cur += 1
            elif dt >= prev_start:
                prev += 1
        topics.append({
            "topic_id": tid,
            "centroid": struct.pack(f"<{len(centroid)}f", *centroid.tolist()),
            "label": _label(samples),
            "sample_ideas": json.dumps([s[:120] for s in samples], ensure_ascii=False),
            "member_count": int(len(idx)),
            "searches_90d": cur,
            "prev_90d": prev,
            "trend": _trend(cur, prev),
            "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        })

    topics.sort(key=lambda x: -x["searches_90d"])
    print(f"built {len(topics)} topics. top by 90d heat:", flush=True)
    for tp in topics[:8]:
        print(f"  [{tp['searches_90d']:4}↑{tp['trend']:7}] n={tp['member_count']:4} {tp['label']}", flush=True)

    if args.dry_run:
        print("dry-run: not writing demand_topics")
        return

    # write: small table, safe. rebuild whole table each run (idempotent).
    t.execute(
        "CREATE TABLE IF NOT EXISTS demand_topics ("
        "topic_id INTEGER PRIMARY KEY, centroid BLOB NOT NULL, label TEXT, sample_ideas TEXT, "
        "member_count INTEGER, searches_90d INTEGER, prev_90d INTEGER, trend TEXT, updated_at TEXT)"
    )
    t.execute("DELETE FROM demand_topics")
    for tp in topics:
        t.execute(
            "INSERT INTO demand_topics(topic_id, centroid, label, sample_ideas, member_count, "
            "searches_90d, prev_90d, trend, updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
            [tp["topic_id"], tp["centroid"], tp["label"], tp["sample_ideas"], tp["member_count"],
             tp["searches_90d"], tp["prev_90d"], tp["trend"], tp["updated_at"]],
        )
    print(f"wrote {len(topics)} rows to demand_topics", flush=True)


if __name__ == "__main__":
    main()
