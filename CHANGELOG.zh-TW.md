[English](CHANGELOG.md) | 繁體中文

# 更新日誌

本專案所有重要變更都會記錄在此檔案。

## [0.3.0] - 2026-02-27

### 變更
- **關鍵字萃取全面改寫** — 三段式 Pipeline（Stage A/B/C）
  - Stage A：硬性過濾泛詞（`ai`、`tool`、`platform`、`system`、`framework`、`engine` 等）+ 擴充停用詞
  - Stage B：意圖錨點偵測 — 識別 1–2 個意圖核心詞（`monitoring`、`agent`、`rag`、`mcp`、`evaluation`、`cli`、`scraping`、`embedding`、`tracing`、`chatbot`…）
  - Stage C：同義詞展開（100+ 詞手寫字典），生成 3–8 條錨定查詢（`monitoring` → `observability / tracing / telemetry`；`evaluation` → `evals / benchmark`；`agent` → `tool calling / orchestration`…）
- 中文與中英混合輸入 tokenization 改善：輸入前自動映射（監控→monitoring、評測→evaluation、爬蟲→scraping、自動化→automation…）
- `extract_keywords()` 現在回傳最多 8 條 variant（原為 4 條），且每條都錨定在偵測到的意圖上

### 新增
- `scoring/synonyms.py` — SYNONYMS 同義詞字典 + INTENT_ANCHORS 意圖錨點集合（新模組）
- `tests/golden_ideas.json` — 25 條固定評測 ideas
- `tests/eval_keywords.py` — 關鍵字品質評測腳本（執行：`python tests/eval_keywords.py`）
- 20 個新 keyword 測試（共 93 個，原為 73 個）

### 改善
- Golden set 意圖錨點命中率：100%
- 垃圾詞比例：25 條 ideas 平均 2%
- 中文 / 中英混合輸入 → 穩定、準確的 query set
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
