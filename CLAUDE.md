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

## 🔑 HANDOFF — 待 Sean 處理（2026-07-06，換筆電接續）
- **P1 語意 embedding 已上 origin/main + Render 部署中。最後一步：在 Render dashboard 設 `OPENAI_API_KEY`。**
  設好前 crowd 優雅 fallback keyword（＝今天行為、零風險）；設好後下個請求自動載 10,150 筆語意索引，`match_mode` 變 "semantic" + 出 `demand_heat`。
  驗證：`POST /api/crowd-intel`（帶真 idea_hash）→ 期望 `match_mode:"semantic"`。細節 `docs/P1-semantic-embeddings.md`。
- ⚠️ 這台桌機 `.git` 有個從別台機器(johns)帶來的 phantom worktree 參照，`git status`/`git diff` 會報 fatal（但 commit/push/pull 正常）。**筆電 fresh clone 或 pull 不受影響**。

## Recent Changes
- [2026-07-06] **feat: P1 語意 embedding 護城河（activate 1 萬筆 query log）— foundation + backfill + wiring 全上 origin/main（`16ccb15`+`5ff301b`+`b191cce`），Render 部署中**。
  - **引擎**：`api/embeddings.py`（OpenAI text-embedding-3-small，httpx，float32 BLOB）+ `db.py`（embedding 欄 + 記憶體矩陣快取 `_load_embedding_matrix` TTL + 向量化 cosine `search_similar_by_embedding`）+ `scripts/turso_http.py`/`backfill_embeddings_http.py`（Turso HTTP API，因 libsql sync client 在 Windows 掛住）。
  - **backfill**：prod Turso `score_history` **10,150/10,150 全嵌入**（~$0.008），語意品質實測（zero-keyword paraphrase 正確匹配、cosine roundtrip 1.0000）。
  - **wiring**：`report._build_crowd_intelligence`（完整報告）+ `/api/crowd-intel` 走語意（idea_hash 去重、min_score 0.45、keyword fallback＝零 regression）+ **demand_heat**（90 天相似查詢數+趨勢，verdict 從「判決」翻「導航」）+ `match_mode` 欄。不碰 reality-score 公式。12/12 測試綠。
  - **⚠️ git 意外（已恢復）**：wiring 時失敗的 stash/checkout 污染本機工作區、commit 出壞 revert commit 到舊 `feat/semantic-embeddings`；已 reset origin/main 乾淨重貼並刪壞分支，**origin/main 全程正確**。
  - **next**：Sean 設 Render `OPENAI_API_KEY`（見上 HANDOFF）。
- [2026-04-14] fix: search engine accuracy — GitHub retry with backoff(403/429), npm relevance filter(cap 500), LLM keyword hyphen→space normalization. Root cause: GitHub returning 0 for 80% queries, npm inflated 500K+. 289 tests(+10 new).
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
- v0.5.1+, 289 tests passing (10 new GitHub retry + npm relevance tests)
- **PayPal 已移除** — 全部免費，商業模式轉向品牌 + 流量
- 新增 3 API endpoints: badge-data, crowd-intel, pulse
- pivot hints 支援中文（lang=zh）
- 8 個 production users（Clerk），2,691 筆掃描，35 國
- Google SEO 第一大來源，358+ stars
