[English](README.md) | 繁體中文

# idea-reality-mcp

AI 開發前的現實查核工具。別再重複造輪子了。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)
[![PyPI](https://img.shields.io/pypi/v/idea-reality-mcp.svg)](https://pypi.org/project/idea-reality-mcp/)
[![Smithery](https://smithery.ai/badge/idea-reality-mcp)](https://idea-reality-mcp--mnemox-ai.run.tools)

> **v0.3 正式發布** — 三段式關鍵字萃取 Pipeline、150+ 中文詞彙對照、90+ 意圖錨點、80+ 同義詞展開。直接支援中文和中英混合輸入。

## 這是什麼

`idea-reality-mcp` 是一個 MCP Server，提供 `idea_check` 工具。當 AI coding agent 準備開始寫東西時，它可以呼叫這個工具，自動掃描多個來源，查看是否已有類似的專案。

**Quick mode**（預設）：GitHub + Hacker News
**Deep mode**：GitHub + HN + npm + PyPI + Product Hunt（所有來源平行查詢）

工具回傳：

- **reality_signal**（0-100）：你的點子和現有專案的重疊程度
- **duplicate_likelihood**：low / medium / high
- **evidence**：所有來源的原始搜尋數據
- **top_similars**：來自 GitHub、npm、PyPI、Product Hunt 的最相似專案
- **pivot_hints**：3 個基於競爭態勢的可執行建議

## 快速開始

```bash
# 安裝並執行
uvx idea-reality-mcp

# 或透過 Smithery 安裝
npx -y @smithery/cli install idea-reality-mcp --client claude

# 或 clone 到本地執行
git clone https://github.com/mnemox-ai/idea-reality-mcp.git
cd idea-reality-mcp
uv run idea-reality-mcp
```

### 可選：環境變數

```bash
# 提升 GitHub API 速率限制
export GITHUB_TOKEN=ghp_your_token_here

# 啟用 Product Hunt 搜尋（deep mode）
export PRODUCTHUNT_TOKEN=your_ph_token_here
```

## Claude Desktop 設定

加入 `~/Library/Application Support/Claude/claude_desktop_config.json`（macOS）或 `%APPDATA%\Claude\claude_desktop_config.json`（Windows）：

```json
{
  "mcpServers": {
    "idea-reality": {
      "command": "uvx",
      "args": ["idea-reality-mcp"]
    }
  }
}
```

## Cursor 設定

加入專案根目錄的 `.cursor/mcp.json`：

```json
{
  "mcpServers": {
    "idea-reality": {
      "command": "uvx",
      "args": ["idea-reality-mcp"]
    }
  }
}
```

## 建議：加入你的 CLAUDE.md

讓 AI agent 在你討論新點子時自動呼叫 `idea_check`，在專案的 `CLAUDE.md`（或同等指令檔）加入這行：

```
當使用者討論新專案點子或詢問市場競爭時，使用 idea-reality-mcp 的 idea_check 工具。
```

這樣 agent 不需要你明確指定，就能自動辨識何時該呼叫工具。

## 工具規格

### `idea_check`

**輸入：**

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `idea_text` | string | 是 | 自然語言描述你的點子 |
| `depth` | `"quick"` \| `"deep"` | 否 | `"quick"` = GitHub + HN（預設）。`"deep"` = 全部 5 個來源平行查詢 |

**輸出：**

```json
{
  "reality_signal": 72,
  "duplicate_likelihood": "high",
  "evidence": [
    {"source": "github", "type": "repo_count", "query": "...", "count": 342, "detail": "..."},
    {"source": "github", "type": "max_stars", "query": "...", "count": 15000, "detail": "..."},
    {"source": "hackernews", "type": "mention_count", "query": "...", "count": 18, "detail": "..."},
    {"source": "npm", "type": "package_count", "query": "...", "count": 56, "detail": "..."},
    {"source": "pypi", "type": "package_count", "query": "...", "count": 23, "detail": "..."},
    {"source": "producthunt", "type": "product_count", "query": "...", "count": 8, "detail": "..."}
  ],
  "top_similars": [
    {"name": "user/repo", "url": "https://github.com/...", "stars": 15000, "updated": "...", "description": "..."},
    {"name": "npm:cool-pkg", "url": "https://npmjs.com/...", "stars": 0, "updated": "", "description": "..."},
    {"name": "pypi:cool-pkg", "url": "https://pypi.org/...", "stars": 0, "updated": "", "description": "..."}
  ],
  "pivot_hints": [
    "High existing competition detected. Consider a niche differentiator...",
    "The leading project (user/repo, 15000 stars) may have gaps...",
    "Consider building an integration or plugin..."
  ],
  "meta": {
    "checked_at": "2026-02-25T10:30:00+00:00",
    "sources_used": ["github", "hackernews", "npm", "pypi", "producthunt"],
    "depth": "deep",
    "version": "0.3.0"
  }
}
```

### 評分權重

**Quick mode：** GitHub repos 60% + GitHub stars 20% + HN 提及 20%

**Deep mode：** GitHub repos 25% + GitHub stars 10% + HN 提及 15% + npm 20% + PyPI 15% + Product Hunt 15%

如果 Product Hunt 不可用（未設定 token），其權重會自動重新分配給其他來源。

## 範例提示

```
在開始之前，幫我查一下這個點子有沒有人做過：
一個自動把 Figma 設計稿轉成 React 元件的 CLI 工具

idea_check("AI code review bot for GitHub PRs", depth="deep")

幫我查市場現實：即時協作的 Markdown 編輯器加上 AI 自動完成
```

## Roadmap

- [x] **v0.1** — GitHub + HN 搜尋，基本評分
- [x] **v0.2** — `depth: "deep"` 支援 npm、PyPI、Product Hunt；改進關鍵字萃取
- [x] **v0.3** — 三段式關鍵字 Pipeline（Stage A/B/C）、150+ 中文詞彙對照、同義詞展開
- [x] **v0.3.1** — 非科技領域搜尋精準度修復，相關性加權排序（目前版本）
- [ ] **v0.4** — LLM 驅動的關鍵字萃取和語意相似度比對
- [ ] **v0.5** — 趨勢偵測和時機分析
- [ ] **v1.0** — Idea Memory Dataset（匿名使用紀錄）

## 授權

MIT — 見 [LICENSE](LICENSE)

## 線上試用

前往 [mnemox.ai/check](https://mnemox.ai/check) 在瀏覽器直接試用 — 不需安裝。

## 聯絡

由 [Mnemox AI](https://mnemox.ai) 打造 · [dev@mnemox.ai](mailto:dev@mnemox.ai)
