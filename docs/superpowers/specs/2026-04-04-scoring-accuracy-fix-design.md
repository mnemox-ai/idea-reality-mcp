# Scoring Accuracy Fix — Design Spec

**Date:** 2026-04-04
**Status:** Draft
**Scope:** Fix 3 bugs causing systematic score underestimation

## Problem

Known red-ocean ideas score green/yellow instead of red:

| Idea | Expected | Actual | Gap |
|------|----------|--------|-----|
| Todo list app | 80+ | 35 | -45 |
| Expense tracker | 70+ | 40 | -30 |
| AI chatbot | 80+ | 69 | -11 |

Root cause: 3 independent bugs compound to suppress scores by 30-50 points.

**Critical insight**: Bad keywords from Bug 1 affect ALL sources (GitHub, npm, SO), not just GitHub. The 45-point gap for "todo list" comes from GitHub (31%) + npm getting irrelevant results + SO missing. Fixing keyword quality lifts the entire scoring pipeline.

## Bug 1 (P0): Keyword Quality — GitHub Returns 0

### Problem

Dictionary keyword extraction generates compound queries like `"productivity list todo"` that GitHub search can't match. For "todo list app", GitHub returns **0 repos**, zeroing out 31% of the score weight (22% repos + 9% stars).

The current flow in `tools.py`:
1. `extract_keywords(idea_text)` — dictionary pipeline (always runs)
2. If `idea_text < 15 words` → `expand_idea()` via Render API (LLM)
3. If expansion succeeds → re-extract keywords from `expanded_description`

The dictionary pipeline (`engine.py` L232-388) splits input into tokens, detects intent anchors from `synonyms.py`, then generates 3-8 query templates. The template logic recombines tokens in orders that don't match real GitHub repo names.

### Fix: LLM-First Keyword Generation

**Change `tools.py`** to call LLM keyword extraction FIRST (not just expansion), with dictionary as fallback:

```
1. Try expand_idea() (existing, gets core_concept + differentiator)
2. Try extract_keywords_llm() (existing, gets 3-8 search queries)
3. If both succeed → use LLM keywords + expansion platform queries
4. If only expansion succeeds → use extract_keywords(expanded_description)
5. If both fail → use extract_keywords(idea_text) (dictionary fallback)
```

**Enhance LLM prompt** (server-side `api/main.py` `/api/extract-keywords` endpoint):
- Add instruction: "Generate keywords optimized for GitHub repository search and npm package search"
- Add instruction: "Include common synonyms (e.g., 'todo' → also generate 'task manager', 'checklist')"
- Add instruction: "Each keyword should be 2-3 words, matching how developers name repos"

**Remove the `< 15 words` gate** — all ideas should benefit from LLM expansion regardless of length.

**Add synonym fallback in dictionary mode** — for when LLM is unavailable:
- Add `KEYWORD_SYNONYMS` dict to `synonyms.py`:
  ```python
  KEYWORD_SYNONYMS = {
      "todo": ["task manager", "checklist", "to-do list"],
      "expense": ["budget tracker", "finance manager", "money tracker"],
      "chat": ["messaging", "instant messaging", "real-time chat"],
      "auth": ["authentication", "login", "identity"],
      ...
  }
  ```
- After dictionary extraction, expand each keyword with its synonyms
- Cap total queries at 8 (existing limit)

### Files Changed
- `src/idea_reality_mcp/tools.py` — reorder LLM/dictionary priority, remove word count gate
- `src/idea_reality_mcp/scoring/synonyms.py` — add `KEYWORD_SYNONYMS` dict
- `src/idea_reality_mcp/scoring/engine.py` — use synonyms in fallback path
- `api/main.py` — enhance `/api/extract-keywords` prompt

### Success Criteria
- "todo list app" → GitHub finds 1000+ repos → competition_density ≥ 90
- "expense tracker" → GitHub finds 500+ repos → competition_density ≥ 80
- **Composite score**: "todo list app" deep mode `reality_signal` ≥ 70
- **Composite score**: "AI chatbot customer service" deep mode `reality_signal` ≥ 75
- Dictionary fallback still generates reasonable queries when LLM is down

### Latency Consideration
Removing the `< 15 words` gate means every call hits Render API (expand + extract). With cold-start Render free tier, worst case is 16s. Mitigation:
- Run `expand_idea()` and `extract_keywords_llm()` in parallel via `asyncio.gather()`
- Set aggressive timeout (5s instead of 8s) — dictionary fallback is fast
- If LLM path takes > 5s, dictionary result is already available as fallback

---

## Bug 2 (P1): PyPI Always Returns 0

### Problem

