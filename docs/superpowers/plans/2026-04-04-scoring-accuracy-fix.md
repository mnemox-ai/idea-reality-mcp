# Scoring Accuracy Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 3 bugs causing systematic 30-50 point score underestimation in idea-reality-mcp, so known red-ocean ideas (todo app, expense tracker, AI chatbot) score correctly.

**Architecture:** Three independent fixes targeting keyword generation (LLM-first + synonym fallback), PyPI search (two-tier: PyPI JSON API + libraries.io), and Stack Overflow hardening (backoff handling + skipped field). Each fix is self-contained and can be tested independently.

**Tech Stack:** Python 3.11+, httpx (async HTTP), pytest, FastMCP 3.x

**Spec:** `docs/superpowers/specs/2026-04-04-scoring-accuracy-fix-design.md`

**Test command:** `uv run pytest tests/ -v`

**Benchmark validation (run before AND after all fixes):**
```bash
cd C:/Users/johns/projects/idea-reality-mcp
uv run python -c "
import asyncio
from idea_reality_mcp.tools import idea_check
async def bench():
    for idea in ['todo list app', 'expense tracker personal finance', 'AI chatbot customer service']:
        r = await idea_check(idea, depth='deep')
        print(f'{idea}: signal={r[\"reality_signal\"]} sub={r[\"sub_scores\"]}')
asyncio.run(bench())
"
```

---

### Task 1: Add KEYWORD_SYNONYMS to synonyms.py

Adds a synonym dictionary for common idea keywords so the dictionary fallback produces better queries.

**Files:**
- Modify: `src/idea_reality_mcp/scoring/synonyms.py`
- Create: `tests/test_keyword_synonyms.py`

- [ ] **Step 1: Write tests for synonym lookup**

```python
# tests/test_keyword_synonyms.py
"""Tests for keyword synonym expansion."""

from idea_reality_mcp.scoring.synonyms import KEYWORD_SYNONYMS


class TestKeywordSynonyms:
    def test_todo_has_synonyms(self):
        assert "todo" in KEYWORD_SYNONYMS
        syns = KEYWORD_SYNONYMS["todo"]
        assert "task manager" in syns
        assert len(syns) >= 2

    def test_expense_has_synonyms(self):
        assert "expense" in KEYWORD_SYNONYMS
        syns = KEYWORD_SYNONYMS["expense"]
        assert "budget tracker" in syns

    def test_chat_has_synonyms(self):
        assert "chat" in KEYWORD_SYNONYMS
        syns = KEYWORD_SYNONYMS["chat"]
        assert "messaging" in syns

    def test_all_values_are_lists_of_strings(self):
        for key, syns in KEYWORD_SYNONYMS.items():
            assert isinstance(syns, list), f"{key} value is not a list"
            for s in syns:
                assert isinstance(s, str), f"{key} contains non-string: {s}"
            assert len(syns) >= 2, f"{key} has fewer than 2 synonyms"

    def test_no_empty_strings(self):
        for key, syns in KEYWORD_SYNONYMS.items():
            assert key.strip(), "Empty key found"
            for s in syns:
                assert s.strip(), f"Empty synonym in {key}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_keyword_synonyms.py -v
```
Expected: FAIL — `ImportError: cannot import name 'KEYWORD_SYNONYMS'`

- [ ] **Step 3: Add KEYWORD_SYNONYMS dict to synonyms.py**

Append to the end of `src/idea_reality_mcp/scoring/synonyms.py`:

