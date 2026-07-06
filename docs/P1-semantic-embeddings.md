# P1 — Semantic Embeddings (activate the query-log moat)

**Why**: `search_similar_ideas` matched on keyword LIKE — it misses paraphrases
("split bills with roommates" vs "expense sharing app"). The **10,150 rows /
8,337 distinct ideas** in `score_history` on Turso (confirmed 2026-07-06 via the
Turso HTTP API; also surfaced by `/api/stats` `total_ideas_scanned`) are the
engine's only proprietary asset; embeddings turn them from a keyword table into a
semantic index.

> ⚠️ Gotcha: `api/db.py` **silently** falls back to a local empty SQLite when
> `libsql_client` is missing OR Turso env vars are unset (only a log warning).
> Any local script must `pip install libsql-client` AND export `TURSO_*`, or it
> will operate on the wrong DB and report bogus counts. The local libsql *sync*
> client also hung here (Windows) — the Turso **HTTP API** (`https://<db>/v2/pipeline`)
> works and is the reliable path for the backfill / analysis from this machine.

## Status

### ✅ Done (branch `feat/semantic-embeddings`, PR pending)
- **`api/embeddings.py`** — batch embed client (OpenAI `text-embedding-3-small`,
  httpx, no SDK) + `pack_embedding`/`unpack_embedding` (float32 BLOB).
- **`api/db.py`** — `embedding BLOB` column (+ idempotent ALTER for the live table),
  `save_score(embedding=)`, `set_embedding`, `rows_missing_embedding`,
  `count_missing_embedding`, `search_similar_by_embedding` (cosine, `min_score`,
  returns `[]` so callers fall back to keyword search).
- **`scripts/backfill_embeddings.py`** — idempotent/resumable backfill
  (`--dry-run` cost estimate, `--limit`, `--batch`).
- **tests** — 12/12 green in `test_score_history.py` (roundtrip, legacy-table
  migration, semantic ranking, backfill flow, empty/zero-vector edges).

### ✅ Backfill DONE (2026-07-06)
- prod Turso `score_history`: **10,150 / 10,150 embedded (0 missing)** via
  `scripts/backfill_embeddings_http.py` (Turso HTTP API — the sync client hangs).
  ~14 min, 12 rows/s, ~$0.008.
- Verified: stored-vs-fresh cosine = 1.0000 (correct text stored); real semantic
  queries return paraphrase matches keyword-LIKE would miss (e.g. "split bills with
  roommates" → "Group expense app that scans receipts" 0.74).
- Real data also confirms **duplicate ideas** (same idea_hash from repeat queries) →
  the scorer wiring must dedup results by `idea_hash`.
- Re-run the same script on a cron / after new checks to keep coverage (idempotent).

### ✅ Wiring + demand-heat DONE (2026-07-06, on origin/main @ b191cce, Render deploying)
- `report._build_crowd_intelligence` (full report) + `/api/crowd-intel` now go
  semantic-first via `_similar_ideas` (embed → `search_similar_by_embedding`, dedup by
  idea_hash, min_score 0.45), keyword LIKE fallback on any failure = zero regression.
- `_demand_heat`: closely-related searches in the last 90d + trend (rising/steady/cooling),
  FACTS-only. Added as `demand_heat` + `match_mode` fields.
- Perf: in-memory normalized embedding matrix cache (`EMB_CACHE_TTL=600`) + vectorized
  cosine — no 60 MB blob load per request.
- Integration-verified locally (zero-keyword-overlap paraphrase matches; graceful fallback);
  12/12 unit tests green.
- NOTE: `/api/check` (lean) does NOT carry crowd_intelligence — the semantic upgrade lands
  in the full report path + `/api/crowd-intel` (the correct "who else searched this" home).
  top_similars = external products, unchanged.

### 🔑 ACTION REQUIRED (Sean) — the last switch
- **Set `OPENAI_API_KEY` in the Render dashboard.** Until set, crowd gracefully falls back
  to keyword (today's behaviour, zero risk). Once set, the next request loads the 10,150-row
  semantic index → `match_mode: "semantic"` + `demand_heat` appear. numpy + libsql-client are
  already in requirements; render.yaml declares the key + `EMB_CACHE_TTL`.
- Verify after setting: `POST /api/crowd-intel` with a real idea_hash → expect
  `match_mode: "semantic"`.

### ☐ Optional follow-ups (not blocking)
- Store new-check embeddings inline (currently the cron backfill covers new rows).
- Cron the backfill (`scripts/backfill_embeddings_http.py`, idempotent) to keep coverage.

## Decisions
- Provider `text-embedding-3-small` (1536-d, cheap, httpx). Swap to `-large` only if
  dedup quality demands it.
- Storage = packed float32 BLOB + brute-force NumPy cosine. Portable Turso/SQLite,
  fine < ~100k rows. Beyond that → Turso native `F32_BLOB` + `vector_distance_cos`
  index (blob format is already forward-compatible).
- Keep the log-curve reality score as-is — it's the explainable trust asset. Embeddings
  only improve *similarity/dedup*, not the score formula.
