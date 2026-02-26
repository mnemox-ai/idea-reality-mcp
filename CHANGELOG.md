English | [繁體中文](CHANGELOG.zh-TW.md)

# Changelog

All notable changes to this project will be documented in this file.

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
