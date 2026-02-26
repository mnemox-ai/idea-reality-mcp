[English](CHANGELOG.md) | 繁體中文

# 更新日誌

本專案所有重要變更都會記錄在此檔案。

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
