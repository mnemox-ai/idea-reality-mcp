English | [繁體中文](CHANGELOG.zh-TW.md)

# Changelog

All notable changes to this project will be documented in this file.

## [0.3.3] - 2026-02-27

### Added
- Published to MCP Registry (`io.github.mnemox-ai/idea-reality-mcp`)
- `server.json` updated to official MCP Registry schema

## [0.3.2] - 2026-02-27

### Added
- **LLM-powered keyword extraction (Render API)** — Claude Haiku 4.5 generates optimal search queries from idea descriptions in any language, with automatic fallback to the dictionary pipeline
- `POST /api/extract-keywords` public endpoint (rate-limited: 50/IP/day) for standalone keyword extraction
- `keyword_source` field in response `meta` — indicates whether keywords came from `"llm"` or `"dictionary"`
- In-memory rate limiter for LLM endpoint (daily reset per IP)
- `scoring/llm.py` — MCP client-side caller for Render API with 8s timeout and graceful fallback
- `tests/test_llm.py` — 10 tests for LLM client module
- `tests/test_api_extract_keywords.py` — 8 tests for API endpoint
- `tests/eval_llm_vs_dict.py` — evaluation script comparing LLM vs dictionary on 54 golden ideas
- `docs/v0.4-comparison.md` — LLM vs dictionary comparison report
- `anthropic>=0.40.0` dependency for API server (`api/requirements.txt`)
- `ANTHROPIC_API_KEY` env var support in `render.yaml`

