[English](CHANGELOG.md) | 繁體中文

# 更新日誌

本專案所有重要變更都會記錄在此檔案。

## [0.4.0] - 2026-03-01

### 新增
- **mnemox.ai/check Email Gate** — 輸入 email 解鎖轉向建議（pivot hints）
- `POST /api/subscribe` 端點 — email 收集（SQLite + stdout 雙寫備份）
- `GET /api/subscribers/count` 端點 — 內部監控用
- `/api/check` 回應新增 `idea_hash` 欄位（SHA256，共用 `db.idea_hash()`）
- **Score History**：SQLite 歷史追蹤（`GET /api/history/{idea_hash}`）
- **Agent Templates**：Claude/Cursor/Copilot/Windsurf 指令範本（`templates/`）
- **idea-check-action v1.0.0**：GitHub Action CI/CD idea 驗證（`mnemox-ai/idea-check-action`）
- 11 個新測試（共 138 個，原 127 個）

### 變更
- `/api/check` 回應現在包含 `idea_hash`，用於追蹤和 subscribe 流程
- DB 初始化同時建立 `score_history` 和 `subscribers` 兩個 table

## [0.3.2] - 2026-02-27

### 新增
- **LLM 驅動關鍵字萃取（Render API）** — Claude Haiku 4.5 從任何語言的 idea 描述生成最佳搜尋查詢，失敗時自動 fallback 到字典 pipeline
- `POST /api/extract-keywords` 公開端點（速率限制：50/IP/天）— 獨立關鍵字萃取
- 回應 `meta` 新增 `keyword_source` 欄位 — 標示關鍵字來自 `"llm"` 或 `"dictionary"`
- 記憶體內速率限制器（每 IP 每日重置）
- `scoring/llm.py` — MCP 客戶端呼叫 Render API（8 秒超時 + graceful fallback）
- `tests/test_llm.py` — 10 個 LLM 客戶端測試
- `tests/test_api_extract_keywords.py` — 8 個 API 端點測試
- `tests/eval_llm_vs_dict.py` — LLM vs 字典 54 條 golden ideas 評估腳本
- `docs/v0.4-comparison.md` — LLM vs 字典比較報告
- `api/requirements.txt` 新增 `anthropic>=0.40.0`
- `render.yaml` 新增 `ANTHROPIC_API_KEY` 環境變數

