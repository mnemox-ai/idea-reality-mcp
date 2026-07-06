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

### ☐ Next (this phase)
2. **Wire semantic search into the scorer** — in the `top_similars` /
   `existingProjects` path (tools.py / api/main.py `/api/check`): embed the incoming
   idea, call `search_similar_by_embedding`, fall back to `search_similar_ideas`
   on `[]` or provider error. Store the new check's embedding via `save_score(embedding=)`.
3. **Deploy** — Render redeploy (requirements now include numpy + libsql-client);
   set `OPENAI_API_KEY` in Render env.
4. **Demand-heat signal (the unique output)** — "N people queried a *semantically*
   similar idea in the last 90 days, trend ↑". New helper over the embedded corpus +
   `created_at`; surface it to flip the verdict from "judgment" ("5 people already
   built this → you lose") to "navigation" ("crowded, but 23 searched in 90d → gap here").

## Decisions
- Provider `text-embedding-3-small` (1536-d, cheap, httpx). Swap to `-large` only if
  dedup quality demands it.
- Storage = packed float32 BLOB + brute-force NumPy cosine. Portable Turso/SQLite,
  fine < ~100k rows. Beyond that → Turso native `F32_BLOB` + `vector_distance_cos`
  index (blob format is already forward-compatible).
- Keep the log-curve reality score as-is — it's the explainable trust asset. Embeddings
  only improve *similarity/dedup*, not the score formula.
