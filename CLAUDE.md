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
- ✅ **P1 語意 embedding 全部完成、LIVE on prod**（`85d7401`）。`OPENAI_API_KEY` 已設在 Render，`/api/crowd-intel` 回 `match_mode:"semantic"` + `demand_heat`。**沒有待辦，這條收掉。**
  - ⚠️ 過程踩到 OOM：設 key 後舊的「in-memory numpy 矩陣」路徑在 512MB Starter 上爆記憶體 crash-loop → 改成 **Turso 原生向量搜尋**（`vector_distance_cos`，DB 端算 cosine、app 記憶體歸零）根治，續留 $7 Starter 不用升級。細節 `docs/P1-semantic-embeddings.md`。
  - Render 我有 API key（存在 gitignored `CHEATSHEET.local` 的 `RENDER_API_KEY`）＝可直接查 deploy/log/改 env/觸發部署。Turso 連線也在 `CHEATSHEET.local`。
- ⚠️ 這台桌機 `.git` 有個從別台機器(johns)帶來的 phantom worktree 參照，`git status`/`git diff` 會報 fatal（但 commit/push/pull 正常）。**筆電 fresh clone 或 pull 不受影響**。

## Recent Changes
- [2026-07-06] **perf: 語意搜尋改用 Turso 原生向量、根治 OOM crash-loop → semantic LIVE on prod（`85d7401`）**。
  - **症狀**：Sean 在 Render 設 `OPENAI_API_KEY` 後，服務對外 502 crash-loop。查 log＝instance 每 1-3 分鐘 restart、無 Python traceback ＝ **OOM SIGKILL**。
  - **根因**：wiring 的 in-memory numpy 矩陣路徑，一被 crowd-intel / full-report 呼叫就把 10,150 筆向量（~60MB，`np.vstack` 載入時再翻倍）疊在 ~300MB baseline 上 → 破 512MB Starter → worker 被砍。`/api/check` quick（AngelRun 用的）不走 crowd_intelligence 所以沒事。
  - **止血**：先用 Render API 移除 key + 觸發 redeploy → 服務回 keyword 模式恢復穩定。
  - **根治**：`search_similar_by_embedding` 改成 backend 分流——**Turso(prod) 走原生 `vector_distance_cos`（DB 端算 cosine、`ORDER BY dist LIMIT k`，app 記憶體 ~0）**；local SQLite(dev/test) 保留 numpy 矩陣。**現有 raw float32 BLOB 已相容 F32_BLOB（self-distance≈2.9e-8）→ 零 migration、零 re-backfill**。12/12 測試綠、原生路徑對真 Turso 驗過（paraphrase 匹配、min_score/exclude 正確）。
  - **驗收**：重設 key + 部署新 code → `match_mode:"semantic"` + `demand_heat`（「過去 90 天 6 筆相關搜尋，rising」）、連打 crowd-intel 後 **instance restart = 0**、續留 $7 Starter（不用升 Standard，也不用搬 Vercel——serverless 反而不適合這個常駐矩陣設計）。
  - ⚠️ 本機 libsql **sync** client 在 Windows 會 hang → 原生路徑本機只能用 Turso **HTTP** client（`scripts/turso_http.py`）或對 prod 驗；Render Linux 正常。
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
