# IDEA-REALITY-MCP — Project Context

## What This Is
Mnemox Idea Reality MCP Server v0.3.4 — a workflow-native pre-build reality check for AI coding agents.
MCP tool `idea_check` scans GitHub, HN, npm, PyPI, and Product Hunt before you build, returns reality_signal (0-100).

## Org
- GitHub: mnemox-ai/idea-reality-mcp
- Parent brand: Mnemox (mnemox.ai)
- Sister projects: tradememory-protocol (AI trading memory layer), **idea-check-action** (GitHub Action wrapper)
- Lead: Sean (sean.sys) — directs AI agents to build systems

## Tech Stack
- Python 3.11+, FastMCP 3.x, httpx (async), uv
- Sources: GitHub Search API, HN Algolia API, npm Registry, PyPI (HTML scraping), Product Hunt GraphQL (optional)
- Entry: `python -m idea_reality_mcp` or `uv run python -m idea_reality_mcp`
- Tests: `uv run pytest tests/ -v` (127 tests)

---

## Architecture (穩定參考)

```
src/idea_reality_mcp/
├── server.py          # FastMCP server
├── tools.py           # idea_check tool (quick + deep mode, asyncio.gather)
├── scoring/
│   ├── engine.py      # reality_signal weighted formula + 3-stage keyword extraction
│   ├── synonyms.py    # INTENT_ANCHORS (90+) + SYNONYMS dict (80+ keys)
│   └── llm.py         # Claude Haiku integration (MCP client → Render API)
└── sources/
    ├── __init__.py    # exports all sources
    ├── github.py      # GitHub Search API adapter
    ├── hn.py          # HN Algolia API adapter
    ├── npm.py         # npm Registry JSON API adapter
    ├── pypi.py        # PyPI HTML scraping adapter
    └── producthunt.py # Product Hunt GraphQL adapter (optional, needs token)

api/
├── main.py            # FastAPI wrapper (REST + MCP Streamable HTTP)
├── db.py              # Score History — SQLite storage layer
└── requirements.txt

templates/             # Agent instruction templates (copy-paste snippets)
├── CLAUDE.md          # Claude Code
├── cursorrules.md     # Cursor
├── copilot-instructions.md  # GitHub Copilot
├── windsurf-rules.md  # Windsurf
└── README.md          # Usage guide

examples/
├── agent-instructions.md  # All platforms in one file (incl. Windsurf, Copilot)
├── sample_prompts.md / .zh-TW.md
├── claude_desktop_config.json
└── cursor_mcp_config.json

drafts/
├── devto-v034.md
└── devto-agent-instructions.md  # Agent auto-check article (938 words)
```

### API Endpoints (Render: https://idea-reality-mcp.onrender.com)
- `GET  /health` — liveness probe
- `POST /api/check` — body: `{idea_text, depth}` → full report + idea_hash + score saved to history
- `POST /api/extract-keywords` — LLM extraction (Haiku 4.5, rate-limited 50/IP/day)
- `GET  /api/history/{idea_hash}` — score history for an idea
- `POST /api/subscribe` — body: `{email, idea_hash}` → email collection (dual-write: SQLite + stdout)
- `GET  /api/subscribers/count` — subscriber metrics
- `ANY  /mcp` — MCP Streamable HTTP transport

### Score History (api/db.py)
- SQLite, `SCORE_DB_PATH` env var or `./score_history.db`
- **Known limitation**: Render free tier wipes filesystem on deploy. Data lost on restart.
- Future: migrate to Turso (SQLite cloud) or Render PostgreSQL
- Schema: idea_hash (SHA256), idea_text, score, breakdown (JSON), keywords (JSON), depth, lang, keyword_source, created_at

## Modes
- **quick** (default): GitHub + HN — weights: repos 60% + stars 20% + HN 20%
- **deep**: all 5 sources in parallel — weights: repos 25% + stars 10% + HN 15% + npm 20% + PyPI 15% + PH 15%
- PH weight auto-redistributed when PRODUCTHUNT_TOKEN not set