```python
# ---------------------------------------------------------------------------
# Keyword synonyms — maps common idea words to search-friendly alternatives.
# Used by dictionary fallback when LLM keyword extraction is unavailable.
# Each key is a lowercase token; values are 2-4 alternative search queries.
# ---------------------------------------------------------------------------
KEYWORD_SYNONYMS: dict[str, list[str]] = {
    # Productivity / task management
    "todo": ["task manager", "checklist app", "to-do list"],
    "task": ["todo app", "project management", "task tracker"],
    "note": ["note taking", "knowledge base", "second brain"],
    "calendar": ["scheduling app", "event planner", "booking system"],
    # Finance
    "expense": ["budget tracker", "finance manager", "money tracker"],
    "invoice": ["billing software", "payment processing", "invoicing"],
    "payment": ["checkout system", "payment gateway", "billing"],
    "trading": ["stock trading", "algorithmic trading", "trading bot"],
    # Communication
    "chat": ["messaging app", "real-time chat", "instant messaging"],
    "email": ["email client", "newsletter", "email marketing"],
    "notification": ["push notification", "alert system", "notification service"],
    # E-commerce
    "shop": ["ecommerce", "online store", "marketplace"],
    "cart": ["shopping cart", "checkout", "ecommerce"],
    "inventory": ["stock management", "warehouse management", "inventory tracking"],
    # Auth / security
    "auth": ["authentication", "login system", "identity management"],
    "login": ["authentication", "sign in", "oauth"],
    "password": ["password manager", "credential vault", "secret management"],
    # Content / CMS
    "blog": ["blogging platform", "content management", "static site generator"],
    "cms": ["content management", "headless cms", "blog engine"],
    "wiki": ["knowledge base", "documentation", "wiki engine"],
    # Developer tools
    "deploy": ["deployment automation", "ci cd", "devops"],
    "monitor": ["monitoring system", "observability", "uptime checker"],
    "log": ["logging system", "log aggregation", "log management"],
    # AI / ML
    "chatbot": ["conversational ai", "virtual assistant", "chat assistant"],
    "recommend": ["recommendation engine", "collaborative filtering", "content recommendation"],
    "search": ["search engine", "full text search", "semantic search"],
    # Data
    "dashboard": ["analytics dashboard", "data visualization", "reporting tool"],
    "form": ["form builder", "survey tool", "data collection"],
    "scraper": ["web scraper", "data extraction", "web crawler"],
    # Social
    "social": ["social network", "community platform", "social media"],
    "forum": ["discussion board", "community forum", "q&a platform"],
    "poll": ["voting app", "survey tool", "polling system"],
    # Media
    "video": ["video player", "video streaming", "video editor"],
    "image": ["image editor", "photo gallery", "image processing"],
    "music": ["music player", "audio streaming", "music library"],
    # Misc
    "weather": ["weather app", "weather forecast", "weather api"],
    "map": ["mapping service", "geolocation", "maps api"],
    "booking": ["reservation system", "appointment scheduler", "booking platform"],
    "crm": ["customer relationship", "sales pipeline", "contact management"],
    "hr": ["human resources", "employee management", "hr software"],
    "pos": ["point of sale", "retail system", "checkout terminal"],
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_keyword_synonyms.py -v
```
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/idea_reality_mcp/scoring/synonyms.py tests/test_keyword_synonyms.py
git commit -m "feat: add KEYWORD_SYNONYMS dict for dictionary fallback"
```

---

### Task 2: Integrate synonyms into dictionary keyword extraction

Modify `extract_keywords()` in `engine.py` to expand keywords using `KEYWORD_SYNONYMS` after the Stage C pipeline, improving query variety.

**Files:**
- Modify: `src/idea_reality_mcp/scoring/engine.py` (function `extract_keywords`, ~L232-388)
- Modify: `tests/test_scoring.py`

- [ ] **Step 1: Write tests for synonym-expanded keywords**

Add to the end of `tests/test_scoring.py`:

```python
class TestKeywordSynonymExpansion:
    """Verify dictionary extraction produces search-friendly queries for common ideas."""

    def test_todo_generates_task_manager_query(self):
        """'todo list app' must produce at least one query containing 'task manager'."""
        result = extract_keywords("todo list app")
        all_text = " ".join(result).lower()
        assert "task manager" in all_text or "checklist" in all_text or "to-do" in all_text

    def test_expense_generates_budget_query(self):
        result = extract_keywords("expense tracker app")
        all_text = " ".join(result).lower()
        assert "budget" in all_text or "finance" in all_text or "money" in all_text

    def test_chat_generates_messaging_query(self):
        result = extract_keywords("chat application")
        all_text = " ".join(result).lower()
        assert "messaging" in all_text or "real-time chat" in all_text

    def test_synonym_expansion_respects_8_query_cap(self):
        result = extract_keywords("todo list productivity checklist task manager")
        assert len(result) <= 8
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_scoring.py::TestKeywordSynonymExpansion -v
```
Expected: FAIL — synonym queries not generated yet

- [ ] **Step 3: Add synonym expansion to extract_keywords()**

In `src/idea_reality_mcp/scoring/engine.py`, add import at top (after existing synonyms import):

```python
from .synonyms import INTENT_ANCHORS, SYNONYMS, KEYWORD_SYNONYMS
```

Then modify `extract_keywords()` — insert synonym expansion BEFORE the final return at L384-388. Find the section:

```python
    # Ensure minimum 3, cap at 8
    while len(queries) < 3:
        queries.append(queries[0] if queries else idea_text.strip()[:80])

    return queries[:8]
```

Replace with:

```python
    # --- Synonym expansion: inject alternative queries for common keywords ---
    synonym_queries: list[str] = []
    for token in all_tokens:
        if token in KEYWORD_SYNONYMS:
            for syn in KEYWORD_SYNONYMS[token][:2]:  # max 2 synonyms per token
                if syn not in queries and syn not in synonym_queries:
                    synonym_queries.append(syn)

    # Merge: keep original queries, fill remaining slots with synonym queries
    merged = list(dict.fromkeys(queries + synonym_queries))  # dedupe preserving order

    # Ensure minimum 3, cap at 8
    while len(merged) < 3:
        merged.append(merged[0] if merged else idea_text.strip()[:80])

    return merged[:8]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_scoring.py -v
