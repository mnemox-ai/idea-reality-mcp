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
from .scoring.engine import compute_signal, extract_keywords


@mcp.tool()
async def idea_check(
    idea_text: str,
    depth: Literal["quick", "deep"] = "quick",
) -> dict:
    """Check market reality for an idea before building it.

    Args:
        idea_text: Natural-language description of the idea.
        depth: "quick" (GitHub + HN, fast) or "deep" (all sources in parallel).

    Returns:
        Reality check report with signal score, evidence, similar projects, and pivot hints.
    """
    keywords = extract_keywords(idea_text)

    if depth == "deep":
        # Deep mode: query all sources in parallel
        github_task = search_github_repos(keywords)
        hn_task = search_hn(keywords)
        npm_task = search_npm(keywords)
        pypi_task = search_pypi(keywords)
        ph_task = search_producthunt(keywords)

        github_results, hn_results, npm_results, pypi_results, ph_results = (
            await asyncio.gather(
                github_task, hn_task, npm_task, pypi_task, ph_task,
            )
        )

        return compute_signal(
            idea_text=idea_text,
            keywords=keywords,
            github_results=github_results,
            hn_results=hn_results,
            depth=depth,
            npm_results=npm_results,
            pypi_results=pypi_results,
            ph_results=ph_results,
        )
    else:
        # Quick mode: GitHub + HN only
        github_results = await search_github_repos(keywords)
        hn_results = await search_hn(keywords)

        return compute_signal(
            idea_text=idea_text,
            keywords=keywords,
            github_results=github_results,
            hn_results=hn_results,
            depth=depth,
        )
