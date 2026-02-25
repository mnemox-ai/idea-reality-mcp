"""Scoring engine — synthesize reality_signal from source data."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal

from ..sources.github import GitHubResults
from ..sources.hn import HNResults
from ..sources.npm import NpmResults
from ..sources.pypi import PyPIResults
from ..sources.producthunt import ProductHuntResults

# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------

# Common English stop words
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
    "them", "their", "who", "whom", "up", "about", "like", "want", "get",
    "new", "also", "one", "two", "way", "many", "much", "well", "still",
    "even", "back", "any", "let", "really", "already", "every",
})

# Words too generic to be useful in searches on their own, but kept if
# they appear inside a compound term.
GENERIC_WORDS = frozenset({
    "build", "make", "create", "app", "tool", "using", "use", "thing",
    "something", "platform", "system", "service", "project", "idea",
    "solution", "product", "software", "program", "application",
})

# Compound terms that should be kept together as a single token.
COMPOUND_TERMS = [
    "machine learning", "deep learning", "natural language processing",
    "computer vision", "web app", "web application", "mobile app",
    "command line", "real time", "open source", "data science",
    "neural network", "reinforcement learning", "large language model",
    "artificial intelligence", "api gateway", "message queue",
    "task manager", "file manager", "code review", "code editor",
    "package manager", "version control", "continuous integration",
    "object detection", "image recognition", "text to speech",
    "speech to text", "time series", "knowledge graph",
    "supply chain", "social media", "e commerce", "ecommerce",
]

# Technology / framework keywords that get priority in ranking.
TECH_KEYWORDS = frozenset({
    "react", "vue", "angular", "svelte", "nextjs", "nuxt", "remix",
    "python", "javascript", "typescript", "rust", "go", "golang",
    "java", "kotlin", "swift", "ruby", "php", "elixir", "scala",
    "django", "flask", "fastapi", "express", "nestjs", "rails",
    "docker", "kubernetes", "terraform", "ansible", "aws", "gcp", "azure",
    "postgres", "postgresql", "mysql", "mongodb", "redis", "sqlite",
    "graphql", "grpc", "rest", "websocket", "mqtt",
    "tensorflow", "pytorch", "keras", "scikit", "pandas", "numpy",
    "openai", "anthropic", "langchain", "llamaindex", "ollama",
    "blockchain", "ethereum", "solana", "bitcoin",
    "electron", "tauri", "flutter", "ionic",
    "mcp", "onnx", "llm", "rag", "cli", "api", "sdk", "orm",
})


def extract_keywords(idea_text: str) -> list[str]:
    """Extract search query variants from idea text.

    Strategy:
    1. Detect and preserve compound terms.
    2. Filter stop words and generic words.
    3. Prioritise technology keywords.
    4. Return up to 4 variants optimised for different search targets.

    Returns:
        List of 3-4 query strings.
    """
    lowered = idea_text.lower().strip()

    # --- Phase 1: extract compound terms first --------------------------------
    found_compounds: list[str] = []
    remaining = lowered
    for compound in sorted(COMPOUND_TERMS, key=len, reverse=True):
        if compound in remaining:
            found_compounds.append(compound)
            remaining = remaining.replace(compound, " ")

    # --- Phase 2: tokenise the rest -------------------------------------------
    cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", remaining)
    tokens = [w for w in cleaned.split() if len(w) > 1]

    # Separate meaningful words from generic/stop
    meaningful = [w for w in tokens if w not in STOP_WORDS and w not in GENERIC_WORDS]
    tech_tokens = [w for w in meaningful if w in TECH_KEYWORDS]
    non_tech = [w for w in meaningful if w not in TECH_KEYWORDS]

    # Combine: compounds first, then tech, then others
    all_keywords = found_compounds + tech_tokens + non_tech

    if not all_keywords:
        # Fallback: use the raw text
        return [idea_text.strip()[:80]] * 3

    # --- Phase 3: build query variants ----------------------------------------
    # Variant 1: full phrase (compounds + keywords, up to 8 tokens)
    full_phrase = " ".join(all_keywords[:8])

    # Variant 2: top 3 keywords by specificity (length proxy), tech first
    ranked = tech_tokens + sorted(set(non_tech), key=lambda w: (-len(w), w))
    if found_compounds:
        ranked = [found_compounds[0]] + ranked
    top3 = " ".join(dict.fromkeys(ranked[:3]))

    # Variant 3: top 2 keywords
    top2 = " ".join(dict.fromkeys(ranked[:2]))

    # Variant 4: registry-optimised (1-2 core terms, best for npm/PyPI)
    registry_terms = tech_tokens[:2] if tech_tokens else ranked[:2]
    registry_query = " ".join(dict.fromkeys(registry_terms))

    variants = list(dict.fromkeys([full_phrase, top3, top2, registry_query]))
    # Ensure at least 3
    while len(variants) < 3:
        variants.append(variants[0])

    return variants[:4]


# ---------------------------------------------------------------------------
# Source-specific score functions
# ---------------------------------------------------------------------------

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


def _npm_score(count: int) -> int:
    """Score npm package count."""
    if count == 0:
        return 0
    if count <= 5:
        return 15
    if count <= 20:
        return 35
    if count <= 100:
        return 55
    if count <= 500:
        return 75
    return 90


def _pypi_score(count: int) -> int:
    """Score PyPI package count."""
    if count == 0:
        return 0
    if count <= 5:
        return 15
    if count <= 20:
        return 35
    if count <= 100:
        return 55
    if count <= 500:
        return 75
    return 90


def _ph_score(count: int) -> int:
    """Score Product Hunt product count."""
    if count == 0:
        return 0
    if count <= 3:
        return 20
    if count <= 10:
        return 40
    if count <= 30:
        return 60
    if count <= 100:
        return 80
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


# ---------------------------------------------------------------------------
# Signal computation
# ---------------------------------------------------------------------------

# Weight presets
_QUICK_WEIGHTS = {
    "github_repo": 0.6,
    "github_star": 0.2,
    "hn": 0.2,
}

_DEEP_WEIGHTS = {
    "github_repo": 0.25,
    "github_star": 0.10,
    "hn": 0.15,
    "npm": 0.20,
    "pypi": 0.15,
    "ph": 0.15,
}


def compute_signal(
    idea_text: str,
    keywords: list[str],
    github_results: GitHubResults,
    hn_results: HNResults,
    depth: str,
    *,
    npm_results: NpmResults | None = None,
    pypi_results: PyPIResults | None = None,
    ph_results: ProductHuntResults | None = None,
) -> dict:
    """Compute the full reality check output.

    Returns:
        Complete idea_check response dict.
    """
    g_repo = _github_repo_score(github_results.total_repo_count)
    g_star = _github_star_score(github_results.max_stars)
    h_score = _hn_score(hn_results.total_mentions)

    sources_used = ["github", "hackernews"]

    if depth == "quick" or (npm_results is None and pypi_results is None):
        # Quick mode — original weights
        signal = int(g_repo * 0.6 + g_star * 0.2 + h_score * 0.2)
    else:
        # Deep mode
        n_score = _npm_score(npm_results.total_count) if npm_results else 0
        p_score = _pypi_score(pypi_results.total_count) if pypi_results else 0

        weights = dict(_DEEP_WEIGHTS)

        if npm_results:
            sources_used.append("npm")
        if pypi_results:
            sources_used.append("pypi")

        # Product Hunt — redistribute weight if skipped/unavailable
        ph_available = ph_results is not None and not ph_results.skipped
        if ph_available:
            ph_val = _ph_score(ph_results.total_count)
            sources_used.append("producthunt")
        else:
            ph_val = 0
            # Redistribute PH weight proportionally to other deep sources
            ph_w = weights.pop("ph", 0.15)
            remaining_keys = list(weights.keys())
            total_remaining = sum(weights[k] for k in remaining_keys)
            if total_remaining > 0:
                for k in remaining_keys:
                    weights[k] += ph_w * (weights[k] / total_remaining)

        signal = int(
            g_repo * weights.get("github_repo", 0.25)
            + g_star * weights.get("github_star", 0.10)
            + h_score * weights.get("hn", 0.15)
            + n_score * weights.get("npm", 0.20)
            + p_score * weights.get("pypi", 0.15)
            + ph_val * weights.get("ph", 0)
        )

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

    if npm_results:
        evidence.extend(npm_results.evidence)
    if pypi_results:
        evidence.extend(pypi_results.evidence)
    if ph_results:
        evidence.extend(ph_results.evidence)

    # Top similars: merge GitHub repos with npm/PyPI/PH entries
    top_similars = list(github_results.top_repos)
    if npm_results:
        for pkg in npm_results.top_packages[:3]:
            top_similars.append({
                "name": f"npm:{pkg['name']}",
                "url": pkg["url"],
                "stars": 0,
                "updated": "",
                "description": pkg["description"],
            })
    if pypi_results:
        for pkg in pypi_results.top_packages[:3]:
            top_similars.append({
                "name": f"pypi:{pkg['name']}",
                "url": pkg["url"],
                "stars": 0,
                "updated": "",
                "description": pkg["description"],
            })
    if ph_results and not ph_results.skipped:
        for prod in ph_results.top_products[:3]:
            top_similars.append({
                "name": f"ph:{prod['name']}",
                "url": prod["url"],
                "stars": prod.get("votes", 0),
                "updated": prod.get("created_at", ""),
                "description": prod.get("tagline", ""),
            })

    return {
        "reality_signal": signal,
        "duplicate_likelihood": _duplicate_likelihood(signal),
        "evidence": evidence,
        "top_similars": top_similars,
        "pivot_hints": _generate_pivot_hints(signal, github_results, hn_results, keywords),
        "meta": {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "sources_used": sources_used,
            "depth": depth,
            "version": "0.2.0",
        },
    }
