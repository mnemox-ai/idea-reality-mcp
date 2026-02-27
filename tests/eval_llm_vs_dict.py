"""v0.4 Evaluation: LLM (Haiku 4.5) vs Dictionary keyword extraction.

Usage:
    ANTHROPIC_API_KEY=sk-... uv run python tests/eval_llm_vs_dict.py

Outputs: docs/v0.4-comparison.md
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from idea_reality_mcp.scoring.engine import extract_keywords, INTENT_ANCHORS, GENERIC_WORDS, STOP_WORDS
from api.main import _extract_keywords_via_haiku, _HAIKU_SYSTEM_PROMPT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_anchor(keywords: list[str], expected: list[str]) -> bool:
    """Check if any expected anchor appears in any keyword string."""
    if not expected:
        return True  # no anchors expected = pass
    text = " ".join(keywords).lower()
    return any(a.lower() in text for a in expected)


def _junk_ratio(keywords: list[str]) -> float:
    """Fraction of tokens that are stop words or generic words."""
    all_tokens = []
    for kw in keywords:
        all_tokens.extend(kw.lower().split())
    if not all_tokens:
        return 0.0
    junk = [t for t in all_tokens if t in STOP_WORDS or t in GENERIC_WORDS]
    return len(junk) / len(all_tokens)


def _is_chinese_idea(idea: str) -> bool:
    """Check if idea contains Chinese characters."""
    return any('\u4e00' <= ch <= '\u9fff' for ch in idea)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main():
    golden_path = Path(__file__).parent / "golden_ideas.json"
    raw = json.loads(golden_path.read_text(encoding="utf-8"))
    ideas = [item for item in raw if "idea" in item]

    print(f"Loaded {len(ideas)} golden ideas")
    print(f"ANTHROPIC_API_KEY present: {bool(os.environ.get('ANTHROPIC_API_KEY'))}")
    print()

    results = []
    llm_failures = 0

    for i, item in enumerate(ideas):
        idea = item["idea"]
        expected_anchors = item.get("expected_anchors", [])

        # Dictionary
        dict_kw = extract_keywords(idea)

        # LLM (with small delay to avoid rate limits)
        if i > 0:
            await asyncio.sleep(0.3)
        llm_kw = await _extract_keywords_via_haiku(idea)
        if llm_kw is None:
            llm_failures += 1
            llm_kw = []

        results.append({
            "idea": idea,
            "expected_anchors": expected_anchors,
            "dict_kw": dict_kw,
            "llm_kw": llm_kw,
            "is_chinese": _is_chinese_idea(idea),
            "dict_anchor_hit": _has_anchor(dict_kw, expected_anchors),
            "llm_anchor_hit": _has_anchor(llm_kw, expected_anchors) if llm_kw else False,
            "dict_junk": _junk_ratio(dict_kw),
            "llm_junk": _junk_ratio(llm_kw) if llm_kw else 0.0,
        })

        status = "OK" if llm_kw else "FAIL"
        print(f"  [{i+1:2d}/{len(ideas)}] {status} | {idea[:60]}")

    # ---------------------------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------------------------
    total = len(results)
    valid_llm = [r for r in results if r["llm_kw"]]
    chinese = [r for r in results if r["is_chinese"]]

    dict_avg_count = sum(len(r["dict_kw"]) for r in results) / total
    llm_avg_count = sum(len(r["llm_kw"]) for r in valid_llm) / len(valid_llm) if valid_llm else 0

    dict_anchor_hits = sum(1 for r in results if r["dict_anchor_hit"])
    llm_anchor_hits = sum(1 for r in results if r["llm_anchor_hit"])

    dict_avg_junk = sum(r["dict_junk"] for r in results) / total
    llm_avg_junk = sum(r["llm_junk"] for r in valid_llm) / len(valid_llm) if valid_llm else 0

    # Cases where dictionary missed but LLM caught
    dict_miss_llm_hit = [
        r for r in results
        if not r["dict_anchor_hit"] and r["llm_anchor_hit"]
    ]

    # Cases where LLM missed but dictionary caught
    llm_miss_dict_hit = [
        r for r in results
        if r["dict_anchor_hit"] and not r["llm_anchor_hit"]
    ]

    # ---------------------------------------------------------------------------
    # Generate markdown report
    # ---------------------------------------------------------------------------
    lines = []
    lines.append("# v0.4 Keyword Extraction Comparison: LLM vs Dictionary")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"Golden set: {total} ideas ({len(chinese)} Chinese, {total - len(chinese)} English)")
    lines.append(f"LLM: Claude Haiku 4.5 | Dictionary: 3-stage pipeline (v0.3.1)")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Dictionary | LLM (Haiku 4.5) |")
    lines.append("|--------|-----------|-----------------|")
    lines.append(f"| Avg keyword count | {dict_avg_count:.1f} | {llm_avg_count:.1f} |")
    lines.append(f"| Anchor hit rate | {dict_anchor_hits}/{total} ({dict_anchor_hits/total*100:.0f}%) | {llm_anchor_hits}/{total} ({llm_anchor_hits/total*100:.0f}%) |")
    lines.append(f"| Avg junk ratio | {dict_avg_junk*100:.1f}% | {llm_avg_junk*100:.1f}% |")
    lines.append(f"| LLM call failures | — | {llm_failures}/{total} |")
    lines.append(f"| Dict miss, LLM hit | {len(dict_miss_llm_hit)} cases | — |")
    lines.append(f"| LLM miss, Dict hit | — | {len(llm_miss_dict_hit)} cases |")
    lines.append("")

    # Full comparison table
    lines.append("## Full Comparison")
    lines.append("")
    lines.append("| # | Idea | Dict Keywords | LLM Keywords | Dict Anchor | LLM Anchor |")
    lines.append("|---|------|---------------|--------------|-------------|------------|")

    for i, r in enumerate(results):
        idea_short = r["idea"][:45] + ("..." if len(r["idea"]) > 45 else "")
        dict_str = " | ".join(r["dict_kw"][:3])
        if len(r["dict_kw"]) > 3:
            dict_str += f" (+{len(r['dict_kw'])-3})"
        llm_str = " | ".join(r["llm_kw"][:3]) if r["llm_kw"] else "*(failed)*"
        if len(r["llm_kw"]) > 3:
            llm_str += f" (+{len(r['llm_kw'])-3})"
        d_anchor = "hit" if r["dict_anchor_hit"] else "**MISS**"
        l_anchor = "hit" if r["llm_anchor_hit"] else "**MISS**"
        lines.append(f"| {i+1} | {idea_short} | {dict_str} | {llm_str} | {d_anchor} | {l_anchor} |")

    lines.append("")

    # Dict miss, LLM hit section
    if dict_miss_llm_hit:
        lines.append("## Dictionary Missed, LLM Caught")
        lines.append("")
        for r in dict_miss_llm_hit:
            lines.append(f"- **{r['idea']}**")
            lines.append(f"  - Expected: `{r['expected_anchors']}`")
            lines.append(f"  - Dict: `{r['dict_kw'][:3]}`")
            lines.append(f"  - LLM: `{r['llm_kw'][:3]}`")
        lines.append("")

    # LLM miss, Dict hit section
    if llm_miss_dict_hit:
        lines.append("## LLM Missed, Dictionary Caught")
        lines.append("")
        for r in llm_miss_dict_hit:
            lines.append(f"- **{r['idea']}**")
            lines.append(f"  - Expected: `{r['expected_anchors']}`")
            lines.append(f"  - Dict: `{r['dict_kw'][:3]}`")
            lines.append(f"  - LLM: `{r['llm_kw'][:3]}`")
        lines.append("")

    # Chinese idea quality
    lines.append("## Chinese Idea Quality (10 samples)")
    lines.append("")
    lines.append("| Idea (ZH) | Dict Keywords | LLM Keywords | Verdict |")
    lines.append("|-----------|--------------|--------------|---------|")
    for r in chinese[:10]:
        dict_str = ", ".join(r["dict_kw"][:3])
        llm_str = ", ".join(r["llm_kw"][:3]) if r["llm_kw"] else "*(failed)*"
        # Auto-verdict based on anchor hit + junk
        if r["llm_kw"] and r["llm_anchor_hit"] and r["llm_junk"] <= r["dict_junk"]:
            verdict = "LLM better"
        elif r["dict_anchor_hit"] and not r["llm_anchor_hit"]:
            verdict = "Dict better"
        elif r["llm_kw"] and r["llm_anchor_hit"] and r["dict_anchor_hit"]:
            verdict = "Tie"
        else:
            verdict = "Dict better" if r["dict_anchor_hit"] else "Both miss"
        lines.append(f"| {r['idea'][:35]} | {dict_str} | {llm_str} | {verdict} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*This comparison is auto-generated. LLM results may vary between runs.*")

    # Write
    docs_dir = Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)
    out_path = docs_dir / "v0.4-comparison.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to: {out_path}")
    print(f"Total: {total} ideas | LLM failures: {llm_failures}")
    print(f"Dict anchor: {dict_anchor_hits}/{total} | LLM anchor: {llm_anchor_hits}/{total}")


if __name__ == "__main__":
    asyncio.run(main())
