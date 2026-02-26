[English](SECURITY.md) | 繁體中文

# 安全政策

## 支援版本

| 版本 | 支援狀態 |
|------|----------|
| 0.2.x | :white_check_mark: |
| 0.1.x | :x: |

## 回報漏洞

如果你發現 idea-reality-mcp 的安全漏洞，請負責任地回報：

1. **請勿**在 GitHub 開公開 issue。
2. 寄信至 **security@mnemox.ai**，附上：
   - 漏洞描述
   - 重現步驟
   - 潛在影響
3. 你會在 48 小時內收到確認回覆。
4. 我們會與你合作，在公開揭露前理解並修復問題。

## 範圍

本專案會對以下服務發送 HTTP 請求：

- `api.github.com` — GitHub Search API
- `hn.algolia.com` — Hacker News Algolia API
- `registry.npmjs.org` — npm Registry API（deep mode）
- `pypi.org` — PyPI Registry（deep mode）
- `api.producthunt.com` — Product Hunt GraphQL API（deep mode，可選 — 僅在設定 `PRODUCTHUNT_TOKEN` 時啟用）

不會儲存或傳輸任何使用者資料至其他服務。可選的 `GITHUB_TOKEN` 和 `PRODUCTHUNT_TOKEN` 環境變數僅用於 API 認證，不會被記錄或保存。
