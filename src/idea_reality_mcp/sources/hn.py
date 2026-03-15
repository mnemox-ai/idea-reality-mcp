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
    recent_mention_ratio: float | None = None


def _compute_recent_ratio(hits: list[dict], three_months_ago: int) -> float | None:
    """Compute ratio of hits within last 3 months vs total hits returned.

    Returns None if hits is empty or timestamps cannot be parsed.
    """
    if not hits:
        return None
    try:
        recent = sum(1 for h in hits if h.get("created_at_i", 0) >= three_months_ago)
        return recent / len(hits)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


async def search_hn(keywords: list[str]) -> HNResults:
    """Search Hacker News via Algolia for mentions in the last 12 months.

    Args:
        keywords: List of search query strings.

    Returns:
        Aggregated mention count and evidence items.
    """
    normalized_keywords = list(dict.fromkeys(k.strip() for k in keywords if k.strip()))
    if not normalized_keywords:
        return HNResults(total_mentions=0, evidence=[])

    now = datetime.now(timezone.utc)
    twelve_months_ago = int((now - timedelta(days=365)).timestamp())
    three_months_ago = int((now - timedelta(days=90)).timestamp())
    max_mentions = 0
    best_ratio: float | None = None
    evidence: list[dict] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in normalized_keywords:
            try:
                resp = await client.get(
                    HN_ALGOLIA_API,
                    params={
                        "query": query,
                        "tags": "(story,show_hn,ask_hn)",
                        "numericFilters": f"created_at_i>{twelve_months_ago}",
                        "hitsPerPage": 20,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                count = data.get("nbHits", 0)

                # Parse hits to compute recent_mention_ratio
                ratio = _compute_recent_ratio(data.get("hits", []), three_months_ago)

                if count > max_mentions:
                    max_mentions = count
                    best_ratio = ratio

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

    return HNResults(
        total_mentions=max_mentions,
        evidence=evidence,
        recent_mention_ratio=best_ratio,
    )
