"""Hacker News Algolia API source."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

HN_ALGOLIA_API = "https://hn.algolia.com/api/v1/search"


@dataclass
class HNResults:
    """Aggregated HN search results."""

    total_mentions: int
    evidence: list[dict]


async def search_hn(keywords: list[str]) -> HNResults:
    """Search Hacker News via Algolia for mentions in the last 12 months.

    Args:
        keywords: List of search query strings.

    Returns:
        Aggregated mention count and evidence items.
    """
    twelve_months_ago = int((datetime.now(timezone.utc) - timedelta(days=365)).timestamp())
    total_mentions = 0
    evidence: list[dict] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in keywords:
            try:
                resp = await client.get(
                    HN_ALGOLIA_API,
                    params={
                        "query": query,
                        "tags": "(story,show_hn,ask_hn)",
                        "numericFilters": f"created_at_i>{twelve_months_ago}",
                        "hitsPerPage": 5,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                count = data.get("nbHits", 0)
                total_mentions += count

                evidence.append({
                    "source": "hackernews",
                    "type": "mention_count",
                    "query": query,
                    "count": count,
                    "detail": f"{count} HN posts in last 12 months for '{query}'",
                })
            except httpx.HTTPError:
                evidence.append({
                    "source": "hackernews",
                    "type": "error",
                    "query": query,
                    "count": 0,
                    "detail": f"Failed to query HN for '{query}'",
                })

    return HNResults(total_mentions=total_mentions, evidence=evidence)
