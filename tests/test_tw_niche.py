"""Test niche/deep domain Chinese inputs through extract_keywords().

Run: uv run python tests/test_tw_niche.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

from idea_reality_mcp.scoring.engine import extract_keywords

TEST_CASES = [
    # --- Aerospace / Space ---
    ("Aerospace", "航天衛星數據分析平台"),
    ("Aerospace", "太空軌道模擬器"),
    ("Aerospace", "火箭發射排程系統"),
    ("Aerospace", "衛星影像辨識工具"),

    # --- Religion ---
    ("Religion", "佛經翻譯工具"),
    ("Religion", "佛教冥想引導APP"),
    ("Religion", "天主教教堂活動管理系統"),
    ("Religion", "聖經經文搜尋引擎"),
    ("Religion", "宗教課程線上學習平台"),

    # --- Physics / Chemistry ---
    ("Physics", "物理實驗模擬器"),
    ("Physics", "量子運算模擬工具"),
    ("Physics", "化學分子結構視覺化"),
    ("Chemistry", "化學方程式平衡計算器"),
    ("Chemistry", "元素週期表互動教學APP"),

    # --- Medical / TCM / Acupuncture ---
    ("Medical", "中醫藥材辨識APP"),
    ("Medical", "針灸穴位查詢工具"),
    ("Medical", "西醫處方箋管理系統"),
    ("Medical", "病歷電子化管理"),
    ("Medical", "掛號預約系統"),
    ("Medical", "中藥配方推薦引擎"),

    # --- Agriculture / Environment ---
    ("Agriculture", "農業灌溉自動化系統"),
    ("Agriculture", "智慧農場感測器監控"),
    ("Agriculture", "農產品溯源追蹤"),
    ("Environment", "碳排放追蹤 dashboard"),
    ("Environment", "空氣品質監測工具"),

    # --- Legal ---
    ("Legal", "法律文件自動生成"),
    ("Legal", "合約審閱AI助手"),
    ("Legal", "判決書搜尋引擎"),
    ("Legal", "律師事務所案件管理"),

    # --- Education ---
    ("Education", "國小數學練習APP"),
    ("Education", "線上考試出題系統"),
    ("Education", "學生成績分析 dashboard"),
    ("Education", "家教媒合平台"),

    # --- Real Estate / Property ---
    ("RealEstate", "租屋比價平台"),
    ("RealEstate", "房屋裝修進度追蹤"),
    ("RealEstate", "社區管理費繳費系統"),

    # --- Music / Art ---
    ("Art", "樂譜辨識轉MIDI"),
    ("Art", "AI作曲工具"),
    ("Art", "畫作風格轉換APP"),
    ("Art", "書法練習APP"),

    # --- Pet / Animal ---
    ("Pet", "寵物健康追蹤APP"),
    ("Pet", "動物收容所管理系統"),
    ("Pet", "寵物飼料配方計算器"),

    # --- Gaming ---
    ("Gaming", "遊戲外掛偵測工具"),
    ("Gaming", "手遊課金追蹤"),
    ("Gaming", "電競戰隊排程管理"),

    # --- Government / Public ---
    ("Gov", "市政報修APP"),
    ("Gov", "選舉民調分析"),
    ("Gov", "公文自動分類系統"),

    # --- Manufacturing / IoT ---
    ("Manufacturing", "工廠設備維護排程"),
    ("Manufacturing", "IoT 感測器數據收集"),
    ("Manufacturing", "產線品質檢測AI"),
    ("Manufacturing", "供應鏈管理 dashboard"),
]

def main():
    print("=" * 90)
    print("  idea-reality-mcp v0.3 -- Niche Domain Chinese Input Test")
    print("=" * 90)

    issues = []
    categories = {}

    for category, idea in TEST_CASES:
        kws = extract_keywords(idea)
        has_chinese = any(any('\u4e00' <= c <= '\u9fff' for c in kw) for kw in kws)
        all_same = len(set(kws)) == 1
        unique_ratio = len(set(kws)) / len(kws)

        status = "OK"
        if has_chinese:
            status = "[!] Chinese leaked"
            issues.append((category, idea, "Chinese chars in output"))
        elif all_same:
            status = "[!] All identical"
            issues.append((category, idea, "All queries identical"))
        elif unique_ratio < 0.5:
            status = "[~] Low variety"

        if category not in categories:
            categories[category] = {"total": 0, "ok": 0, "issues": 0}
        categories[category]["total"] += 1
        if status == "OK" or status.startswith("[~]"):
            categories[category]["ok"] += 1
        else:
            categories[category]["issues"] += 1

        print(f"\n[{category}] {idea}")
        print(f"  Status: {status}")
        for i, kw in enumerate(kws):
            print(f"    Q{i+1}: {kw}")

    print("\n" + "=" * 90)
    print(f"Total tested: {len(TEST_CASES)}")
    print(f"Issues: {len(issues)}")

    print("\n--- By Category ---")
    for cat, stats in categories.items():
        marker = "OK" if stats["issues"] == 0 else f"{stats['issues']} issues"
        print(f"  {cat:15s}: {stats['total']} tested, {marker}")

    if issues:
        print("\n--- Issues Detail ---")
        for cat, idea, problem in issues:
            print(f"  [{cat}] {idea} -> {problem}")

    # Show unmapped Chinese chars analysis
    print("\n--- Unmapped Chinese Terms (leaked or lost) ---")
    from idea_reality_mcp.scoring.engine import CHINESE_TECH_MAP
    all_mapped = set(CHINESE_TECH_MAP.keys())
    unmapped_chars = set()
    for _, idea in TEST_CASES:
        for char in idea:
            if '\u4e00' <= char <= '\u9fff' and char not in ''.join(all_mapped):
                unmapped_chars.add(char)
    # Show as sorted list
    if unmapped_chars:
        print(f"  {len(unmapped_chars)} unique unmapped Chinese chars found")
        # Group common ones
        print(f"  Sample: {''.join(sorted(unmapped_chars)[:50])}")

    print("=" * 90)


if __name__ == "__main__":
    main()
