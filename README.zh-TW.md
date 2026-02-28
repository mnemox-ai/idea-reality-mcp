[English](README.md) | 繁體中文

# idea-reality-mcp

**你的 AI Agent 在動手前自動檢查。不需要你記。**

唯一能在 Agent 寫第一行 code 前搜尋 5 個真實資料庫的 MCP 工具。不用手動搜尋。不會忘記。只有事實。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)
[![PyPI](https://img.shields.io/pypi/v/idea-reality-mcp.svg)](https://pypi.org/project/idea-reality-mcp/)
[![Smithery](https://smithery.ai/badge/idea-reality-mcp)](https://idea-reality-mcp--mnemox-ai.run.tools)
[![GitHub stars](https://img.shields.io/github/stars/mnemox-ai/idea-reality-mcp)](https://github.com/mnemox-ai/idea-reality-mcp)

<p align="center">
  <a href="https://mnemox.ai/check"><strong>👉 在瀏覽器直接試用 — 免安裝</strong></a>
</p>

## 它做什麼

```
你：「AI code review 工具」

idea-reality-mcp：
├── reality_signal: 90/100
├── GitHub repos: 847 個
├── 最大競品: reviewdog (9,094 ⭐)
├── npm 套件: 56 個
├── HN 討論: 254 則
└── 判定: HIGH — 建議找利基切入
```

一個數字。五個真實來源。Agent 自己決定下一步。

## 問題

每個開發者都踩過這個坑：花了好幾天做一個 side project，結果 GitHub 一搜發現有人做了，而且有 5,000 stars。

你問 ChatGPT：*「有沒有人做過 X？」*

ChatGPT 說：*「這是個很好的點子！市面上有一些類似工具，但你一定可以做得更好！」*

**這不是驗證。這是啦啦隊。**

## 「為什麼不直接 Google？」

這是我們最常被問的問題。老實回答：

**Google 很好用 — 前提是你記得去搜。** 問題不在搜尋品質，而是你的 AI Agent 在開始寫 code 前從來不會 Google。

idea-reality-mcp 跑在你的 Agent **裡面**。自動觸發。不管你記不記得，搜尋都會發生。

| | Google | ChatGPT / SaaS 驗證工具 | idea-reality-mcp |
|---|---|---|---|
| **誰來跑** | 你，手動 | 你，手動 | 你的 Agent，自動 |
| **輸入** | 自己想關鍵字 | 自然語言 | 自然語言 |
| **輸出** | 10 條藍色連結 — 自己判斷 | 「聽起來不錯！」 | 0-100 分 + 證據 + 競品 |
| **來源** | 網頁 | 無（LLM 生成） | GitHub + HN + npm + PyPI + PH |
| **跨平台** | 每個站分開搜 | N/A | 5 個來源平行搜，一次搞定 |
| **工作流** | Tab 之間複製貼上 | 另一個 App | MCP / CLI / API / CI |
| **可驗證** | 是（手動） | 否 | 是（每個數字有來源） |
| **價格** | 免費 | 免費試用 → 付費牆 | 免費、開源、永久 |

**一句話：不是你在用它，是你的 Agent 在用。這才是重點。**

## 試用（30 秒）

```bash
uvx idea-reality-mcp
```

或[在瀏覽器直接試用](https://mnemox.ai/check) — 不需安裝，即時結果。

## 安裝

### Claude Code（CLI）— 最快

```bash
claude mcp add idea-reality -- uvx idea-reality-mcp
```

### Claude Desktop / Cursor

貼入你的 MCP 設定檔（`claude_desktop_config.json` 或 `.cursor/mcp.json`）：

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

<details>
<summary>設定檔位置</summary>

- **Claude Desktop (macOS):** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Claude Desktop (Windows):** `%APPDATA%\Claude\claude_desktop_config.json`
- **Cursor:** 專案根目錄的 `.cursor/mcp.json`

</details>

### Smithery（遠端）

```bash
npx -y @smithery/cli install idea-reality-mcp --client claude
```

### 可選：環境變數

```bash
export GITHUB_TOKEN=ghp_...        # 提升 GitHub API 速率限制
export PRODUCTHUNT_TOKEN=your_...  # 啟用 Product Hunt（deep mode）
```

### 可選：Agent 自動觸發

MCP tool 描述已經告訴你的 Agent `idea_check` 做什麼。如果想讓它**主動執行**（每個新專案自動檢查），加一行到你的 `CLAUDE.md`、`.cursorrules` 或 `.github/copilot-instructions.md`：

```
開始新專案時，用 idea_check MCP tool 檢查是否已有類似專案存在。
```

> 完整範本見 [templates/](templates/)。

## 使用方式

### 「我有個 side project 點子，該不該做？」

對你的 AI Agent 說：

```
在開始之前，幫我查一下有沒有人做過：
一個自動把 Figma 設計稿轉成 React 元件的 CLI 工具
```

Agent 會呼叫 `idea_check`，回傳：reality_signal、競品列表、轉向建議。

### 「找競品和替代方案」

```
idea_check("open source feature flag service", depth="deep")
```

Deep mode 平行掃描全部 5 個來源 — GitHub repos、HN 討論、npm 套件、PyPI 套件、Product Hunt — 回傳排序結果。

### 「Sprint 前的 Build-or-Buy 檢查」

```
我們準備花 2 週做內部的 error tracking 工具。
先跑一次現實檢查。
```

如果 signal 回來 85+，而且有成熟的開源替代品——你剛省了團隊 2 週。

## 新功能：AI 驅動的搜尋智能

**Claude Haiku 4.5** 從你的 idea 描述生成最佳搜尋查詢 — 支援任何語言 — 並自動 fallback 到經過實戰驗證的字典 pipeline。

| | 之前 | 現在 |
|---|---|---|
| 英文 idea | ✅ 良好 | ✅ 良好 |
| 中文 / 非英文 idea | ⚠️ 字典查找（150+ 詞彙） | ✅ 原生理解 |
| 模糊描述 | ⚠️ 關鍵字比對 | ✅ 語意萃取 |
| 可靠性 | 100%（不需外部 API） | 100%（自動 fallback 到字典） |

LLM 理解你的 idea。字典是你的安全網。**永遠有結果。**

## 工具規格

### `idea_check`

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `idea_text` | string | 是 | 自然語言描述你的點子 |
| `depth` | `"quick"` \| `"deep"` | 否 | `"quick"` = GitHub + HN（預設）。`"deep"` = 全部 5 個來源平行查詢 |

**輸出：** `reality_signal`（0-100）、`duplicate_likelihood`、`evidence[]`、`top_similars[]`、`pivot_hints[]`、`meta{}`

<details>
<summary>完整輸出範例</summary>

```json
{
  "reality_signal": 72,
  "duplicate_likelihood": "high",
  "evidence": [
    {"source": "github", "type": "repo_count", "query": "...", "count": 342},
    {"source": "github", "type": "max_stars", "query": "...", "count": 15000},
    {"source": "hackernews", "type": "mention_count", "query": "...", "count": 18},
    {"source": "npm", "type": "package_count", "query": "...", "count": 56},
    {"source": "pypi", "type": "package_count", "query": "...", "count": 23},
    {"source": "producthunt", "type": "product_count", "query": "...", "count": 8}
  ],
  "top_similars": [
    {"name": "user/repo", "url": "https://github.com/...", "stars": 15000, "description": "..."}
  ],
  "pivot_hints": [
    "競爭激烈。考慮找一個利基差異化方向...",
    "領先專案可能在某些面向有缺口...",
    "考慮做整合或外掛，而非從頭造輪子..."
  ],
  "meta": {
    "sources_used": ["github", "hackernews", "npm", "pypi", "producthunt"],
    "keyword_source": "llm",
    "depth": "deep",
    "version": "0.4.0"
  }
}
```

</details>

### 評分權重

| 模式 | GitHub repos | GitHub stars | HN | npm | PyPI | Product Hunt |
|------|-------------|-------------|-----|-----|------|-------------|
| Quick | 60% | 20% | 20% | — | — | — |
| Deep | 25% | 10% | 15% | 20% | 15% | 15% |

Product Hunt 不可用時（未設 token），權重自動重新分配。

## CI：PR 開啟時自動檢查

用 [idea-check-action](https://github.com/mnemox-ai/idea-check-action) 驗證新功能提案：

```yaml
name: Idea Reality Check
on:
  issues:
    types: [opened]

jobs:
  check:
    if: contains(github.event.issue.labels.*.name, 'proposal')
    runs-on: ubuntu-latest
    steps:
      - uses: mnemox-ai/idea-check-action@v1
        with:
          idea: ${{ github.event.issue.title }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Roadmap

- [x] **v0.1** — GitHub + HN 搜尋，基本評分
- [x] **v0.2** — Deep mode（npm、PyPI、Product Hunt），改進關鍵字萃取
- [x] **v0.3** — 三段式關鍵字 Pipeline，150+ 中文詞彙對照，同義詞展開，LLM 搜尋智能（Render API）
- [x] **v0.4** — Email gate、Score History、Agent Templates、GitHub Action
- [ ] **v0.5** — 時序信號（趨勢偵測和時機分析）
- [ ] **v1.0** — Idea Memory Dataset（匿名使用紀錄）

## 結果不準？

如果工具漏掉了明顯的競品，或回傳不相關的結果：

1. [開一個 Issue](https://github.com/mnemox-ai/idea-reality-mcp/issues/new?template=inaccurate-result.yml)，附上你的 idea text 和輸出
2. 我們會改進該領域的關鍵字萃取

## 授權

MIT — 見 [LICENSE](LICENSE)

## 聯絡

由 [Mnemox AI](https://mnemox.ai) 打造 · [dev@mnemox.ai](mailto:dev@mnemox.ai)
