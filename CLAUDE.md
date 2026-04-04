@.claude/instructions.md

## REST API (Render — 2026-02-26 新增)

- **生產 URL：** `https://idea-reality-mcp.onrender.com`
- **入口：** `api/main.py`（FastAPI wrapper，直接 import scoring engine）
- **端點：**
  - `GET /health` — liveness probe
  - `POST /api/check` — body: `{idea_text, depth}` → 回傳完整 report dict
  - `ANY /mcp` — MCP Streamable HTTP transport（Smithery / MCP HTTP clients 連接用）
- **CORS：** 允許 mnemox.ai、mnemox-ai.github.io、localhost
- **部署：** `render.yaml`（free tier，sleep/wake acceptable）
- **PRODUCTHUNT_TOKEN：** optional，未設時 gracefully skip PH source

## Recent Changes
- [2026-04-04] fix: v0.5.1 scoring accuracy — keyword synonyms(40+), PyPI two-tier rewrite(JSON+libraries.io), SO backoff hardening, dictionary-first strategy. todo 35→74, expense 40→77, chatbot 69→75. 298 tests.
- [2026-03-25] fix: REST/MCP parity (SO added), dead payment code removed(-790 lines), deps pinned, _get_client_ip unified(×9), error format consistent. 277 tests.
- [2026-03-25] feat: onboarding CLI — `idea-reality setup/doctor/config`, 8 platforms, TERMS.md. README updated.
- [2026-03-25] security: parameterized SQL(×6), Discord IP hash(×2), idea_text max_length(×4). 277 tests.
- [2026-03-23] fix: /api/check rate limit (100/day per IP) + IP extraction consistency (request.client.host)
- [2026-03-22] GEO: README + README.zh-TW 加 FAQ 式開頭、When to use、How it works 3 步驟
- [2026-03-19] Repo 清理：根目錄 25→17 files，zh docs 移到 docs/zh/，gitignore 垃圾檔，README 改善
- [2026-03-19] feat: Chinese pivot hints (lang param in engine + API + security validation)
- [2026-03-19] feat: badge-data + crowd-intel + pulse API endpoints（3 個新 endpoint）
- [2026-03-19] feat: 移除 $9.99 PayPal paywall，全部免費
- [2026-03-19] feat: GET /api/pulse endpoint (weekly volume, top keywords, country distribution, trending ideas). 277 tests passing.
- [2026-03-15] PayPal 付款修復：credential typo、capture endpoint 加 language 參數、quick mode 不顯示 paywall、付款回來 UX 重寫
- [2026-03-15] Search Quality Improvement: idea expansion (LLM), per-platform queries, relevance filtering. 275 tests
- [2026-03-15] Merged PR #3 (antonio-mello-ai): StackOverflow as 6th data source (deep mode)
- [2026-03-15] Jarvis 系統建立，加入 /morning 掃描範圍

## Current Status
- v0.5.1, 298 tests passing
- **PayPal 已移除** — 全部免費，商業模式轉向品牌 + 流量
- 新增 3 API endpoints: badge-data, crowd-intel, pulse
- pivot hints 支援中文（lang=zh）
- 8 個 production users（Clerk），2,691 筆掃描，35 國
- Google SEO 第一大來源，358+ stars
