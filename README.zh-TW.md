[English](README.md) | 繁體中文

# idea-reality-mcp

**別再重複造輪子。**

花了 3 週寫一個工具，上線後才發現有人早就做了——還有 5,000 stars。

`idea_check` 在你的 Agent 寫第一行 code 前，掃描 GitHub、Hacker News、npm、PyPI、Product Hunt、Stack Overflow。一次呼叫。六個資料庫。用分數取代猜測。

[![PyPI](https://img.shields.io/pypi/v/idea-reality-mcp.svg)](https://pypi.org/project/idea-reality-mcp/)
[![Smithery](https://smithery.ai/badge/idea-reality-mcp)](https://smithery.ai/server/idea-reality-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-275%20passing-brightgreen.svg)]()
[![GitHub stars](https://img.shields.io/github/stars/mnemox-ai/idea-reality-mcp)](https://github.com/mnemox-ai/idea-reality-mcp)
[![Downloads](https://static.pepy.tech/badge/idea-reality-mcp)](https://pepy.tech/project/idea-reality-mcp)

<p align="center">
  <a href="cursor://anysphere.cursor-deeplink/mcp/install?name=idea-reality&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22idea-reality-mcp%22%5D%7D">
    <img src="https://cursor.com/deeplink/mcp-install-dark.svg" alt="Install in Cursor" height="32">
  </a>
</p>

## 你會看到什麼

```
你：「AI code review 工具」

idea_check →
├── reality_signal: 92/100
├── trend: accelerating ↗（市場加速中）
├── market_momentum: 73/100
├── GitHub repos: 847 個（45% 在近 6 個月建立）
├── 最大競品: reviewdog (9,094 ⭐)
├── npm 套件: 56 個
├── HN 討論: 254 則（趨勢上升）
├── Stack Overflow: 1,203 個問題
└── 判定: HIGH — 市場正在加速，快找利基切入
```

一個分數。六個來源。趨勢偵測。Agent 自己決定下一步。

<p align="center">
  <a href="https://mnemox.ai/check"><strong>在瀏覽器直接試用 — 免安裝</strong></a>
</p>

## 快速開始

**1. 安裝並執行**

```bash
uvx idea-reality-mcp
```

**2. 加到你的 MCP 客戶端**

<details>
<summary>Claude Desktop — <code>claude_desktop_config.json</code></summary>

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

設定檔位置：**macOS** `~/Library/Application Support/Claude/claude_desktop_config.json` · **Windows** `%APPDATA%\Claude\claude_desktop_config.json`

</details>

<details>
<summary>Claude Code</summary>

```bash
claude mcp add idea-reality -- uvx idea-reality-mcp
```

</details>

<details>
<summary>Cursor — <code>.cursor/mcp.json</code></summary>

或點上方按鈕一鍵安裝。

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

</details>

<details>
<summary>Smithery（遠端，不需本地安裝）</summary>

```bash
npx -y @smithery/cli install idea-reality-mcp --client claude
```

</details>

**3. 開始使用**

對你的 Agent 說：

```
在開始之前，幫我查一下有沒有人做過：
一個自動把 Figma 設計稿轉成 React 元件的 CLI 工具
```

Agent 會呼叫 `idea_check`，回傳：reality_signal、競品列表、轉向建議。

## 為什麼不直接 Google？

**Google 很好用——前提是你記得去搜。** 問題不在搜尋品質，而是你的 AI Agent 在開始寫 code 前從來不會 Google。

`idea_check` 跑在你的 Agent **裡面**。自動觸發。不管你記不記得，搜尋都會發生。

| | Google | ChatGPT / SaaS 驗證工具 | idea-reality-mcp |
|---|---|---|---|
| **誰來跑** | 你，手動 | 你，手動 | 你的 Agent，自動 |
| **輸出** | 10 條藍色連結 | 「聽起來不錯！」 | 0-100 分 + 證據 + 競品 |
| **來源** | 網頁 | 無（LLM 生成） | GitHub + HN + npm + PyPI + PH + SO |
| **工作流** | Tab 之間複製貼上 | 另一個 App | MCP / CLI / API / CI |
| **價格** | 免費 | 免費試用 → 付費牆 | 免費、開源（MIT） |

## 模式

| 模式 | 來源 | 用途 |
|------|------|------|
| **quick**（預設） | GitHub + HN | 快速 sanity check，< 3 秒 |
| **deep** | GitHub + HN + npm + PyPI + Product Hunt + Stack Overflow | 完整競爭掃描 |

### 評分權重

| 來源 | Quick | Deep |
|------|-------|------|
| GitHub repos | 60% | 22% |
| GitHub stars | 20% | 9% |
| Hacker News | 20% | 14% |
| npm | — | 18% |
| PyPI | — | 13% |
| Product Hunt | — | 14% |
| Stack Overflow | — | 10% |

Product Hunt 或 Stack Overflow 不可用時，權重自動重新分配。

## 工具規格

### `idea_check`

| 參數 | 型別 | 必填 | 說明 |
|------|------|------|------|
| `idea_text` | string | 是 | 自然語言描述你的點子 |
| `depth` | `"quick"` \| `"deep"` | 否 | `"quick"` = GitHub + HN（預設）。`"deep"` = 全部 6 個來源 |

<details>
<summary>完整輸出範例</summary>

```json
{
  "reality_signal": 72,
  "duplicate_likelihood": "high",
  "trend": "accelerating",
  "sub_scores": { "market_momentum": 73 },
  "evidence": [
    {"source": "github", "type": "repo_count", "query": "...", "count": 342},
    {"source": "github", "type": "max_stars", "query": "...", "count": 15000},
    {"source": "hackernews", "type": "mention_count", "query": "...", "count": 18},
    {"source": "npm", "type": "package_count", "query": "...", "count": 56},
    {"source": "pypi", "type": "package_count", "query": "...", "count": 23},
    {"source": "producthunt", "type": "product_count", "query": "...", "count": 8},
    {"source": "stackoverflow", "type": "question_count", "query": "...", "count": 120}
  ],
  "top_similars": [
    {"name": "user/repo", "url": "https://github.com/...", "stars": 15000, "description": "..."}
  ],
  "pivot_hints": [
    "競爭激烈。考慮找一個利基差異化方向...",
    "領先專案可能在某些面向有缺口..."
  ]
}
```

</details>

## REST API

不用 MCP？直接呼叫 API：

```bash
curl -X POST https://idea-reality-mcp.onrender.com/api/check \
  -H "Content-Type: application/json" \
  -d '{"idea_text": "AI code review tool", "depth": "quick"}'
```

免費，不需 API key。

## CI：PR 開啟時自動檢查

用 [idea-check-action](https://github.com/mnemox-ai/idea-check-action) 驗證功能提案：

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

## 可選設定

```bash
export GITHUB_TOKEN=ghp_...        # 提升 GitHub API 速率限制
export PRODUCTHUNT_TOKEN=your_...  # 啟用 Product Hunt（deep mode）
```

**自動觸發：** 加一行到你的 `CLAUDE.md`、`.cursorrules` 或 `.github/copilot-instructions.md`：

```
開始新專案時，用 idea_check MCP tool 檢查是否已有類似專案存在。
```

## Roadmap

- [x] **v0.1** — GitHub + HN 搜尋，基本評分
- [x] **v0.2** — Deep mode（npm、PyPI、Product Hunt），關鍵字萃取
- [x] **v0.3** — 三段式關鍵字 Pipeline，中文支援，LLM 搜尋智能
- [x] **v0.4** — Score History、Agent Templates、GitHub Action
- [x] **v0.5** — 時序信號、趨勢偵測、市場動量
- [ ] **v1.0** — Idea Memory Dataset（匿名使用紀錄）

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=mnemox-ai/idea-reality-mcp&type=Date)](https://star-history.com/#mnemox-ai/idea-reality-mcp&Date)

## 結果不準？

1. [開一個 Issue](https://github.com/mnemox-ai/idea-reality-mcp/issues/new?template=inaccurate-result.yml)，附上你的 idea text 和輸出
2. 我們會改進該領域的關鍵字萃取

## 授權

MIT — 見 [LICENSE](LICENSE)

由 [Mnemox AI](https://mnemox.ai) 打造 · [dev@mnemox.ai](mailto:dev@mnemox.ai)
