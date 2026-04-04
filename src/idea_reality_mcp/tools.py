"""idea_check tool — the core MCP tool."""

from __future__ import annotations

import asyncio
from typing import Literal

from .server import mcp
from .sources.github import search_github_repos
from .sources.hn import search_hn
from .sources.npm import search_npm
from .sources.pypi import search_pypi
from .sources.producthunt import search_producthunt
from .sources.stackoverflow import search_stackoverflow
from .scoring.engine import compute_signal, extract_keywords
from .scoring.expansion import expand_idea, generate_platform_queries


@mcp.tool()
async def idea_check(
    idea_text: str,
    depth: Literal["quick", "deep"] = "quick",
    lang: Literal["en", "zh"] = "en",
) -> dict:
    """Check if a product idea already exists before building it.

    Use when users discuss new project ideas, ask about competition,
    market saturation, or whether something has been built before.

    Trigger phrases: "has anyone built", "does this exist",
    "check competition", "is this idea original",
    "有沒有人做過", "市場上有類似的嗎", "幫我查這個點子"

    Args:
        idea_text: Natural-language description of the idea.
        depth: "quick" (GitHub + HN, fast) or "deep" (all sources in parallel).

    Returns:
        Reality check report with signal score, evidence, similar projects, and pivot hints.
    """
    # Dictionary keywords are the primary search queries (short, precise, synonym-expanded).
    # LLM expansion supplements with core_concept but does NOT replace dictionary queries.
    keyword_source = "dictionary"
    expansion = None
    platform_queries: dict = {}

    # Dictionary extraction with synonym expansion (instant, always available)
    keywords = extract_keywords(idea_text)

    # Try LLM expansion — enrich keywords with core_concept, not replace
    expansion = await expand_idea(idea_text)
    if expansion is not None:
        core = expansion.get("core_concept", "")
        if core and core not in keywords:
            # Insert core_concept early for search priority, keep dict keywords
            keywords.insert(0, core)
            keywords = keywords[:8]  # respect cap
        keyword_source = "expanded"
        # Generate platform-specific queries from expansion, but merge with dict keywords
        platform_queries = generate_platform_queries(expansion, keywords)

    if depth == "deep":
        # Deep mode: query all sources in parallel
        # Use dictionary keywords for all sources (short, precise, synonym-expanded)
        github_task = search_github_repos(keywords)
        hn_task = search_hn(keywords)
        npm_task = search_npm(keywords)
        pypi_task = search_pypi(keywords)
        ph_task = search_producthunt(keywords)
        so_task = search_stackoverflow(keywords)

        github_results, hn_results, npm_results, pypi_results, ph_results, so_results = (
            await asyncio.gather(
                github_task, hn_task, npm_task, pypi_task, ph_task, so_task,
            )
        )

        result = compute_signal(
            idea_text=idea_text,
            keywords=keywords,
            github_results=github_results,
            hn_results=hn_results,
            depth=depth,
            npm_results=npm_results,
            pypi_results=pypi_results,
            ph_results=ph_results,
            so_results=so_results,
            expansion=expansion,
            lang=lang,
        )
    else:
        # Quick mode: GitHub + HN in parallel
        github_results, hn_results = await asyncio.gather(
            search_github_repos(keywords),
            search_hn(keywords),
        )

        result = compute_signal(
            idea_text=idea_text,
            keywords=keywords,
            github_results=github_results,
            hn_results=hn_results,
            depth=depth,
            expansion=expansion,
            lang=lang,
        )

    result["meta"]["keyword_source"] = keyword_source
    return result
