[English](sample_prompts.md) | 繁體中文

# idea_check 範例提示

## 基本用法

```
在開始之前，幫我查一下這個點子有沒有人做過：
一個自動把 Figma 設計稿轉成 React 元件的 CLI 工具
```

```
idea_check: 一個 AI 驅動的 GitHub PR code review bot，能自動建議修正
```

```
幫我查市場現實：即時協作的 Markdown 編輯器加上 AI 自動完成功能
```

## 指定查詢深度

```
快速查一下：Kubernetes 成本最佳化儀表板，加上 AI 建議功能
```

```
idea_check("LINE Bot 自動客服系統", depth="deep")
```

## 解讀結果

- **reality_signal 0–29**：藍海 — 現有競爭很少。建議驗證市場需求。
- **reality_signal 30–60**：中度競爭 — 需要差異化或找到利基市場。
- **reality_signal 61–100**：紅海 — 考慮轉向、專精化，或做成既有工具的整合外掛。

查看 `top_similars` 了解已存在的專案，查看 `pivot_hints` 取得可執行的下一步建議。
