"""LLM-powered idea expansion — MCP client side.

Calls the Render API ``/api/expand-idea`` to get a structured expansion of the
user's idea (description, core concept, differentiator, target user, category).
Falls back to *None* on **any** failure (timeout, rate-limit, server error, bad
JSON, missing keys) so the caller can proceed without expansion data.
"""

from __future__ import annotations

import json
import os

import httpx

_DEFAULT_API_URL = "https://idea-reality-mcp.onrender.com"
_TIMEOUT_SECONDS = 5.0

_REQUIRED_KEYS = frozenset({
    "expanded_description",
    "core_concept",
    "differentiator",
    "target_user",
    "category",
})


async def expand_idea(idea_text: str) -> dict | None:
    """Ask the Render API to expand an idea into structured fields.

    Returns:
        A dict with keys: expanded_description, core_concept, differentiator,
        target_user, category.  Or *None* if the request fails for any reason
        (timeout, 429, 5xx, invalid response, missing keys, etc.).
    """
    api_url = os.environ.get("IDEA_REALITY_API_URL", _DEFAULT_API_URL)
    url = f"{api_url}/api/expand-idea"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json={"idea_text": idea_text})

        if resp.status_code != 200:
            return None

        data = resp.json()

        if not isinstance(data, dict):
            return None

        if not _REQUIRED_KEYS.issubset(data.keys()):
            return None

        return data

    except (httpx.HTTPError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None


def generate_platform_queries(
    expansion: dict | None,
    base_keywords: list[str],
) -> dict[str, list[str]]:
    """Generate platform-specific search queries from an expansion dict.

    If *expansion* is None, returns an empty dict so the caller falls back to
    the default keyword pipeline.
    """
    if expansion is None:
        return {}

    core = expansion.get("core_concept", "").strip()
    diff = expansion.get("differentiator", "").strip()
    target = expansion.get("target_user", "").strip()
    category = expansion.get("category", "").strip()

    if not core:
        return {}

    # --- GitHub: 2-3 technical queries combining core + differentiator ---
    github = [core]
    if diff:
        github.append(f"{core} {diff}")
    if category:
        github.append(f"{category} {core}")
    github = github[:3]

    # --- npm / PyPI: lowercase-hyphen package-name style ---
    slug = "-".join(core.lower().split()[:3])
    npm = [slug]
    pypi = [slug]
    if diff:
        diff_slug = "-".join(diff.lower().split()[:2])
        npm.append(f"{slug}-{diff_slug}")
        pypi.append(f"{slug}-{diff_slug}")

    # --- Hacker News: natural language 4-8 words ---
    hn_parts = [core]
    if target:
        hn_parts.append(f"for {target}")
    hackernews = [" ".join(hn_parts)[:80]]
    if diff:
        hackernews.append(f"{core} {diff}"[:80])

    # --- Product Hunt / Stack Overflow: product-name style 2-4 words ---
    ph_name = " ".join(core.split()[:4])
    producthunt = [ph_name]
    if diff:
        producthunt.append(f"{ph_name} {' '.join(diff.split()[:2])}")

    so_name = " ".join(core.split()[:4])
    stackoverflow = [so_name]
    if category:
        stackoverflow.append(f"{category} {so_name}")

    return {
        "github": github,
        "npm": npm,
        "pypi": pypi,
        "hackernews": hackernews,
        "producthunt": producthunt,
        "stackoverflow": stackoverflow,
    }