### 變更
- **README 全面改寫** — 攻擊性定位（「我們搜。他們猜。」）、競品比較表、「為什麼不直接問 ChatGPT？」段落
- `api/main.py` 在 `/api/check` 優先用 Haiku 萃取關鍵字，失敗時 fallback 到字典
- Haiku 回應的 markdown code fence 自動清除（模型會用 ``` 包住 JSON）
- MCP stdio（`tools.py`）使用 dictionary-only pipeline（100% anchor hit、無外部依賴）
- 版本號更新至 `0.3.2`

### 基礎設施
- **MCP Streamable HTTP transport**（`/mcp` 端點）— 支援 Smithery 和 MCP HTTP clients
- `smithery.yaml` Smithery marketplace 設定檔
- 上架 Smithery + 提交至 9+ MCP 目錄

### 統計
- 120 個測試通過（102 原有 + 18 新增）
- LLM eval：54/54 ideas 處理完成，50/54 anchor 命中（93%），0 次失敗
- 字典 eval：54/54 anchor 命中（100%）
- 中文 idea 品質：LLM 較佳 3/10、平手 6/10、字典較佳 1/10

### 發布通路（自 v0.3.1 起累積）
- 上架 Smithery marketplace（已公開）
- 提交至 9+ MCP 目錄：Smithery、PulseMCP、MCP Market、Glama、mcp.so、Cursor Directory、ClaudeMCP.com（PR #45）、mcp-get（PR #176）、Fleur（PR #37）

## [0.3.1] - 2026-02-27

### 修復
- **非科技領域搜尋精準度** — 改善法律、中醫、農業、宗教等非科技領域的關鍵字萃取與結果排序
  - 新增遺漏的中文映射：`文件`→document、`文檔`→document、`智慧`→smart、`問診`→consultation
  - `分析` 映射從 `analytics`（偏 BI）改為 `analysis`（通用）
  - 新增複合詞 `數據分析`→`data analytics` 保留 BI 語境
  - `analysis` 加入 INTENT_ANCHORS + 同義詞擴展
  - 新增「領域優先」查詢模板：非科技領域名詞排在動作動詞前面
  - 修正「雙錨點」查詢模板，加入領域上下文避免過於寬泛
- **GitHub 結果相關性排序** — 改為先按查詢匹配次數排序，再按星數。匹配多個查詢的 repo 排在前面。

### 新增
- 9 個非科技領域測試（102 個測試，從 93 增加）：中醫、法律、農業、佛教、寵物、問診
- `meta.version` 更新為 `"0.3.1"`

## [0.3.0] - 2026-02-27

### 變更
- **關鍵字萃取全面改寫** — 三段式 Pipeline（Stage A/B/C）
  - Stage A：硬性過濾泛詞（`ai`、`tool`、`platform`、`system`、`framework`、`engine` 等）+ 擴充停用詞
  - Stage B：意圖錨點偵測 — 識別 1–2 個意圖核心詞（`monitoring`、`agent`、`rag`、`mcp`、`evaluation`、`cli`、`scraping`、`embedding`、`tracing`、`chatbot`…）
  - Stage C：同義詞展開（100+ 詞手寫字典），生成 3–8 條錨定查詢（`monitoring` → `observability / tracing / telemetry`；`evaluation` → `evals / benchmark`；`agent` → `tool calling / orchestration`…）
- **中文／中英混合輸入全面支援** — 150+ 詞的 `CHINESE_TECH_MAP`，涵蓋 15+ 領域（科技、SaaS、醫療、法律、教育、製造、農業、太空、宗教、藝術、遊戲、政府…）
  - 按 key 長度排序（最長優先），避免複合詞被短詞搶先匹配
  - 絕不回傳原始中文 — 未映射字元自動清除
- `extract_keywords()` 現在回傳最多 8 條 variant（原為 4 條），且每條都錨定在偵測到的意圖上

### 新增
- `scoring/synonyms.py` — SYNONYMS 同義詞字典（80+ key）+ INTENT_ANCHORS 意圖錨點集合（90+ 項）
- `tests/golden_ideas.json` — 54 條固定評測 ideas（中英文）
- `tests/eval_keywords.py` — 關鍵字品質評測腳本（執行：`python tests/eval_keywords.py`）
- `tests/test_tw_chinese.py` — 46 個台灣中文輸入測試案例
- `tests/test_tw_niche.py` — 53 個跨領域中文輸入測試案例（15 大類）
- 20 個新 keyword 測試（共 93 個，原為 73 個）

### 修復
- 同義詞展開重複字 bug（`"redis redis"`、`"mcp server server"`）
- `追蹤` 改對應通用 `tracking`（原為 infra 限定的 `tracing`）

### 改善
- Golden set 意圖錨點命中率：100%（54/54 ideas）
- 垃圾詞比例：54 條 ideas 平均 4%
- 台灣中文輸入：98%+ 通過率（99 個測試案例，涵蓋一般 + 跨領域）
- 查詢輸出零中文字元洩漏
- `meta.version` 更新為 `"0.3.0"`

## [0.2.0] - 2026-02-25

### 新增
- **npm Registry 來源**（`sources/npm.py`）— 搜尋 npm 上的相似套件（免費，不需認證）
- **PyPI Registry 來源**（`sources/pypi.py`）— 搜尋 PyPI 上的相似 Python 套件
- **Product Hunt 來源**（`sources/producthunt.py`）— 搜尋 Product Hunt 上的相似產品（可選，需要 `PRODUCTHUNT_TOKEN`）
- **`depth: "deep"` 模式** — 使用 `asyncio.gather()` 平行查詢全部 5 個來源
- **改進關鍵字萃取** — 複合詞偵測（如 "machine learning"）、技術關鍵字優先、擴充停用詞、Registry 最佳化查詢變體
- 新評分函式：`_npm_score()`、`_pypi_score()`、`_ph_score()`
- Deep mode 評分權重：GitHub repos 25% + stars 10% + HN 15% + npm 20% + PyPI 15% + Product Hunt 15%
- Product Hunt 不可用時自動重新分配權重
- `top_similars` 現在包含 npm、PyPI、Product Hunt 的結果（前綴 `npm:`、`pypi:`、`ph:`）
- `sources/__init__.py` 匯出所有來源函式和 dataclass
- 42 個新測試（總計 73 個，原本 31 個）
- 此 CHANGELOG

### 變更
- `extract_keywords()` 現在回傳最多 4 個變體（原為 3），包含 Registry 最佳化查詢
- `compute_signal()` 接受可選的 `npm_results`、`pypi_results`、`ph_results` 關鍵字參數
- `meta.version` 更新為 `"0.2.0"`
- `meta.sources_used` 現在動態反映實際查詢的來源
- README 更新 deep mode 文件、評分權重和新環境變數

## [0.1.0] - 2026-02-25

### 新增
- 首次發布
- `idea_check` MCP 工具，支援 `idea_text` 和 `depth` 參數
- GitHub Search API 來源（`sources/github.py`）
- Hacker News Algolia API 來源（`sources/hn.py`）
- 加權公式評分引擎（GitHub 60% + stars 20% + HN 20%）
- 關鍵字萃取，含停用詞過濾
- 重複可能性分類（low / medium / high）
- 轉向建議生成（3 個可執行建議）
- 31 個測試
- GitHub Actions CI/CD
- 發布至 PyPI
