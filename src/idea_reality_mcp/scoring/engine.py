"""Scoring engine — synthesize reality_signal from source data."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal

from ..sources.github import GitHubResults
from ..sources.hn import HNResults

# Common English stop words for keyword extraction
STOP_WORDS = frozenset({
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "don", "now", "and", "but", "or", "if", "while", "that", "which",
    "what", "this", "these", "those", "am", "it", "its", "i", "me", "my",
    "we", "our", "you", "your", "he", "him", "his", "she", "her", "they",
    "them", "their", "who", "whom", "up", "about", "like", "want", "build",
    "make", "create", "app", "tool", "using", "use", "thing", "something",
})


def extract_keywords(idea_text: str) -> list[str]:
    """Extract 3 search query variants from idea text.

    Strategy:
    1. Full cleaned phrase (truncated to first 8 meaningful words)
    2. Top 3 keywords joined
    3. Top 2 keywords joined

    Returns:
        List of 3 query strings.
    """
    # Normalize: lowercase, keep only alphanumeric and spaces
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", idea_text.lower())
    words = [w for w in cleaned.split() if w not in STOP_WORDS and len(w) > 1]

    if not words:
        # Fallback: use the raw text
        return [idea_text.strip()[:80]] * 3

    # Variant 1: full phrase (up to 8 words)
    full_phrase = " ".join(words[:8])

    # Variant 2: top 3 keywords (by length as proxy for specificity)
    ranked = sorted(set(words), key=lambda w: (-len(w), w))
    top3 = " ".join(ranked[:3])

    # Variant 3: top 2 keywords
    top2 = " ".join(ranked[:2])

    variants = list(dict.fromkeys([full_phrase, top3, top2]))
    # Ensure exactly 3
    while len(variants) < 3:
        variants.append(variants[0])

    return variants[:3]


def _github_repo_score(count: int) -> int:
    if count == 0:
        return 0
    if count <= 10:
        return 20
    if count <= 50:
        return 40
    if count <= 200:
        return 60
    if count <= 500:
        return 75
    return 90


def _github_star_score(max_stars: int) -> int:
    if max_stars < 10:
        return 0
    if max_stars <= 100:
        return 30
    if max_stars <= 500:
        return 50
    if max_stars <= 1000:
        return 70
    return 90


def _hn_score(mentions: int) -> int:
    if mentions == 0:
        return 0
    if mentions <= 5:
        return 25
    if mentions <= 15:
        return 50
    if mentions <= 30:
        return 70
    return 90


def _duplicate_likelihood(signal: int) -> Literal["low", "medium", "high"]:
    if signal < 30:
        return "low"
    if signal <= 60:
        return "medium"
    return "high"


def _generate_pivot_hints(
    signal: int,
    github: GitHubResults,
    hn: HNResults,
    keywords: list[str],
) -> list[str]:
    """Generate 3 actionable pivot hints based on the analysis."""
    hints: list[str] = []

    if signal >= 60:
        hints.append(
            "High existing competition detected. Consider a niche differentiator "
            "or target an underserved audience segment."
        )
        if github.top_repos:
            top = github.top_repos[0]
            hints.append(
                f"The leading project ({top['name']}, {top['stars']} stars) may have gaps. "
                "Check its issues and feature requests for unmet needs."
            )
        hints.append(
            "Consider building an integration or plugin for existing tools "
            "rather than a standalone replacement."
        )
    elif signal >= 30:
        hints.append(
            "Moderate competition exists. Focus on a specific use case or workflow "
            "that current solutions handle poorly."
        )
        hints.append(
            "Validate with potential users before building — the market exists "
            "but may not need another general solution."
        )
        hints.append(
            "Look at the most recent entries for emerging trends you could lead."
        )
    else:
        hints.append(
            "Low competition — this could be a greenfield opportunity or a niche "
            "that hasn't gained traction yet."
        )
        hints.append(
            "Validate demand before investing heavily. Low competition can also "
            "mean low demand."
        )
        hints.append(
            "Search adjacent problem spaces — the idea might exist under different "
            "terminology."
        )

    return hints[:3]


def compute_signal(
    idea_text: str,
    keywords: list[str],
    github_results: GitHubResults,
    hn_results: HNResults,
    depth: str,
) -> dict:
    """Compute the full reality check output.

    Returns:
        Complete idea_check response dict.
    """
    g_repo = _github_repo_score(github_results.total_repo_count)
    g_star = _github_star_score(github_results.max_stars)
    h_score = _hn_score(hn_results.total_mentions)

    signal = int(g_repo * 0.6 + g_star * 0.2 + h_score * 0.2)
    signal = max(0, min(100, signal))

    # Build evidence
    evidence = [
        {
            "source": "github",
            "type": "repo_count",
            "query": kw,
            "count": github_results.total_repo_count,
            "detail": f"{github_results.total_repo_count} repos found across queries",
        }
        for kw in keywords[:1]
    ]
    evidence.append({
        "source": "github",
        "type": "max_stars",
        "query": keywords[0],
        "count": github_results.max_stars,
        "detail": f"Top repo has {github_results.max_stars} stars",
    })
    evidence.extend(hn_results.evidence)

    return {
        "reality_signal": signal,
        "duplicate_likelihood": _duplicate_likelihood(signal),
        "evidence": evidence,
        "top_similars": github_results.top_repos,
        "pivot_hints": _generate_pivot_hints(signal, github_results, hn_results, keywords),
        "meta": {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "sources_used": ["github", "hackernews"],
            "depth": depth,
            "version": "0.1.0",
        },
    }