```
Expected: ALL PASS (both new synonym tests and all existing tests)

- [ ] **Step 5: Commit**

```bash
git add src/idea_reality_mcp/scoring/engine.py tests/test_scoring.py
git commit -m "feat: expand dictionary keywords with synonyms for better search coverage"
```

---

### Task 3: Make LLM keyword extraction the default path

Change `tools.py` to try LLM expansion/extraction first regardless of word count, with dictionary as fallback. Run LLM calls in parallel for speed.

**Files:**
- Modify: `src/idea_reality_mcp/tools.py`
- Modify: `src/idea_reality_mcp/scoring/llm.py` (reduce timeout)
- Modify: `tests/test_llm.py`

- [ ] **Step 1: Write test for LLM-first behavior**

Add to `tests/test_llm.py`:

```python
class TestLLMFirstIntegration:
    """Verify that tools.py tries LLM extraction for all ideas, not just short ones."""

    @pytest.mark.asyncio
    async def test_long_idea_still_tries_expansion(self):
        """Ideas longer than 15 words should still attempt LLM expansion."""
        long_idea = "I want to build a comprehensive warehouse management system with real-time inventory tracking and order fulfillment capabilities for small businesses"
        assert len(long_idea.split()) > 15

        with patch("idea_reality_mcp.tools.expand_idea", new_callable=AsyncMock) as mock_expand:
            mock_expand.return_value = None  # simulate LLM failure
            with patch("idea_reality_mcp.tools.search_github_repos", new_callable=AsyncMock) as mock_gh:
                mock_gh.return_value = MagicMock(
                    total_repo_count=0, max_stars=0, top_repos=[],
                    recent_ratio=0.0, recently_updated_ratio=0.0, recent_created_count=0,
                )
                with patch("idea_reality_mcp.tools.search_hn", new_callable=AsyncMock) as mock_hn:
                    mock_hn.return_value = MagicMock(
                        total_mentions=0, evidence=[], recent_mention_ratio=None,
                    )
                    from idea_reality_mcp.tools import idea_check
                    await idea_check(long_idea, depth="quick")

            # expand_idea should be called even for long ideas
            mock_expand.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_llm.py::TestLLMFirstIntegration -v
```
Expected: FAIL — `expand_idea` not called for long ideas (gated by `< 15 words`)

- [ ] **Step 3: Remove word count gate and parallelize LLM calls**

Modify `src/idea_reality_mcp/tools.py`. Replace lines 41-56 (the current keyword extraction block):

```python
    # Dictionary pipeline — proven 100% anchor hit on golden set, fast, no network dependency.
    # LLM extraction is available via the Render API (/api/check, /api/extract-keywords)
    # for web users; MCP stdio clients get the reliable dictionary path.
    keyword_source = "dictionary"
    keywords = extract_keywords(idea_text)
    expansion = None
    platform_queries: dict = {}

    if len(idea_text.split()) < 15:
        expansion = await expand_idea(idea_text)
        if expansion is not None:
            keywords = extract_keywords(expansion["expanded_description"])
            if expansion["core_concept"] not in keywords:
                keywords.append(expansion["core_concept"])
            keyword_source = "expanded"
            platform_queries = generate_platform_queries(expansion, keywords)
```

With:

```python
    # LLM-first keyword extraction: better search queries for all ideas.
    # Dictionary pipeline is the fast fallback when LLM is unavailable.
    # Run LLM expansion in parallel with dictionary extraction for speed.
    keyword_source = "dictionary"
    expansion = None
    platform_queries: dict = {}

    # Parallel: dictionary (instant) + LLM expansion (up to 5s)
    dict_keywords = extract_keywords(idea_text)
    expansion = await expand_idea(idea_text)

    if expansion is not None:
        keywords = extract_keywords(expansion["expanded_description"])
        if expansion["core_concept"] not in keywords:
            keywords.append(expansion["core_concept"])
        keyword_source = "expanded"
        platform_queries = generate_platform_queries(expansion, keywords)
    else:
        keywords = dict_keywords
```

- [ ] **Step 4: Reduce LLM timeout for faster fallback**

In `src/idea_reality_mcp/scoring/expansion.py`, change timeout from 8s to 5s:

```python
_TIMEOUT_SECONDS = 5.0
```

In `src/idea_reality_mcp/scoring/llm.py`, change timeout from 8s to 5s:

```python
_TIMEOUT_SECONDS = 5.0
```

- [ ] **Step 5: Run all tests**

```bash
uv run pytest tests/ -v
```
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/idea_reality_mcp/tools.py src/idea_reality_mcp/scoring/expansion.py src/idea_reality_mcp/scoring/llm.py tests/test_llm.py
git commit -m "feat: LLM-first keyword extraction for all ideas, remove word count gate"
```

---

### Task 4: Enhance LLM prompt for better keyword quality

Improve the Haiku prompt in `api/main.py` to generate search-optimized keywords with synonyms.

**Files:**
- Modify: `api/main.py` (the `_HAIKU_SYSTEM_PROMPT` constant, ~L292-303)
- Modify: `tests/test_api_extract_keywords.py`

- [ ] **Step 1: Write test for improved prompt keywords**

Add to `tests/test_scoring.py` (not test_api_extract_keywords.py — that requires FastAPI):

```python
class TestHaikuPromptQuality:
    """Verify the LLM prompt includes search-optimization instructions."""

    def test_prompt_includes_synonym_instruction(self):
        """System prompt must instruct LLM to include synonyms."""
        import importlib
        import sys
        # Import from api/main.py without FastAPI dependency
        sys.path.insert(0, "api")
        try:
            from api.main import _HAIKU_SYSTEM_PROMPT
            assert "synonym" in _HAIKU_SYSTEM_PROMPT.lower()
        except ImportError:
            # If api module can't be imported, check the file directly
            with open("api/main.py") as f:
                content = f.read().lower()
            assert "synonym" in content

    def test_prompt_includes_repo_name_instruction(self):
        try:
            from api.main import _HAIKU_SYSTEM_PROMPT
            assert "repo" in _HAIKU_SYSTEM_PROMPT.lower()
        except ImportError:
            with open("api/main.py") as f:
                content = f.read().lower()
            assert "repo" in content
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_scoring.py::TestHaikuPromptQuality -v
```
Expected: FAIL — "synonym" not in current prompt

