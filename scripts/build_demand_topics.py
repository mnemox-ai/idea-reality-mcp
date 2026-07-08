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
    # generic startup / product jargon that pollutes labels (appears across many clusters)
    "wedge", "icp", "saas", "b2b", "b2c", "mvp", "poc", "api", "ml", "llm", "gpt",
    "product", "startup", "solution", "software", "service", "services", "auto",
    "automated", "automatically", "small", "team", "teams", "manage", "management",
    # common filler that slips into labels
    "also", "has", "have", "any", "get", "got", "one", "two", "via", "use", "used",
    "way", "per", "out", "off", "all", "its", "not", "but", "each", "own", "who",
}


def _unpack(blob: bytes):
    return struct.unpack(f"<{len(blob) // 4}f", blob)


def _read_all_embedded(chunk: int = 1500):
    """Read (idea_hash, idea_text, created_at, embedding) for every embedded row, in rowid chunks.
    idea_hash is needed to join query_log for distinct-requester heat (anti-poisoning)."""
    rows, last = [], 0
    while True:
        batch = t.execute(
            "SELECT rowid AS rid, idea_hash, idea_text, created_at, embedding FROM score_history "
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


def _load_query_ips(chunk: int = 2500) -> dict:
    """Map idea_hash -> list of (ip_hash, datetime) from query_log.

    This is the anti-poisoning backbone: topic heat is counted as DISTINCT ip_hash (people),
    not raw query rows, so one actor flooding hundreds of queries counts as a single person
    and cannot manufacture a 'rising' trend. (Real data: one ip_hash = 33% of all queries.)"""
    out: dict = {}
    last = 0
    while True:
        batch = t.execute(
            "SELECT id, ip_hash, idea_hash, created_at FROM query_log WHERE id > ? ORDER BY id LIMIT ?",
            [last, chunk],
            timeout=90,
        )
        if not batch:
            break
        for r in batch:
            ih = r.get("idea_hash")
            if not ih:
                continue
            out.setdefault(ih, []).append((r.get("ip_hash"), _parse_ts(r.get("created_at"))))
        last = batch[-1]["id"]
    return out


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


def _tokenize(texts: list[str]) -> Counter:
    words: Counter = Counter()
    for tx in texts:
        for w in "".join(c.lower() if c.isalnum() else " " for c in (tx or "")).split():
            if len(w) > 2 and not w.isdigit() and w not in _STOPWORDS:
                words[w] += 1
    return words


def _assign_labels(topics: list[dict]) -> None:
    """Label each topic by its most DISTINCTIVE terms (tf-idf across all topics).

    Plain frequency makes every cluster read 'wedge / icp / saas' because that jargon is
    everywhere. Weighting term-frequency-in-topic by inverse topic-frequency demotes ubiquitous
    terms and surfaces what actually separates this topic. Mutates topics in place."""
    import math
    per_topic = [_tokenize(tp.get("_samples", [])) for tp in topics]
    df: Counter = Counter()
    for c in per_topic:
        for w in c:
            df[w] += 1
    n = max(len(topics), 1)
    for tp, c in zip(topics, per_topic):
        if not c:
            tp["label"] = "misc"
            continue
        ranked = sorted(c, key=lambda w: c[w] * math.log((n + 1) / (df[w] + 0.5)), reverse=True)
        tp["label"] = " / ".join(ranked[:4]) or "misc"


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

    print("loading query_log IPs (distinct-requester heat)...", flush=True)
    query_ips = _load_query_ips()
    print(f"  idea_hash with IP data: {len(query_ips)}", flush=True)

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
        # Distinct-requester heat (anti-poisoning): count DISTINCT ip_hash per window across
        # this topic's ideas, not raw query rows. One actor flooding queries => 1 person =>
        # can't manufacture a trend. Ideas with no query_log IP simply don't add to the count.
        topic_hashes = {rows[i]["idea_hash"] for i in idx if rows[i].get("idea_hash")}
        cur_ips, prev_ips = set(), set()
        for ih in topic_hashes:
            for ip, dt in query_ips.get(ih, ()):
                if not ip or not dt:
                    continue
                if dt >= cur_start:
                    cur_ips.add(ip)
                elif dt >= prev_start:
                    prev_ips.add(ip)
        cur, prev = len(cur_ips), len(prev_ips)
        topics.append({
            "topic_id": tid,
            "centroid": struct.pack(f"<{len(centroid)}f", *centroid.tolist()),
            "_samples": samples,  # for tf-idf labelling (dropped before write)
            "sample_ideas": json.dumps([s[:120] for s in samples], ensure_ascii=False),
            "member_count": int(len(idx)),
            "searches_90d": cur,   # distinct requesters (people) in the 90d window
            "prev_90d": prev,
            "trend": _trend(cur, prev),
            "updated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        })

    _assign_labels(topics)  # tf-idf across topics -> distinctive labels
    topics.sort(key=lambda x: -x["searches_90d"])
    print(f"built {len(topics)} topics. top by 90d distinct-requester heat:", flush=True)
    for tp in topics[:8]:
        print(f"  [{tp['searches_90d']:4} ppl {tp['trend']:7}] n={tp['member_count']:4} {tp['label']}", flush=True)

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