`pypi.py` scrapes `pypi.org/search/` HTML with regex `<strong>{count}</strong> project`. PyPI now uses client-side JS rendering — httpx gets empty HTML. Every query returns `count = 0`.

### Fix: Two-Tier PyPI Search

**Tier 1 (keyless, always available)**: PyPI Simple JSON API
- Endpoint: `GET https://pypi.org/simple/` — returns full package index (PEP 503)
- For each keyword, check if exact package name exists via `GET https://pypi.org/pypi/{keyword}/json`
- Also try hyphenated variants: `"todo app"` → check `todo-app`, `todoapp`
- Returns: count of matching packages + metadata (version, summary, etc.)
- Limitation: exact match only, no fuzzy search — but non-zero for real packages

**Tier 2 (with key, enhanced)**: libraries.io API
- Endpoint: `GET https://libraries.io/api/search?q={keyword}&platforms=pypi&api_key={key}`
- Returns: total count + full search results
- Env var: `LIBRARIES_IO_KEY` (free registration, 60 req/min)

**Logic**:
```python
async def search_pypi(keywords: list[str]) -> PyPIResults:
    lib_key = os.environ.get("LIBRARIES_IO_KEY")
    if lib_key:
        return await _search_libraries_io(keywords, lib_key)
    else:
        return await _search_pypi_json(keywords)  # keyless fallback
```

This ensures MCP stdio users (no env vars) still get non-zero PyPI data.

**Add `skipped` field** to `PyPIResults` dataclass (matching `ProductHuntResults` pattern) — only True if both tiers fail.

**Update `engine.py`** weight redistribution to handle PyPI skip (same pattern as PH at L682-695).

### Files Changed
- `src/idea_reality_mcp/sources/pypi.py` — rewrite with two-tier approach
- `src/idea_reality_mcp/scoring/engine.py` — add PyPI weight redistribution when skipped

### Success Criteria
- **Without any key**: "flask" → PyPI count ≥ 1 (exact match works)
- **With LIBRARIES_IO_KEY**: "web framework" → PyPI count > 0 (fuzzy search)
- Graceful skip if both fail, weight redistributed, no crash
- Existing tests updated to mock both tiers

---

## Bug 3 (P1): Stack Overflow Hardening

### Problem — Verified Root Cause

Debug confirmed: SO API **works correctly** — `search_stackoverflow(["todo app", "task manager"])` returns 11 questions with proper evidence. The code path in `tools.py` and `engine.py` is correct.

The earlier test results missing `developer_interest` from sub_scores were likely due to:
1. SO API rate limiting (300 req/day free tier) during high-traffic testing
2. The `backoff` field in SO API responses is not handled — when throttled, subsequent queries in the same batch silently fail

### Fix: Harden SO Against Rate Limiting

1. **Handle `backoff` field** — SO API returns `{"backoff": N}` when throttled. If present, skip remaining queries in the batch instead of silently failing.
2. **Handle `error_id` / `error_message`** — API error responses have these fields. Currently only `httpx.HTTPError` is caught; JSON-level errors are not.
3. **Add `skipped: bool = False`** to `StackOverflowResults` — consistent with PH/PyPI pattern for weight redistribution.
4. **Broader exception handling** — add `except Exception` fallback to prevent unhandled errors from crashing `asyncio.gather()`.

### Files Changed
- `src/idea_reality_mcp/sources/stackoverflow.py` — backoff handling, error_id check, skipped field, broader exception catch
- `src/idea_reality_mcp/scoring/engine.py` — update SO availability check to also check `not so_results.skipped`

### Success Criteria
- SO evidence appears in deep mode results when not rate-limited
- `developer_interest` sub_score is always present in deep mode output
- When rate-limited: graceful skip, weight redistributed, no crash or silent failure

---

## Testing Strategy

### Unit Tests
- **Keyword quality**: Golden set of 10 well-known ideas, assert GitHub-appropriate keywords generated
- **PyPI mock**: Mock libraries.io responses, verify count parsing
- **SO mock**: Mock SE API responses including rate-limit and error scenarios
- **Weight redistribution**: Test all combinations of skipped sources

### Integration Tests
- Run actual `idea_check("todo list app", depth="deep")` → assert signal ≥ 60
- Run actual `idea_check("AI chatbot customer service", depth="deep")` → assert signal ≥ 70

### Regression
- All existing 277 tests must pass
- Run the 3 benchmark ideas before/after and compare scores

---

## Non-Goals

- Product Hunt token setup (deferred)
- Score threshold (green/yellow/red boundary) adjustment — fix data first, then calibrate
- Quick mode changes — focus on deep mode accuracy first
- New data sources

---

## Version

This will be released as **v0.5.1** (patch — bug fixes only, no new features).