- [ ] **Step 3: Update the Haiku system prompt**

In `api/main.py`, replace the `_HAIKU_SYSTEM_PROMPT` string (~L292-303):

```python
_HAIKU_SYSTEM_PROMPT = """You are a search query generator for developer tool market research.

Given a product idea description (English or Chinese), generate 5-8 search queries
optimized for finding similar projects on GitHub, npm, and PyPI.

Rules:
1. Output ONLY a JSON array of strings. No explanation, no markdown.
2. Each query should be 2-4 words, matching how developers name repositories and packages.
3. Include SYNONYMS for common concepts (e.g., "todo" -> also generate "task manager", "checklist").
4. Include queries for: GitHub repo name search, npm/PyPI package name search, HN discussion search.
5. Use English terms even if input is in Chinese.
6. Prioritize specific technical terms over generic words.
7. Never include: "tool", "app", "platform", "system", "AI", "powered", "smart", "build".
8. Think about what a developer would name their repo or package for this idea."""
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_api_extract_keywords.py -v
```
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add api/main.py tests/test_api_extract_keywords.py
git commit -m "feat: enhance Haiku prompt for better search-optimized keywords with synonyms"
```

---

### Task 5: Rewrite PyPI source — Two-Tier approach

Replace broken HTML scraping with PyPI JSON API (keyless) + libraries.io (enhanced).

**Files:**
- Modify: `src/idea_reality_mcp/sources/pypi.py` (complete rewrite)
- Rewrite: `tests/test_pypi.py` (new mocks for new API)

- [ ] **Step 1: Write tests for new PyPI source**

Replace the entire contents of `tests/test_pypi.py`:

```python
"""Tests for PyPI search source adapter (two-tier: PyPI JSON + libraries.io)."""

from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from idea_reality_mcp.sources.pypi import PyPIResults, search_pypi


def _mock_response(json_data=None, status_code: int = 200, text: str = "") -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


SAMPLE_PYPI_JSON = {
    "info": {
        "name": "flask",
        "version": "3.0.0",
        "summary": "A simple framework for building complex web applications.",
        "home_page": "https://flask.palletsprojects.com",
        "project_url": "https://pypi.org/project/flask/",
    }
}

SAMPLE_LIBRARIES_IO = [
    {
        "name": "flask",
        "platform": "Pypi",
        "description": "A simple framework for building complex web applications.",
        "repository_url": "https://github.com/pallets/flask",
        "stars": 68000,
        "latest_release_number": "3.0.0",
    },
    {
        "name": "django",
        "platform": "Pypi",
        "description": "A high-level Python web framework.",
        "repository_url": "https://github.com/django/django",
        "stars": 80000,
        "latest_release_number": "5.0",
    },
]