## Key Design Decisions (穩定參考)
- Protocol, not SaaS — no dashboard, no website UI (except /check demo)
- Zero storage by default — MCP stdio stores nothing; Render API stores score history
- GITHUB_TOKEN optional — works without but rate-limited (10 req/min)
- PRODUCTHUNT_TOKEN optional — skipped gracefully if not set
- Scoring is intentionally simple and explainable, not ML
- Graceful degradation — partial results if any source fails
- Chinese support via dictionary (150+ terms) for MCP stdio; LLM (Haiku 4.5) for Render API

---

## Current Status (會變動)

### v0.4.0 (current, stable)
- ✅ Core MCP server (stdio + Streamable HTTP)
- ✅ 5 sources: GitHub, HN, npm, PyPI, Product Hunt
- ✅ 3-stage keyword extraction + LLM extraction (Render)
- ✅ 138/138 tests passing
- ✅ Score History (SQLite, /api/history endpoint)
- ✅ Email gate + subscribe endpoint (POST /api/subscribe, GET /api/subscribers/count)
- ✅ Agent templates — simplified to one-line hints (community feedback)
- ✅ idea-check-action GitHub Action (mnemox-ai/idea-check-action)
- ✅ Published: PyPI + GitHub Release + MCP Registry + Smithery + 10+ directories
- ✅ Live demo: mnemox.ai/check (with email gate)
- ✅ Full bilingual docs (EN + zh-TW)
- ✅ DEV.to article drafts (v0.3.4 + agent instructions)

### idea-check-action (v1)
- GitHub: mnemox-ai/idea-check-action (public)
- Composite action: `pip install idea-reality-mcp` → `entrypoint.py`
- Inputs: idea, depth, github-token, threshold
- Outputs: score, report (JSON), top-competitor
- Graceful failure: never breaks CI (::warning:: on error)
- Self-test workflow (.github/workflows/test.yml)

---

## Planning Rules (穩定參考)

1. **Every new feature field must have an "implementation cost" estimate.**
2. **No architecture design for features beyond the next 2 versions.**
3. **"Cool but not now" filter.** — Does Sean have enough users/data today?
4. **Data claims need math.**
5. **One solo developer = max 2 priorities at a time.**

## Priorities (會變動)

### Priority 1: v0.5 (next)
- **Temporal Signals**: recent_created_ratio + recently_active_ratio, top 3 competitor activity
- **Decision Tracking**: decision buttons (build/pivot/kill), linked to email + idea_hash

### Priority 2: Distribution (ongoing)
- Monitor Show HN + Dev.to comments
- Post DEV.to agent instructions article (draft ready)
- Follow up: Glama, PR #2346 (pinged), ClaudeMCP #45, mcp-get #176, Fleur #37

### Future Ideas (do NOT elaborate)
- Privacy mode / local LLM / Tor / decoy queries → v2.0+
- Decision Framework full version → after ground truth data
- Agent session memory / follow-up → v1.0+
- competitor_health detailed → v0.5

---

## Community Feedback Log（持續累積）

### 2026-03-01 Reddit r/ClaudeAI
- **反饋**：Agent instruction templates 過度工程化。MCP tool description 本身已告訴 agent 何時 call，不需要把 instruction 塞進 CLAUDE.md/.cursorrules 浪費 context window token。
- **修正**：templates/ 全部精簡為一行 hint，README 把 MCP 安裝設為主要，agent instruction 設為可選。
- **學到的**：MCP 設計哲學 = tool description 即文件。Threshold 邏輯（>80 STOP）是 tool 的責任，不該寫在 agent config 裡。開發者社群對 over-engineering 很敏感。

### Release 後同步更新 Checklist
每次 release 後必須逐一檢查：
1. pyproject.toml + __init__.py + engine.py（版號）
2. api/main.py（FastAPI title）
3. server.json（MCP Registry ×2）
4. tests/test_scoring.py + test_server_smoke.py
5. CHANGELOG.md + CHANGELOG.zh-TW.md
6. .claude/instructions.md（此檔 Current Status）
7. mnemox-ai.github.io/index.html（project stat）
8. mnemox-github-profile/profile/README.md
9. Git tag + GitHub Release + 確認 PyPI CI

---

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
7. Post-release: run the sync checklist above, don't rely on memory
