# 10 Ideas Scan Results — DEV.to Article Data

Scanned 2026-03-01 via mnemox.ai/check (Deep mode, English)

## Summary Table

| # | Idea | Signal | GitHub Repos | HN Posts | npm Pkgs | Top Stars | Top Competitor |
|---|------|--------|-------------|----------|----------|-----------|---------------|
| 1 | AI-powered code review automation tool | **74** 🔴 | 6,851 | 78 | 1,588,003 | 14,402 | analysis-tools-dev/static-analysis |
| 2 | open source feature flag service | **74** 🔴 | 971 | 18 | 159,304 | 1,168 | (scroll needed) |
| 3 | AI chatbot customer support open source | **74** 🔴 | 7,358 | 33 | 385,376 | 25,165 | (scroll needed) |
| 4 | markdown note taking app AI search | **74** 🔴 | 1,075 | 42 | 1,935,579 | 63,332 | (scroll needed) |
| 5 | LLM API gateway proxy router | **74** 🔴 | 1,018 | 38 | 533,792 | 37,284 | BerriAI/litellm |
| 6 | AI agent memory layer persistent context | **31** 🟢 | 711 | 23 | 274,681 | 27,216 | ComposioHQ/composio |
| 7 | MCP server database query natural language | **30** 🟢 | 5,748 | 65 | 359,245 | 14,498 | Canner/WrenAI |
| 8 | AI changelog generator git commits | **31** 🟢 | 756 | 3 | 118,343 | 23,368 | conventional-changelog/standard-version |
| 9 | MCP server CI CD pipeline debugging | **31** 🟢 | 3,152 | 53 | 285,689 | 8,251 | mark3labs/mcp-go |
| 10 | bluetooth pet collar firmware ESP32 | **33** 🟢 | 204 | 0 | 2,804 | 1,720 | OMOTE-Community/OMOTE-Firmware |

## Observations

### Signal 分布
- **#1-5 全部 74** — "Dead on arrival" 區，AI/developer tools 全紅
- **#6-10 全部 30-33** — 意外低，包含 niche MCP 方向和硬體

### 文章三個亮點截圖建議
1. **#5 LLM API gateway** — Signal 74, top competitor litellm 37K stars, 超擁擠
2. **#10 bluetooth pet collar** — Signal 33, HN 0 posts, 最 niche
3. **#7 MCP server database** — Signal 30, 但 GitHub 5,748 repos = 有東西但分散

### 分類（for article）
- 🔴 **Don't bother**: #1 code review, #2 feature flags, #3 chatbot, #4 notes, #5 LLM gateway
- 🟢 **Build it (maybe)**: #6 agent memory, #7 MCP+DB, #8 changelog, #9 MCP+CI/CD, #10 pet collar

### Bug 發現
- Signal 30-33 時 badge 仍顯示 "HIGH" — 應該是 "LOW" 或 "MODERATE"
- 可能是 UI 沒根據 signal level 更新 badge class 的問題

## Screenshots
所有截圖都在 Claude Code conversation 中可見（每個 idea 一張 gauge+evidence）
