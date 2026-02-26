# IDEA-REALITY-MCP — Project Context

## What This Is
Mnemox Idea Reality MCP Server v0.3.0 — a workflow-native pre-build reality check for AI coding agents.
MCP tool `idea_check` scans GitHub, HN, npm, PyPI, and Product Hunt before you build, returns reality_signal (0-100).

## Org
- GitHub: mnemox-ai/idea-reality-mcp
- Parent brand: Mnemox (mnemox.ai)
- Sister project: tradememory-protocol (AI trading memory layer)
- Lead: Sean (sean.sys) — directs AI agents to build systems

## Tech Stack
- Python 3.11+, FastMCP 3.x, httpx (async), uv
- Sources: GitHub Search API, HN Algolia API, npm Registry, PyPI (HTML scraping), Product Hunt GraphQL (optional)
- Entry: `python -m idea_reality_mcp` or `uv run python -m idea_reality_mcp`
- Tests: `uv run pytest tests/ -v` (93 tests)

## Architecture
```
src/idea_reality_mcp/
├── server.py          # FastMCP server
├── tools.py           # idea_check tool (quick + deep mode, asyncio.gather)
├── scoring/
│   ├── engine.py      # reality_signal weighted formula + 3-stage keyword extraction
│   └── synonyms.py    # INTENT_ANCHORS (90+) + SYNONYMS dict (80+ keys)
└── sources/
    ├── __init__.py    # exports all sources
    ├── github.py      # GitHub Search API adapter
    ├── hn.py          # HN Algolia API adapter
    ├── npm.py         # npm Registry JSON API adapter
    ├── pypi.py        # PyPI HTML scraping adapter
    └── producthunt.py # Product Hunt GraphQL adapter (optional, needs token)
```

## Modes
- **quick** (default): GitHub + HN — weights: repos 60% + stars 20% + HN 20%
- **deep**: all 5 sources in parallel — weights: repos 25% + stars 10% + HN 15% + npm 20% + PyPI 15% + PH 15%
- PH weight auto-redistributed when PRODUCTHUNT_TOKEN not set

## Current Status (v0.3.0)
- ✅ Core MCP server working (stdio transport)
- ✅ 5 sources: GitHub, HN, npm, PyPI, Product Hunt
- ✅ depth="deep" parallel mode
- ✅ 3-stage keyword extraction pipeline (Stage A/B/C)
- ✅ 150+ Chinese term mappings (CHINESE_TECH_MAP), 15+ domains
- ✅ 90+ intent anchors, 80+ synonym expansions
- ✅ 93/93 tests passing, 54/54 golden eval (100% anchor hit)
- ✅ Published to PyPI (v0.3.0) + GitHub Release
- ✅ CI/CD: GitHub Actions (tests + PyPI trusted publisher)
- ✅ README, LICENSE (MIT), SECURITY.md, CONTRIBUTING.md, CHANGELOG.md
- ✅ Full bilingual docs (EN + zh-TW)
- ✅ awesome-mcp-servers PR #2346 submitted
- ✅ Live demo: mnemox.ai/check (Render API backend)

## Roadmap (v0.4+)
- [ ] LLM-powered keyword extraction and semantic similarity
- [ ] Idea Memory Dataset (opt-in anonymous logging of checks)
- [ ] Trend detection and timing analysis

## Key Design Decisions
- Protocol, not SaaS — no dashboard, no website UI (except /check demo)
- Zero storage by default — doesn't store any user input
- GITHUB_TOKEN optional — works without but rate-limited (10 req/min)
- PRODUCTHUNT_TOKEN optional — skipped gracefully if not set
- Scoring is intentionally simple and explainable, not ML
- Graceful degradation — partial results if any source fails
- Chinese support via dictionary (150+ terms), not LLM translation

## Communication Style
- Sean prefers 繁體中文 for discussion, English for code/docs
- Direct, no-BS, honest feedback over optimistic reassurance
- "先可用再變強" — ship first, optimize later

## When Working On This Project
1. Always run tests after changes: `uv run pytest tests/ -v`
2. Keep scoring formula explainable
3. Don't add SaaS features (no auth, no dashboard, no user accounts)
4. README is marketing — keep it sharp and technical
5. Every new source goes in sources/ as its own adapter file
6. Follow existing patterns: dataclass for results, async with httpx, evidence list
