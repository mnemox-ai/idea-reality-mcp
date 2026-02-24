# IDEA-REALITY-MCP — Project Context

## What This Is
Mnemox Idea Reality MCP Server v0.1.0 — a workflow-native pre-build reality check for AI coding agents.
MCP tool `idea_check` scans GitHub + HN before you build, returns reality_signal (0-100).

## Org
- GitHub: mnemox-ai/idea-reality-mcp
- Parent brand: Mnemox (mnemox.ai)
- Sister project: tradememory-protocol (AI trading memory layer)
- Lead: Sean (sean.sys) — directs AI agents to build systems

## Tech Stack
- Python 3.11+, FastMCP 3.x, httpx (async), uv
- Sources: GitHub Search API + HN Algolia API
- Entry: `python -m idea_reality_mcp` or `uv run python -m idea_reality_mcp`
- Tests: `uv run pytest tests/ -v` (31 tests)

## Architecture
```
src/idea_reality_mcp/
├── server.py          # FastMCP server
├── tools.py           # idea_check tool definition
├── scoring/engine.py  # reality_signal weighted formula (0.6 github + 0.2 stars + 0.2 hn)
└── sources/
    ├── github.py      # GitHub Search API adapter
    └── hn.py          # HN Algolia API adapter
```

## Current Status (v0.1.0)
- ✅ Core MCP server working (stdio transport)
- ✅ GitHub + HN sources live
- ✅ 31/31 tests passing
- ✅ README, LICENSE (MIT), SECURITY.md, CONTRIBUTING.md
- ✅ Published to GitHub, tagged v0.1.0

## Roadmap (v0.2+)
- [ ] ProductHunt source (sources/ph.py)
- [ ] "deep" mode (parallel all sources)
- [ ] Idea Memory Dataset (opt-in anonymous logging of checks)
- [ ] PyPI publish
- [ ] awesome-mcp-servers PR
- [ ] GitHub Release with demo outputs

## Key Design Decisions
- Protocol, not SaaS — no dashboard, no website UI
- Zero storage by default — v0 doesn't store any user input
- GITHUB_TOKEN optional — works without but rate-limited (10 req/min)
- Scoring is intentionally simple and explainable, not ML

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