### Changed
- **README completely rewritten** — aggressive positioning ("We search. They guess."), competitor comparison table, "Why not just ask ChatGPT?" section
- `api/main.py` now calls Haiku for keyword extraction in `/api/check`, falling back to dictionary on any failure
- Markdown code fence stripping for Haiku responses (model wraps JSON in ``` fences)
- MCP stdio (`tools.py`) uses dictionary-only pipeline (100% anchor hit, no external dependency)
- Version bumped to `0.3.2`

### Infrastructure
- **MCP Streamable HTTP transport** at `/mcp` endpoint — enables Smithery and MCP HTTP clients
- `smithery.yaml` configuration for Smithery marketplace
- Published to Smithery + submitted to 9+ MCP directories

### Stats
- 120 tests passing (102 original + 18 new)
- LLM eval: 54/54 ideas processed, 50/54 anchor hit (93%), 0 failures
- Dictionary eval: 54/54 anchor hit (100%)
- Chinese idea quality: LLM better in 3/10, tie in 6/10, dictionary better in 1/10

## [0.3.1] - 2026-02-27

### Fixed
- **Search precision for non-tech domains** — improved keyword extraction and result ranking for domains like legal, medical (TCM), agriculture, religion, etc.
  - Added missing Chinese mappings: `文件` (document), `文檔` (document), `智慧` (smart), `問診` (consultation)
  - Changed `分析` mapping from `analytics` (BI-specific) to `analysis` (general)
  - Added compound `數據分析` → `data analytics` to preserve BI context
  - Added `analysis` to INTENT_ANCHORS with synonym expansion
  - New "domain-first" query template: puts domain nouns before action verbs for better non-tech results
  - Fixed "anchor + anchor" template to include domain context (prevents overly broad queries)
- **GitHub result relevance ranking** — repos now sorted by query-match frequency first, then by stars. Repos matching multiple query variants rank higher than popular but irrelevant repos.

### Added
- 9 new non-tech domain tests (102 total, up from 93): TCM, legal, agriculture, buddhism, pet health, consultation
- `meta.version` updated to `"0.3.1"`

## [0.3.0] - 2026-02-27

### Changed
- **Keyword extraction overhaul** — three-stage pipeline (Stage A/B/C)
  - Stage A: Hard-filter boilerplate words (`ai`, `tool`, `platform`, `system`, `framework`, `engine`, etc.) + expanded stop word coverage
  - Stage B: Intent anchor detection — identifies 1–2 key intent signals (`monitoring`, `agent`, `rag`, `mcp`, `evaluation`, `cli`, `scraping`, `embedding`, `tracing`, `chatbot`…)
  - Stage C: Synonym expansion with curated 100+ term dictionary, generates 3–8 anchored queries (`monitoring` → `observability / tracing / telemetry`; `evaluation` → `evals / benchmark`; `agent` → `tool calling / orchestration`…)
- **Chinese/mixed-language support** — 150+ term `CHINESE_TECH_MAP` covering 15+ domains (tech, SaaS, medical, legal, education, manufacturing, agriculture, aerospace, religion, art, gaming, government…)
  - Sorted by key length (longest first) to prevent compound match collisions
  - Never returns raw Chinese text — fallback strips unmapped chars
- `extract_keywords()` now returns up to 8 variants (was 4), all anchored to detected intent

### Added
- `scoring/synonyms.py` — SYNONYMS dict (80+ keys) + INTENT_ANCHORS set (90+ entries)
- `tests/golden_ideas.json` — 54-idea golden evaluation set (EN + ZH)
- `tests/eval_keywords.py` — keyword quality evaluation script (run with `python tests/eval_keywords.py`)
- `tests/test_tw_chinese.py` — 46 Taiwanese Chinese input test cases
- `tests/test_tw_niche.py` — 53 niche domain Chinese input test cases (15 categories)
- 20 new keyword tests (93 total, up from 73)

### Fixed
- Synonym expansion duplicate word bug (`"redis redis"`, `"mcp server server"`)
- `追蹤` mapped to general `tracking` (was infra-specific `tracing`)

### Improved
- Anchor hit rate on golden set: 100% (54/54 ideas)
- Junk keyword ratio: 4% average across 54 test ideas
- TW Chinese input: 98%+ pass rate (99 test cases across general + niche domains)
- Zero Chinese character leakage in query output
- `meta.version` updated to `"0.3.0"`

## [0.2.0] - 2026-02-25

### Added
- **npm Registry source** (`sources/npm.py`) — search npm for similar packages (free, no auth required)
- **PyPI Registry source** (`sources/pypi.py`) — search PyPI for similar Python packages
- **Product Hunt source** (`sources/producthunt.py`) — search Product Hunt for similar products (optional, requires `PRODUCTHUNT_TOKEN`)
- **`depth: "deep"` mode** — queries all 5 sources in parallel using `asyncio.gather()`
- **Improved keyword extraction** — compound term detection (e.g. "machine learning"), technology keyword prioritisation, expanded stop word list, registry-optimised query variant
- New scoring functions: `_npm_score()`, `_pypi_score()`, `_ph_score()`
- Deep mode scoring weights: GitHub repos 25% + stars 10% + HN 15% + npm 20% + PyPI 15% + Product Hunt 15%
- Automatic weight redistribution when Product Hunt is unavailable
- `top_similars` now includes entries from npm, PyPI, and Product Hunt (prefixed with `npm:`, `pypi:`, `ph:`)
- `sources/__init__.py` now exports all source functions and dataclasses
- 42 new tests (73 total, up from 31)
- This CHANGELOG

### Changed
- `extract_keywords()` now returns up to 4 variants (was 3), including a registry-optimised query
- `compute_signal()` accepts optional `npm_results`, `pypi_results`, `ph_results` keyword arguments
- `meta.version` updated to `"0.2.0"`
- `meta.sources_used` now dynamically reflects which sources were actually queried
- README updated with deep mode documentation, scoring weights, and new environment variables

## [0.1.0] - 2026-02-25

### Added
- Initial release
- `idea_check` MCP tool with `idea_text` and `depth` parameters
- GitHub Search API source (`sources/github.py`)
- Hacker News Algolia API source (`sources/hn.py`)
- Scoring engine with weighted formula (GitHub 60% + stars 20% + HN 20%)
- Keyword extraction with stop word filtering
- Duplicate likelihood classification (low/medium/high)
- Pivot hints generation (3 actionable suggestions)
- 31 tests
- CI/CD with GitHub Actions
- Published to PyPI
