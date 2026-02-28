# IDEA-REALITY-MCP — Project Context

## What This Is
Mnemox Idea Reality MCP Server v0.3.4 — a workflow-native pre-build reality check for AI coding agents.
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
- Tests: `uv run pytest tests/ -v` (120 tests)

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

## Current Status (v0.3.4)
- ✅ Core MCP server working (stdio + Streamable HTTP transport)
- ✅ 5 sources: GitHub, HN, npm, PyPI, Product Hunt
- ✅ depth="deep" parallel mode
- ✅ 3-stage keyword extraction pipeline (Stage A/B/C)
- ✅ 150+ Chinese term mappings (CHINESE_TECH_MAP), 15+ domains
- ✅ 90+ intent anchors, 80+ synonym expansions
- ✅ LLM keyword extraction (Haiku 4.5) on Render API, dictionary-only on MCP stdio
- ✅ 120/120 tests passing, 54/54 golden eval (100% dictionary anchor hit)
- ✅ Published to PyPI (v0.3.4) + GitHub Release
- ✅ CI/CD: GitHub Actions (tests + PyPI trusted publisher)
- ✅ README rewritten: "We search. They guess." positioning
- ✅ Full bilingual docs (EN + zh-TW)
- ✅ Live demo: mnemox.ai/check (Render API backend)
- ✅ MCP Streamable HTTP at /mcp endpoint
- ✅ smithery.yaml + published to Smithery marketplace
- ✅ Listed on 9+ directories
- ✅ MCP Registry metadata (server.json) prepared

## Roadmap (v0.4+)
- [ ] Trend detection and timing analysis
- [ ] Idea Memory Dataset (opt-in anonymous logging of checks)

## Key Design Decisions
- Protocol, not SaaS — no dashboard, no website UI (except /check demo)
- Zero storage by default — doesn't store any user input
- GITHUB_TOKEN optional — works without but rate-limited (10 req/min)
- PRODUCTHUNT_TOKEN optional — skipped gracefully if not set
- Scoring is intentionally simple and explainable, not ML
- Graceful degradation — partial results if any source fails
- Chinese support via dictionary (150+ terms) for MCP stdio; LLM (Haiku 4.5) for Render API

## Planning Rules

1. **Every new feature field must have an "implementation cost" estimate.**
   - Don't propose a JSON schema field unless you can name the exact API endpoint or data source.
   - If it requires a new API, LLM call, or custom calculation, say so explicitly with time estimate.

2. **No architecture design for features beyond the next 2 versions.**
   - v0.4 and v0.5: full implementation detail allowed.
   - v1.0+: one-line description only. No code snippets, no JSON schemas, no architecture diagrams.
   - Reason: designs for v2.0 will be obsolete by the time we get there.

3. **"Cool but not now" filter.**
   - Before proposing any feature, ask: "Does Sean have enough users/data to benefit from this today?"
   - If the answer is no, move it to a "Future Ideas" section and stop elaborating.
   - Examples of "not now": privacy/Tor/decoy queries, local LLM, differential privacy, decoy queries.

4. **Data claims need math.**
   - Don't say "100 data points is enough to start modeling" without specifying the statistical method.
   - Don't propose "backfill historical data" without confirming the API supports it.

5. **One solo developer = max 2 priorities at a time.**
   - Never propose 3+ parallel workstreams. Sean is one person + AI agents.
   - Every plan must have a strict sequential order, not a parallel one.

## Priorities

### Priority 1: v0.4 (plan approved, coding starts 3/3)
- **Feature A — Temporal Signals**: dual-dimension (recent_created_ratio + recently_active_ratio), top 3 competitor activity
- **Feature B — Email Collection + Decision Tracking**: Supabase, decision buttons (5s delay), email subscribe w/ rate limit
- **Timeline**: v0.3.4 stays live until 3/14+. No version bump until both features ready + content push planned.
- **Full plan**: `.claude/plans/dazzling-toasting-umbrella.md`

### Priority 2: Distribution (2/27 – 3/2, no code)
- Monitor Show HN + Dev.to comments, reply immediately
- Self-comment on own Dev.to article (first comment)
- Engage in related article comments
- Follow up: Glama, PR #2346, ClaudeMCP #45, mcp-get #176, Fleur #37

### Future Ideas (do NOT elaborate)
- Privacy mode / local LLM / Tor / decoy queries → v2.0+
- Decision Framework full version → after ground truth data exists
- Agent session memory / follow-up → v1.0+
- competitor_health detailed (bus_factor, PR frequency) → v0.5

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
