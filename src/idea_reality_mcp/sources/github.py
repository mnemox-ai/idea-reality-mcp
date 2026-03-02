"""GitHub Search API source."""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

GITHUB_API = "https://api.github.com/search/repositories"


@dataclass
class GitHubResults:
    """Aggregated GitHub search results across keyword variants."""

    total_repo_count: int
    max_stars: int
    top_repos: list[dict]


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def search_github_repos(keywords: list[str]) -> GitHubResults:
    """Search GitHub for repositories matching keyword variants.

    Args:
        keywords: List of search query strings (typically 3 variants).

    Returns:
        Aggregated results with total count, max stars, and top 5 repos.
    """
    total_count = 0
    max_stars = 0
    all_repos: list[dict] = []

    # Track how many queries each repo matched (relevance signal)
    repo_query_hits: dict[str, int] = {}

    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in keywords:
            try:
                resp = await client.get(
                    GITHUB_API,
                    params={"q": query, "sort": "stars", "order": "desc", "per_page": 5},
                    headers=_headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                total_count += data.get("total_count", 0)

                for item in data.get("items", []):
                    name = item.get("full_name", "")
                    if not name:
                        continue
                    stars = item.get("stargazers_count", 0)
                    if stars > max_stars:
                        max_stars = stars
                    repo_query_hits[name] = repo_query_hits.get(name, 0) + 1
                    all_repos.append({
                        "name": name,
                        "url": item.get("html_url", ""),
                        "stars": stars,
                        "updated": item.get("updated_at", ""),
                        "description": (item.get("description") or "")[:200],
                    })
            except httpx.HTTPError:
                continue

    # Deduplicate by name and sort by relevance (query hits) then stars.
    # Repos matching multiple query variants are more likely to be relevant.
    seen = set()
    unique_repos = []
    for repo in sorted(
        all_repos,
        key=lambda r: (repo_query_hits.get(r["name"], 0), r["stars"]),
        reverse=True,
    ):
        if repo["name"] not in seen:
            seen.add(repo["name"])
            unique_repos.append(repo)

    return GitHubResults(
        total_repo_count=total_count,
        max_stars=max_stars,
        top_repos=unique_repos[:5],
    )
