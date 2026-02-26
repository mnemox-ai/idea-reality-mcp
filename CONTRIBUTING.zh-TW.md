[English](CONTRIBUTING.md) | 繁體中文

# 貢獻指南

感謝你對 idea-reality-mcp 的興趣。

## 開始

```bash
git clone https://github.com/mnemox-ai/idea-reality-mcp.git
cd idea-reality-mcp
uv sync --dev
```

## 執行測試

```bash
uv run pytest
```

## 開發流程

1. Fork 此 repo，從 `main` 建立新 branch。
2. 進行修改。
3. 視需要新增或更新測試。
4. 執行 `uv run pytest` 確認所有測試通過。
5. 開一個 pull request，附上清楚的描述。

## 程式風格

- 遵循 codebase 中既有的 pattern。
- 使用 type hints。
- 保持函式精簡、職責單一。

## 新增資料來源

1. 在 `src/idea_reality_mcp/sources/` 建立新檔案。
2. 實作一個回傳 dataclass 結果的 async function。
3. 整合進 `scoring/engine.py`。
4. 在 `tests/` 新增對應測試。

## 回報 Bug

在 GitHub 開一個 issue，附上：
- 重現步驟
- 預期 vs 實際行為
- Python 版本和作業系統

## 授權

貢獻的程式碼將以 MIT License 授權。
