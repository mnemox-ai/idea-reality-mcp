"""Product Hunt source — PERMANENTLY DISABLED. Do not re-enable with a token.

Product Hunt's API cannot do what this source claims to do, and it never could.
Verified against the live API on 2026-07-17:

    Field 'posts' doesn't accept argument 'search'

The query below asks for ``posts(search: $query)``. That argument does not exist.
Schema introspection confirms the full arg list on ``posts``::

    posts(featured, postedBefore, postedAfter, topic, order, twitterUrl, url,
          after, before, first, last)

There is no text search on posts, at all. The only searchable field in the whole v2
schema is ``topics(query:)``, which is useless here: 'mcp' and 'startup idea checker'
return nothing, while 'artificial intelligence' returns a 107k-post category. Neither
answers "has someone already built THIS idea", which is the only question this source
exists to answer.

WHY THIS IS HARD-DISABLED RATHER THAN JUST LEFT UNCONFIGURED:

Until today the missing token was hiding the broken query — ``if not token: return
skipped`` returned before the call could fail, so nobody ever saw the error. Setting
the token does not fix the source; it makes it *lie*. The GraphQL call fails, the
exception is swallowed, ``total_count`` stays 0, and ``skipped`` is False — so
scoring/engine.py:705 treats it as a live source reporting **zero competitors on
Product Hunt** and feeds that into 14% of the deep-mode score. Every idea then looks
more original than it is, silently, with no error anywhere.

That is exactly what happened on prod for ~1 hour on 2026-07-17 when the token was set
during this investigation. Returning skipped=True unconditionally is what keeps
engine.py redistributing the 14% to sources that actually answer.

To bring Product Hunt back you need a real search surface (their site search is not in
the API), not a token. Until then this returns skipped and the docs must not claim it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import httpx

PH_GRAPHQL_API = "https://api.producthunt.com/v2/api/graphql"


@dataclass
class ProductHuntResults:
    """Aggregated Product Hunt search results."""

    total_count: int = 0
    top_products: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    recent_launch_ratio: float = 0.0
    skipped: bool = False


def _token() -> str | None:
    return os.environ.get("PRODUCTHUNT_TOKEN")


async def search_producthunt(keywords: list[str]) -> ProductHuntResults:
    """Always skipped. Product Hunt's API has no post text search — see module docstring.

    Returns ``skipped=True`` regardless of PRODUCTHUNT_TOKEN, so engine.py redistributes
    Product Hunt's 14% deep-mode weight instead of scoring a fabricated zero.
    """
    return ProductHuntResults(
        skipped=True,
        evidence=[{
            "source": "producthunt",
            "type": "skipped",
            "query": "",
            "count": 0,
            "detail": (
                "Product Hunt disabled: their API has no post text search "
                "(posts() rejects 'search'). Weight redistributed to live sources."
            ),
        }],
    )


async def _search_producthunt_broken(keywords: list[str]) -> ProductHuntResults:
    """Dead code, kept only as the evidence that the query is invalid. Never called.

    ``posts(search: $query)`` returns "Field 'posts' doesn't accept argument 'search'".
    Do not wire this back up without first proving a working search against the live API.
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

    max_total_count = 0
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
                if count > max_total_count:
                    max_total_count = count

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

    # Calculate recent_launch_ratio: products launched in last 6 months / total
    recent_launch_ratio = 0.0
    if unique:
        six_months_ago = datetime.now(timezone.utc) - timedelta(days=182)
        recent_count = 0
        for prod in unique:
            created = prod.get("created_at", "")
            if not created:
                continue
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                if dt >= six_months_ago:
                    recent_count += 1
            except (ValueError, TypeError):
                continue
        recent_launch_ratio = recent_count / len(unique)

    return ProductHuntResults(
        total_count=max_total_count,
        top_products=unique[:5],
        recent_launch_ratio=recent_launch_ratio,
        evidence=evidence,
    )