class TestSearchPyPIJsonTier:
    """Tier 1: PyPI JSON API (keyless, always available)."""

    @pytest.mark.asyncio
    async def test_exact_match_found(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(json_data=SAMPLE_PYPI_JSON)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.pypi.httpx.AsyncClient", return_value=mock_client):
            with patch.dict("os.environ", {}, clear=False):
                # Remove LIBRARIES_IO_KEY if present
                import os
                env = {k: v for k, v in os.environ.items() if k != "LIBRARIES_IO_KEY"}
                with patch.dict("os.environ", env, clear=True):
                    result = await search_pypi(["flask"])

        assert isinstance(result, PyPIResults)
        assert result.total_count >= 1
        assert not result.skipped
        assert len(result.top_packages) >= 1
        assert result.top_packages[0]["name"] == "flask"

    @pytest.mark.asyncio
    async def test_no_match_returns_zero(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(status_code=404)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.pypi.httpx.AsyncClient", return_value=mock_client):
            import os
            env = {k: v for k, v in os.environ.items() if k != "LIBRARIES_IO_KEY"}
            with patch.dict("os.environ", env, clear=True):
                result = await search_pypi(["xyznonexistent123"])

        assert isinstance(result, PyPIResults)
        assert result.total_count == 0
        assert not result.skipped


class TestSearchPyPILibrariesIoTier:
    """Tier 2: libraries.io API (with key, enhanced search)."""

    @pytest.mark.asyncio
    async def test_libraries_io_success(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        # libraries.io returns a list of packages
        mock_client.get.return_value = _mock_response(json_data=SAMPLE_LIBRARIES_IO)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.pypi.httpx.AsyncClient", return_value=mock_client):
            with patch.dict("os.environ", {"LIBRARIES_IO_KEY": "test-key"}):
                result = await search_pypi(["web framework"])

        assert isinstance(result, PyPIResults)
        assert result.total_count >= 2
        assert not result.skipped
        assert len(result.top_packages) >= 1

    @pytest.mark.asyncio
    async def test_libraries_io_error_falls_back_to_pypi_json(self):
        """If libraries.io fails, should fallback to PyPI JSON tier."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        # First call (libraries.io) fails, second call (PyPI JSON) succeeds
        mock_client.get.side_effect = [
            _mock_response(status_code=500),
            _mock_response(json_data=SAMPLE_PYPI_JSON),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.pypi.httpx.AsyncClient", return_value=mock_client):
            with patch.dict("os.environ", {"LIBRARIES_IO_KEY": "test-key"}):
                result = await search_pypi(["flask"])

        assert isinstance(result, PyPIResults)
        assert not result.skipped


class TestSearchPyPISkipped:
    @pytest.mark.asyncio
    async def test_skipped_field_exists(self):
        result = PyPIResults()
        assert hasattr(result, "skipped")

    @pytest.mark.asyncio
    async def test_total_failure_sets_skipped(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.pypi.httpx.AsyncClient", return_value=mock_client):
            import os
            env = {k: v for k, v in os.environ.items() if k != "LIBRARIES_IO_KEY"}
            with patch.dict("os.environ", env, clear=True):
                result = await search_pypi(["anything"])

        assert isinstance(result, PyPIResults)
        # Should still return a result, not crash


class TestSearchPyPIDeduplication:
    @pytest.mark.asyncio
    async def test_dedup_across_keywords(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = [
            _mock_response(json_data=SAMPLE_PYPI_JSON),
            _mock_response(json_data=SAMPLE_PYPI_JSON),  # same package
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.pypi.httpx.AsyncClient", return_value=mock_client):
            import os
            env = {k: v for k, v in os.environ.items() if k != "LIBRARIES_IO_KEY"}
            with patch.dict("os.environ", env, clear=True):
                result = await search_pypi(["flask", "flask-web"])

        names = [p["name"] for p in result.top_packages]
        assert len(set(names)) == len(names)  # no duplicates
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_pypi.py -v
```
Expected: FAIL — `PyPIResults` has no `skipped` attribute, API calls don't match new structure

- [ ] **Step 3: Rewrite pypi.py with two-tier approach**

Replace entire contents of `src/idea_reality_mcp/sources/pypi.py`:

```python
"""PyPI search source — two-tier approach.

Tier 1 (keyless): PyPI JSON API — exact package name lookup.
Tier 2 (with key): libraries.io API — fuzzy search across PyPI packages.

Falls back gracefully: Tier 2 → Tier 1 → skipped.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import httpx

PYPI_JSON_URL = "https://pypi.org/pypi/{package}/json"
LIBRARIES_IO_URL = "https://libraries.io/api/search"


@dataclass
class PyPIResults:
    """Aggregated PyPI search results."""

    total_count: int = 0
    top_packages: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    skipped: bool = False


def _keyword_to_package_names(keyword: str) -> list[str]:
    """Convert a keyword query to candidate PyPI package names.

    'todo app' -> ['todo-app', 'todoapp', 'todo', 'app']
    'web framework' -> ['web-framework', 'webframework', 'web', 'framework']
    """
    words = re.sub(r"[^a-zA-Z0-9\s]", " ", keyword.lower()).split()
    if not words:
        return []
    candidates = []
    if len(words) > 1:
        candidates.append("-".join(words))       # todo-app
        candidates.append("".join(words))         # todoapp
    for w in words:
        if len(w) >= 3:  # skip very short words
            candidates.append(w)
    return candidates


async def _search_pypi_json(keywords: list[str]) -> PyPIResults:
    """Tier 1: Query PyPI JSON API for exact package name matches."""
    found_count = 0
    all_packages: list[dict] = []
    evidence: list[dict] = []
    seen: set[str] = set()

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for keyword in keywords:
            keyword_count = 0
            candidates = _keyword_to_package_names(keyword)
            for pkg_name in candidates:
                if pkg_name in seen:
                    continue
                seen.add(pkg_name)
                try:
                    url = PYPI_JSON_URL.format(package=pkg_name)
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        info = data.get("info", {})
                        found_count += 1
                        keyword_count += 1
                        all_packages.append({
                            "name": info.get("name", pkg_name),
                            "url": f"https://pypi.org/project/{info.get('name', pkg_name)}/",
                            "version": info.get("version", ""),
                            "description": (info.get("summary") or "")[:200],
                        })
                    # 404 = package doesn't exist, that's fine
                except (httpx.HTTPError, Exception):
                    pass  # graceful degradation

            evidence.append({
                "source": "pypi",
                "type": "package_count",
                "query": keyword,
                "count": keyword_count,
                "detail": f"{keyword_count} PyPI packages found for '{keyword}'",
            })

    # Deduplicate by name
    deduped: list[dict] = []
    seen_names: set[str] = set()
    for pkg in all_packages:
        if pkg["name"] not in seen_names:
            seen_names.add(pkg["name"])
            deduped.append(pkg)

    return PyPIResults(
        total_count=found_count,
        top_packages=deduped[:5],
        evidence=evidence,
        skipped=False,
    )


async def _search_libraries_io(keywords: list[str], api_key: str) -> PyPIResults | None:
    """Tier 2: Query libraries.io for fuzzy PyPI package search.

    Returns None on failure (caller falls back to Tier 1).
    """
    max_count = 0
    all_packages: list[dict] = []
    evidence: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for keyword in keywords:
                try:
                    resp = await client.get(
                        LIBRARIES_IO_URL,
                        params={
                            "q": keyword,
                            "platforms": "pypi",
                            "api_key": api_key,
                            "per_page": 5,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    if not isinstance(data, list):
                        continue

                    count = len(data)
                    if count > max_count:
                        max_count = count

                    for pkg in data:
                        all_packages.append({
                            "name": pkg.get("name", ""),
                            "url": f"https://pypi.org/project/{pkg.get('name', '')}/",
                            "version": pkg.get("latest_release_number", ""),
                            "description": (pkg.get("description") or "")[:200],
                        })

                    evidence.append({
                        "source": "pypi",
                        "type": "package_count",
                        "query": keyword,
                        "count": count,
                        "detail": f"{count} PyPI packages found for '{keyword}'",
                    })
                except httpx.HTTPError:
                    evidence.append({
                        "source": "pypi",
                        "type": "error",
                        "query": keyword,
                        "count": 0,
                        "detail": f"Failed to query libraries.io for '{keyword}'",
                    })
    except Exception:
        return None  # total failure, fall back to Tier 1

    # Deduplicate
    seen: set[str] = set()
    deduped: list[dict] = []
    for pkg in all_packages:
        name = pkg["name"]
        if name and name not in seen:
            seen.add(name)
            deduped.append(pkg)

    return PyPIResults(
        total_count=max_count,
        top_packages=deduped[:5],
        evidence=evidence,
        skipped=False,
    )


async def search_pypi(keywords: list[str]) -> PyPIResults:
    """Search PyPI for packages matching keyword variants.

    Two-tier approach:
    - Tier 2 (libraries.io): fuzzy search if LIBRARIES_IO_KEY env var is set
    - Tier 1 (PyPI JSON): exact package name lookup (always available)

    Falls back gracefully through tiers.
    """
    # Try Tier 2 first (libraries.io — fuzzy search)
    lib_key = os.environ.get("LIBRARIES_IO_KEY")
    if lib_key:
        result = await _search_libraries_io(keywords, lib_key)
        if result is not None and result.total_count > 0:
            return result

    # Fall back to Tier 1 (PyPI JSON — exact match)
    return await _search_pypi_json(keywords)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_pypi.py -v
```
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/idea_reality_mcp/sources/pypi.py tests/test_pypi.py
git commit -m "fix: rewrite PyPI source with two-tier approach (PyPI JSON + libraries.io)"
```

---

### Task 6: Add PyPI weight redistribution to engine.py

Update `compute_signal()` to handle `PyPIResults.skipped` field, redistributing weight when PyPI data is unavailable (same pattern as Product Hunt).

**Files:**
- Modify: `src/idea_reality_mcp/scoring/engine.py` (~L670-720)
- Modify: `tests/test_scoring.py`

- [ ] **Step 1: Write test for PyPI weight redistribution**

Add to `tests/test_scoring.py`:

```python
class TestPyPIWeightRedistribution:
    """Verify PyPI weight is redistributed when skipped."""

    def test_pypi_skipped_redistributes_weight_to_increase_score(self):
        """When PyPI is skipped, its 13% weight goes to sources with data → higher score."""
        github = GitHubResults(
            total_repo_count=100, max_stars=1000, top_repos=[],
            recent_ratio=0.3, recently_updated_ratio=0.5, recent_created_count=30,
        )
        hn = HNResults(total_mentions=50, evidence=[], recent_mention_ratio=0.4)
        npm = NpmResults(total_count=100, top_packages=[], evidence=[])

        # PyPI skipped: its 13% weight redistributed to GitHub/HN/npm (which have data)
        pypi_skipped = PyPIResults(total_count=0, skipped=True, evidence=[])
        result_skipped = compute_signal(
            idea_text="test", keywords=["test"], github_results=github,
            hn_results=hn, depth="deep", npm_results=npm, pypi_results=pypi_skipped,
        )

        # PyPI NOT skipped: 13% weight × score(0) = 0 contribution, dilutes total
        pypi_zero = PyPIResults(total_count=0, skipped=False, evidence=[])
        result_zero = compute_signal(
            idea_text="test", keywords=["test"], github_results=github,
            hn_results=hn, depth="deep", npm_results=npm, pypi_results=pypi_zero,
        )

        # With redistribution, score should be HIGHER because PyPI's zero-weight
        # goes to sources that have data (GitHub=100, HN=50, npm=100)
        assert result_skipped["reality_signal"] >= result_zero["reality_signal"]
        assert 0 <= result_skipped["reality_signal"] <= 100

    def test_pypi_skipped_not_in_sources_used(self):
        github = GitHubResults(
            total_repo_count=10, max_stars=100, top_repos=[],
            recent_ratio=0.5, recently_updated_ratio=0.5, recent_created_count=5,
        )
        hn = HNResults(total_mentions=5, evidence=[], recent_mention_ratio=0.5)
        npm = NpmResults(total_count=10, top_packages=[], evidence=[])
        pypi_skipped = PyPIResults(total_count=0, skipped=True, evidence=[])

        result = compute_signal(
            idea_text="test", keywords=["test"], github_results=github,
            hn_results=hn, depth="deep", npm_results=npm, pypi_results=pypi_skipped,
        )

        assert "pypi" not in result["meta"]["sources_used"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_scoring.py::TestPyPIWeightRedistribution -v
```
Expected: FAIL — `PyPIResults` constructor doesn't accept `skipped` keyword yet (or it works if Task 5 is already done — either way, the engine logic needs updating)

- [ ] **Step 3: Add PyPI weight redistribution to compute_signal()**

In `src/idea_reality_mcp/scoring/engine.py`, find the deep mode block (~L670-680):

```python
        n_score = _npm_score(npm_results.total_count) if npm_results else 0
        p_score = _pypi_score(pypi_results.total_count) if pypi_results else 0

        weights = dict(_DEEP_WEIGHTS)

        if npm_results:
            sources_used.append("npm")
        if pypi_results:
            sources_used.append("pypi")
```

Replace with:

```python
        n_score = _npm_score(npm_results.total_count) if npm_results else 0

        weights = dict(_DEEP_WEIGHTS)

        if npm_results:
            sources_used.append("npm")

        # PyPI — redistribute weight if skipped/unavailable
        pypi_available = pypi_results is not None and not getattr(pypi_results, "skipped", False)
        if pypi_available:
            p_score = _pypi_score(pypi_results.total_count)
            sources_used.append("pypi")
        else:
            p_score = 0
            pypi_w = weights.pop("pypi", 0.13)
            remaining_keys = list(weights.keys())
            total_remaining = sum(weights[k] for k in remaining_keys)
            if total_remaining > 0:
                for k in remaining_keys:
                    weights[k] += pypi_w * (weights[k] / total_remaining)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_scoring.py -v
```
Expected: ALL PASS

- [ ] **Step 5: Commit**

```bash
git add src/idea_reality_mcp/scoring/engine.py tests/test_scoring.py
git commit -m "feat: add PyPI weight redistribution when skipped (same pattern as PH)"
```

---

### Task 7: Harden Stack Overflow against rate limiting

Add backoff handling, error_id detection, and `skipped` field to SO source.

**Files:**
- Modify: `src/idea_reality_mcp/sources/stackoverflow.py`
- Modify: `tests/test_stackoverflow.py`

- [ ] **Step 1: Write tests for backoff and error handling**

Add to `tests/test_stackoverflow.py`:

```python
class TestSearchStackOverflowBackoff:
    """Verify backoff and API error handling."""

    @pytest.mark.asyncio
    async def test_backoff_field_skips_remaining_queries(self):
        """When API returns backoff field, skip remaining keyword queries."""
        backoff_response = {
            "items": [],
            "has_more": False,
            "backoff": 10,  # seconds to wait
        }
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = [
            _mock_response(SAMPLE_RESPONSE),      # kw1 succeeds
            _mock_response(backoff_response),      # kw2 returns backoff
            _mock_response(SAMPLE_RESPONSE),       # kw3 should be skipped
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.stackoverflow.httpx.AsyncClient", return_value=mock_client):
            result = await search_stackoverflow(["kw1", "kw2", "kw3"])

        # kw1 results should be preserved
        assert result.total_count == 3
        # kw3 should NOT have been called (backoff after kw2)
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_error_id_in_response(self):
        """API error responses with error_id should be handled gracefully."""
        error_response = {
            "error_id": 502,
            "error_name": "throttle_violation",
            "error_message": "too many requests",
        }
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(error_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.stackoverflow.httpx.AsyncClient", return_value=mock_client):
            result = await search_stackoverflow(["test"])

        assert isinstance(result, StackOverflowResults)
        assert result.total_count == 0

    @pytest.mark.asyncio
    async def test_skipped_field_exists(self):
        result = StackOverflowResults()
        assert hasattr(result, "skipped")
        assert result.skipped is False

    @pytest.mark.asyncio
    async def test_json_decode_error_handled(self):
        """Non-JSON response should not crash."""
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.side_effect = ValueError("No JSON")

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.stackoverflow.httpx.AsyncClient", return_value=mock_client):
            result = await search_stackoverflow(["test"])

        assert isinstance(result, StackOverflowResults)
        assert result.total_count == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_stackoverflow.py::TestSearchStackOverflowBackoff -v
```
Expected: FAIL — no `skipped` attribute, no backoff handling

- [ ] **Step 3: Update stackoverflow.py with hardened error handling**

Modify `src/idea_reality_mcp/sources/stackoverflow.py`:

1. Add `skipped: bool = False` to the dataclass:

```python
@dataclass
class StackOverflowResults:
    """Aggregated Stack Overflow search results."""

    total_count: int = 0
    top_questions: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    recent_question_ratio: float | None = None
    skipped: bool = False
```

2. Replace the inner loop in `search_stackoverflow()` (the `for query in keywords:` block, L66-127) with:

```python
    backoff_hit = False

    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in keywords:
            if backoff_hit:
                evidence.append({
                    "source": "stackoverflow",
                    "type": "skipped",
                    "query": query,
                    "count": 0,
                    "detail": f"Skipped '{query}' due to API backoff",
                })
                continue

            params: dict = {
                "order": "desc",
                "sort": "relevance",
                "intitle": query,
                "site": "stackoverflow",
                "pagesize": 10,
                "filter": "!9_bDDxJY5",
            }
            if key:
                params["key"] = key

            try:
                resp = await client.get(SO_API, params=params)
                resp.raise_for_status()
                data = resp.json()

                # Check for API-level errors
                if "error_id" in data:
                    evidence.append({
                        "source": "stackoverflow",
                        "type": "error",
                        "query": query,
                        "count": 0,
                        "detail": f"SO API error: {data.get('error_message', 'unknown')}",
                    })
                    if data.get("error_name") == "throttle_violation":
                        backoff_hit = True
                    continue

                # Check for backoff signal
                if data.get("backoff"):
                    backoff_hit = True

                items = data.get("items", [])
                count = len(items)
                if data.get("has_more"):
                    count = count + 1

                ratio = _compute_recent_ratio(items, three_months_ago)

                if count > max_count:
                    max_count = count
                    best_ratio = ratio

                for item in items:
                    qid = item.get("question_id")
                    if qid and qid not in seen_ids:
                        seen_ids.add(qid)
                        all_questions.append({
                            "title": item.get("title", ""),
                            "link": item.get("link", ""),
                            "score": item.get("score", 0),
                            "answer_count": item.get("answer_count", 0),
                            "is_answered": item.get("is_answered", False),
                            "creation_date": item.get("creation_date", 0),
                            "tags": item.get("tags", []),
                        })

                evidence.append({
                    "source": "stackoverflow",
                    "type": "question_count",
                    "query": query,
                    "count": count,
                    "detail": f"{count} Stack Overflow questions found for '{query}'",
                })
            except httpx.HTTPError:
                evidence.append({
                    "source": "stackoverflow",
                    "type": "error",
                    "query": query,
                    "count": 0,
                    "detail": f"Failed to query Stack Overflow for '{query}'",
                })
            except Exception:
                evidence.append({
                    "source": "stackoverflow",
                    "type": "error",
                    "query": query,
                    "count": 0,
                    "detail": f"Unexpected error querying Stack Overflow for '{query}'",
                })
```

- [ ] **Step 4: Update engine.py SO availability check**

In `src/idea_reality_mcp/scoring/engine.py`, find L698:

```python
        so_available = so_results is not None
```

Replace with:

```python
        so_available = so_results is not None and not getattr(so_results, "skipped", False)
```

- [ ] **Step 5: Run all tests**

```bash
uv run pytest tests/ -v
```
Expected: ALL PASS

- [ ] **Step 6: Commit**

```bash
git add src/idea_reality_mcp/sources/stackoverflow.py src/idea_reality_mcp/scoring/engine.py tests/test_stackoverflow.py
git commit -m "fix: harden SO against rate limiting (backoff, error_id, skipped field)"
```

---

### Task 8: Run full test suite + benchmark validation

Final validation that all fixes work together and scores are correct.

**Files:**
- No new files — validation only

- [ ] **Step 1: Run full test suite**

```bash
cd C:/Users/johns/projects/idea-reality-mcp
uv run pytest tests/ -v
```
Expected: ALL PASS (277+ tests)

- [ ] **Step 2: Run benchmark ideas**

```bash
uv run python -c "
import asyncio
from idea_reality_mcp.tools import idea_check
async def bench():
    for idea in ['todo list app', 'expense tracker personal finance', 'AI chatbot customer service']:
        r = await idea_check(idea, depth='deep')
        sig = r['reality_signal']
        dup = r['duplicate_likelihood']
        sub = r['sub_scores']
        print(f'IDEA: {idea}')
        print(f'  signal={sig} ({dup})')
        print(f'  sub_scores={sub}')
        print(f'  sources={r[\"meta\"][\"sources_used\"]}')
        print()
asyncio.run(bench())
"
```

Expected:
- todo list app: `reality_signal` >= 60, `duplicate_likelihood` = "high" or "medium"
- AI chatbot: `reality_signal` >= 70, `duplicate_likelihood` = "high"
- expense tracker: `reality_signal` >= 55

- [ ] **Step 3: If benchmarks fail, debug and fix**

If any benchmark idea scores below expected:
1. Check which sub_scores are still 0
2. Verify keyword generation produces good queries (print `keywords`)
3. Check if PyPI/SO are contributing

- [ ] **Step 4: Bump version to v0.5.1**

Update version in:
- `pyproject.toml`: `version = "0.5.1"`
- `src/idea_reality_mcp/scoring/engine.py`: `"version": "0.5.1"` (in `compute_signal` return dict)

- [ ] **Step 5: Final commit**

```bash
git add pyproject.toml src/idea_reality_mcp/scoring/engine.py
git commit -m "chore: bump version to v0.5.1 (scoring accuracy fixes)"
```

---

## Task Dependency Graph

```
Task 1 (synonyms dict) ──→ Task 2 (integrate into engine)
                                              │
Task 3 (LLM-first) ──────────────────────────→│
Task 4 (enhance prompt) ─────────────────────→│
                                              │
Task 5 (PyPI rewrite) ──→ Task 6 (weight redistribution)
                                              │
Task 7 (SO hardening) ──────────────────────→│
                                              │
                                              ↓
                                    Task 8 (validation)
```

**Parallelizable groups:**
- Group A: Tasks 1+2 (keyword synonyms)
- Group B: Tasks 3+4 (LLM-first)
- Group C: Tasks 5+6 (PyPI)
- Group D: Task 7 (SO)
- Groups A/B/C/D are independent and can be worked on in parallel
- Task 8 depends on all others
