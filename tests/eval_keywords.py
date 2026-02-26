"""Keyword extraction evaluation script — v0.3 golden set.

Measures 4 metrics against a fixed set of test ideas:
  1. Anchor hit rate   — queries contain at least 1 intent anchor
  2. Junk ratio        — boilerplate words in output queries
  3. Query diversity   — Jaccard similarity between queries (want < 0.5 avg)
  4. Must-not-appear   — boilerplate words that must NOT appear

Usage:
    python tests/eval_keywords.py
    python tests/eval_keywords.py --golden tests/golden_ideas.json
    python tests/eval_keywords.py --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from idea_reality_mcp.scoring.engine import GENERIC_WORDS, extract_keywords
from idea_reality_mcp.scoring.synonyms import INTENT_ANCHORS

# Words that should not dominate search queries
JUNK_WORDS = GENERIC_WORDS | {
    "ai", "tool", "platform", "system", "solution", "app", "service",
    "engine", "framework", "library", "helper", "manager", "builder",
    "generator", "powered", "based", "driven", "enabled", "smart",
    "intelligent", "automatic", "automated", "simple", "easy",
}


def jaccard(a: str, b: str) -> float:
    """Jaccard similarity between two query strings (word-level)."""
    sa, sb = set(a.split()), set(b.split())
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / len(sa | sb)


def avg_pairwise_jaccard(queries: list[str]) -> float:
    """Average pairwise Jaccard similarity across all query pairs."""
    if len(queries) < 2:
        return 0.0
    pairs = [
        jaccard(queries[i], queries[j])
        for i in range(len(queries))
        for j in range(i + 1, len(queries))
    ]
    return sum(pairs) / len(pairs)


def eval_one(idea: dict, verbose: bool = False) -> dict:
    """Evaluate a single idea. Returns per-idea metric dict."""
    text = idea["idea"]
    expected_anchors = idea.get("expected_anchors", [])
    must_not = set(idea.get("must_not_appear", []))

    queries = extract_keywords(text)
    all_words = set(" ".join(queries).split())

    # Metric 1: anchor hit — at least 1 expected anchor appears in queries
    anchor_hit = any(a in " ".join(queries) for a in expected_anchors) if expected_anchors else True

    # Metric 2: junk words in queries
    junk_found = all_words & JUNK_WORDS
    junk_ratio = len(junk_found) / max(len(all_words), 1)

    # Metric 3: query diversity (lower pairwise Jaccard = more diverse)
    diversity = 1.0 - avg_pairwise_jaccard(queries)  # 1.0 = fully diverse

    # Metric 4: must-not-appear violations
    violations = must_not & all_words

    if verbose:
        print(f"\n{'─'*60}")
        print(f"Idea:    {text}")
        print(f"Queries: {queries}")
        print(f"Anchors expected: {expected_anchors} → hit={anchor_hit}")
        if junk_found:
            print(f"Junk words found: {sorted(junk_found)}")
        if violations:
            print(f"VIOLATIONS (must-not-appear): {sorted(violations)}")
        print(f"Diversity score: {diversity:.2f}")

    return {
        "idea": text,
        "anchor_hit": anchor_hit,
        "junk_ratio": junk_ratio,
        "diversity": diversity,
        "violations": sorted(violations),
        "queries": queries,
    }


def run_eval(golden_path: str, verbose: bool = False) -> None:
    """Run full evaluation and print summary."""
    with open(golden_path, encoding="utf-8") as f:
        ideas = json.load(f)

    results = [eval_one(idea, verbose=verbose) for idea in ideas]
    n = len(results)

    anchor_hit_rate = sum(r["anchor_hit"] for r in results) / n
    avg_junk = sum(r["junk_ratio"] for r in results) / n
    avg_diversity = sum(r["diversity"] for r in results) / n
    violation_count = sum(1 for r in results if r["violations"])

    print("\n" + "=" * 60)
    print(f"KEYWORD EXTRACTION EVAL — {n} ideas")
    print("=" * 60)
    print(f"Anchor hit rate:   {anchor_hit_rate:.0%}  (target: ↑)")
    print(f"Avg junk ratio:    {avg_junk:.0%}  (target: ↓)")
    print(f"Query diversity:   {avg_diversity:.2f}  (target: ↑, 1.0=max)")
    print(f"Must-not-appear violations: {violation_count}/{n} ideas")

    # Print ideas that failed
    failures = [r for r in results if not r["anchor_hit"] or r["violations"]]
    if failures:
        print(f"\n[!] Failed ideas ({len(failures)}):")
        for r in failures:
            print(f"  - {r['idea'][:60]}")
            if not r["anchor_hit"]:
                print("    -> anchor not found")
            if r["violations"]:
                print(f"    -> violations: {r['violations']}")

    print("\n" + "=" * 60)

    # Exit code: 0 if all anchor hits pass, 1 otherwise
    if anchor_hit_rate < 0.7:
        print("RESULT: FAIL - anchor hit rate below 70%")
        sys.exit(1)
    else:
        print("RESULT: PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate keyword extraction quality")
    parser.add_argument(
        "--golden",
        default=str(Path(__file__).parent / "golden_ideas.json"),
        help="Path to golden ideas JSON",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    run_eval(args.golden, verbose=args.verbose)
