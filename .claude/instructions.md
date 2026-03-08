# IDEA-REALITY-MCP — Project Context

## What This Is
Mnemox Idea Reality MCP Server v0.4.0 — pre-build reality check for AI coding agents.
`idea_check` scans GitHub, HN, npm, PyPI, Product Hunt → returns reality_signal (0-100).
**Status: 暫停開發中，持續監測流量。** Google SEO 第一大來源，持續有不同國家用戶查詢。290+ stars。

## Quick Ref
- GitHub: mnemox-ai/idea-reality-mcp | PyPI: idea-reality-mcp
- Tests: `uv run pytest tests/ -v` (181 tests)
- Entry: `python -m idea_reality_mcp` or `uv run python -m idea_reality_mcp`
- Tech: Python 3.11+, FastMCP 3.x, httpx (async), uv

## Architecture

```
src/idea_reality_mcp/
├── server.py          # FastMCP server
├── tools.py           # idea_check (quick + deep, asyncio.gather)
├── scoring/
│   ├── engine.py      # reality_signal formula + 3-stage keyword extraction
│   ├── synonyms.py    # INTENT_ANCHORS (90+) + SYNONYMS (80+)
│   └── llm.py         # Haiku 4.5 integration (Render API)
└── sources/           # github.py, hn.py, npm.py, pypi.py, producthunt.py

api/
├── main.py            # FastAPI (REST + MCP Streamable HTTP)
├── db.py              # Score History (SQLite)
└── requirements.txt
```

## API Endpoints (Render: https://idea-reality-mcp.onrender.com)
- `POST /api/check` — `{idea_text, depth}` → report + idea_hash
- `POST /api/extract-keywords` — Haiku 4.5 (50/IP/day)
- `GET  /api/history/{idea_hash}` — score history
- `POST /api/subscribe` — email collection (dual-write: SQLite + stdout)
- `ANY  /mcp` — MCP Streamable HTTP
- Render env: ANTHROPIC_API_KEY + GITHUB_TOKEN + DISCORD_WEBHOOK_URL + EXPORT_KEY

## Modes
- **quick**: GitHub + HN (repos 60% + stars 20% + HN 20%)
- **deep**: 5 sources parallel (repos 25% + stars 10% + HN 15% + npm 20% + PyPI 15% + PH 15%)

## Key Design Decisions
- Protocol, not SaaS — no dashboard, no user accounts
- Zero storage by default (MCP stdio stores nothing)
- Scoring: simple, explainable, not ML
- Graceful degradation — partial results if any source fails
- Discord webhook = 永久查詢資料庫（每次 /api/check 自動推送）

## v0.5 Ideas (when resumed)
- Temporal Signals: recent_created_ratio + recently_active_ratio
- Decision Tracking: build/pivot/kill buttons

## Community Lessons
- MCP 設計哲學 = tool description 即文件，不需要塞 instruction 到 agent config
- 差異化不在搜尋品質，在 agent 自動觸發
- Email gate 在結果尾巴 = 低轉換率（已確認 0 subscribers）

## Rules
1. Run tests after changes: `uv run pytest tests/ -v`
2. Keep scoring formula explainable
3. No SaaS features
4. README is marketing — sharp and technical
5. New sources → `sources/` as own adapter file
6. Post-release: sync checklist (pyproject → api/main → server.json → CHANGELOG → website → profile → PyPI)
