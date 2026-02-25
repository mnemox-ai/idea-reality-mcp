"""Product Hunt GraphQL API source (optional).

Requires a ``PRODUCTHUNT_TOKEN`` environment variable.  When the token is not
set the search is skipped gracefully and an empty result is returned.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import httpx

PH_GRAPHQL_API = "https://api.producthunt.com/v2/api/graphql"


@dataclass
class ProductHuntResults:
    """Aggregated Product Hunt search results."""

    total_count: int = 0
    top_products: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    skipped: bool = False


def _token() -> str | None:
    return os.environ.get("PRODUCTHUNT_TOKEN")


async def search_producthunt(keywords: list[str]) -> ProductHuntResults:
    """Search Product Hunt for products matching keyword variants.

    Args:
        keywords: List of search query strings.

    Returns:
        Aggregated results.  If no token is configured the ``skipped``
        flag is set and counts are zero.
    """
    token = _token()
    if not token:
        return ProductHuntResults(
            skipped=True,
            evidence=[{
                "source": "producthunt",
                "type": "skipped",
                "query": "",
                "count": 0,
                "detail": "Product Hunt search skipped (PRODUCTHUNT_TOKEN not set)",
            }],
        )

    total_count = 0
    all_products: list[dict] = []
    evidence: list[dict] = []

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in keywords:
            graphql_query = """
            query SearchPosts($query: String!) {
                posts(order: VOTES, search: $query, first: 5) {
                    totalCount
                    edges {
                        node {
                            name
                            tagline
                            url
                            votesCount
                            createdAt
                        }
                    }
                }
            }
            """
            try:
                resp = await client.post(
                    PH_GRAPHQL_API,
                    json={"query": graphql_query, "variables": {"query": query}},
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

                posts_data = data.get("data", {}).get("posts", {})
                count = posts_data.get("totalCount", 0)
                total_count += count

                for edge in posts_data.get("edges", []):
                    node = edge.get("node", {})
                    all_products.append({
                        "name": node.get("name", ""),
                        "url": node.get("url", ""),
                        "tagline": (node.get("tagline") or "")[:200],
                        "votes": node.get("votesCount", 0),
                        "created_at": node.get("createdAt", ""),
                    })

                evidence.append({
                    "source": "producthunt",
                    "type": "product_count",
                    "query": query,
                    "count": count,
                    "detail": f"{count} Product Hunt posts found for '{query}'",
                })
            except httpx.HTTPError:
                evidence.append({
                    "source": "producthunt",
                    "type": "error",
                    "query": query,
                    "count": 0,
                    "detail": f"Failed to query Product Hunt for '{query}'",
                })

    # Deduplicate by name, keep highest votes
    seen: dict[str, dict] = {}
    for prod in all_products:
        name = prod["name"]
        if name not in seen or prod["votes"] > seen[name]["votes"]:
            seen[name] = prod
    unique = sorted(seen.values(), key=lambda p: p["votes"], reverse=True)

    return ProductHuntResults(
        total_count=total_count,
        top_products=unique[:5],
        evidence=evidence,
    )
