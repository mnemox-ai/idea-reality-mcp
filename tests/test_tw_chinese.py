"""Test Taiwanese Chinese inputs through extract_keywords() and display results.

Run: uv run python tests/test_tw_chinese.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from idea_reality_mcp.scoring.engine import extract_keywords

# Categories of Taiwanese user inputs
TEST_CASES = [
    # --- Pure Chinese (typical FB/PTT user) ---
    ("Pure ZH", "LINE Bot 自動客服系統"),
    ("Pure ZH", "電商後台管理系統"),
    ("Pure ZH", "記帳工具"),
    ("Pure ZH", "線上訂餐系統"),
    ("Pure ZH", "健身追蹤APP"),
    ("Pure ZH", "AI 聊天機器人"),
    ("Pure ZH", "排程任務管理工具"),
    ("Pure ZH", "發票自動生成與付款追蹤"),
    ("Pure ZH", "即時通知推播系統"),
    ("Pure ZH", "股票技術分析 dashboard"),
    ("Pure ZH", "向量資料庫搜尋引擎"),
    ("Pure ZH", "社群媒體排程發文工具"),
    ("Pure ZH", "幫我記帳的東西"),
    ("Pure ZH", "自動回覆LINE訊息的機器人"),
    ("Pure ZH", "知識庫管理平台"),
    ("Pure ZH", "雲端部署自動化"),
    ("Pure ZH", "網站爬蟲工具"),
    ("Pure ZH", "資料庫遷移工具"),
    ("Pure ZH", "日誌收集和分析"),
    ("Pure ZH", "客戶關係管理系統"),

    # --- Mixed Chinese + English (developer-style) ---
    ("Mixed", "LINE Bot 客服自動回覆"),
    ("Mixed", "AI 翻譯工具"),
    ("Mixed", "Python 資料分析 dashboard"),
    ("Mixed", "FastAPI 後端 API gateway"),
    ("Mixed", "LLM 評測工具"),
    ("Mixed", "MCP server 開發框架"),
    ("Mixed", "RAG 知識庫搜尋"),
    ("Mixed", "Docker 容器化部署工具"),
    ("Mixed", "Redis 快取管理"),
    ("Mixed", "GraphQL API 監控 dashboard"),
    ("Mixed", "Slack Bot 排程通知"),
    ("Mixed", "PyTorch 模型微調工具"),
    ("Mixed", "React 電商前端"),
    ("Mixed", "Kubernetes 成本分析 dashboard"),

    # --- Colloquial / natural language (non-developer user) ---
    ("Colloquial", "幫我自動發 IG 限動"),
    ("Colloquial", "可以幫我翻譯文件的東西"),
    ("Colloquial", "自動幫我整理 email"),
    ("Colloquial", "追蹤加密貨幣價格"),
    ("Colloquial", "找便宜機票的工具"),
    ("Colloquial", "讀 PDF 然後幫我摘要"),

    # --- Specific Taiwanese business scenarios ---
    ("TW Biz", "蝦皮賣家庫存管理"),
    ("TW Biz", "Uber Eats 外送訂單追蹤"),
    ("TW Biz", "台灣電子發票自動對帳"),
    ("TW Biz", "健保資料分析系統"),
    ("TW Biz", "Foodpanda 餐廳評價爬蟲"),
    ("TW Biz", "LINE Pay 金流串接"),
]

def main():
    print("=" * 90)
    print("  idea-reality-mcp v0.3 -- Taiwanese Chinese Input Test")
    print("=" * 90)

    issues = []

    for category, idea in TEST_CASES:
        kws = extract_keywords(idea)
        # Check for issues
        has_chinese = any(any('\u4e00' <= c <= '\u9fff' for c in kw) for kw in kws)
        has_raw_repeat = len(set(kws)) < len(kws) * 0.5  # over half duplicated
        all_same = len(set(kws)) == 1

        status = "OK"
        if has_chinese:
            status = "[!] Chinese in output"
            issues.append((idea, "Chinese chars leaked into keywords"))
        elif all_same:
            status = "[!] All identical"
            issues.append((idea, "All queries identical"))
        elif has_raw_repeat:
            status = "[~] High duplication"

        print(f"\n[{category}] {idea}")
        print(f"  Status: {status}")
        for i, kw in enumerate(kws):
            print(f"    Q{i+1}: {kw}")

    print("\n" + "=" * 90)
    print(f"Total tested: {len(TEST_CASES)}")
    print(f"Issues found: {len(issues)}")
    if issues:
        print("\nISSUES:")
        for idea, problem in issues:
            print(f"  - [{problem}] {idea}")
    else:
        print("All clear -- no Chinese leakage or degenerate outputs!")
    print("=" * 90)


if __name__ == "__main__":
    main()
