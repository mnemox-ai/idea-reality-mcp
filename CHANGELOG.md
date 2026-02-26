English | [繁體中文](CHANGELOG.zh-TW.md)

# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-02-27

### Changed
- **Keyword extraction overhaul** — three-stage pipeline (Stage A/B/C)
  - Stage A: Hard-filter boilerplate words (`ai`, `tool`, `platform`, `system`, `framework`, `engine`, etc.) + expanded stop word coverage
  - Stage B: Intent anchor detection — identifies 1–2 key intent signals (`monitoring`, `agent`, `rag`, `mcp`, `evaluation`, `cli`, `scraping`, `embedding`, `tracing`, `chatbot`…)
  - Stage C: Synonym expansion with curated 100+ term dictionary, generates 3–8 anchored queries (`monitoring` → `observability / tracing / telemetry`; `evaluation` → `evals / benchmark`; `agent` → `tool calling / orchestration`…)
- Chinese and mixed-language input now mapped to English equivalents before tokenisation (監控→monitoring, 評測→evaluation, 爬蟲→scraping, 自動化→automation…)
- `extract_keywords()` now returns up to 8 variants (was 4), all anchored to detected intent

### Added
- `scoring/synonyms.py` — SYNONYMS dict + INTENT_ANCHORS set (new module)
- `tests/golden_ideas.json` — 25-idea golden evaluation set
- `tests/eval_keywords.py` — keyword quality evaluation script (run with `python tests/eval_keywords.py`)
- 20 new keyword tests (93 total, up from 73)

### Improved
- Anchor hit rate on golden set: 100% (measured from baseline)
- Junk keyword ratio: 2% average across 25 test ideas
- Chinese/mixed input produces stable, intent-aligned query sets
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
