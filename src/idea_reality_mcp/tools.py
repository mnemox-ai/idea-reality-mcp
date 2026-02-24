"""idea_check tool — the core MCP tool."""

from __future__ import annotations

from typing import Literal

from .server import mcp
from .sources.github import search_github_repos
from .sources.hn import search_hn
from .scoring.engine import compute_signal, extract_keywords


@mcp.tool()
async def idea_check(
    idea_text: str,
    depth: Literal["quick", "deep"] = "quick",
) -> dict:
    """Check market reality for an idea before building it.

    Args:
        idea_text: Natural-language description of the idea.
        depth: "quick" (GitHub + HN) or "deep" (stub, reserved for v0.2).

    Returns:
        Reality check report with signal score, evidence, similar projects, and pivot hints.
    """
    keywords = extract_keywords(idea_text)

    deep_note = None
    if depth == "deep":
        # Stub for v0.2 — falls back to quick for now
        deep_note = "deep mode not yet available (v0.2), using quick mode"

    github_results = await search_github_repos(keywords)
    hn_results = await search_hn(keywords)

    result = compute_signal(
        idea_text=idea_text,
        keywords=keywords,
        github_results=github_results,
        hn_results=hn_results,
        depth=depth,
    )

    if deep_note:
        result["note"] = deep_note

    return result
