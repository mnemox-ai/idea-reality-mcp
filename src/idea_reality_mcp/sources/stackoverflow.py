"""Stack Overflow API source."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import httpx

SO_API = "https://api.stackexchange.com/2.3/search"


@dataclass
class StackOverflowResults:
    """Aggregated Stack Overflow search results."""

    total_count: int = 0
    top_questions: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    recent_question_ratio: float | None = None


def _api_key() -> str | None:
    return os.environ.get("STACKEXCHANGE_KEY")


def _compute_recent_ratio(items: list[dict], three_months_ago: int) -> float | None:
    """Compute ratio of questions within last 3 months vs total items returned.

    Returns None if items is empty or timestamps cannot be parsed.
    """
    if not items:
        return None
    try:
        recent = sum(1 for item in items if item.get("creation_date", 0) >= three_months_ago)
        return recent / len(items)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


async def search_stackoverflow(keywords: list[str]) -> StackOverflowResults:
    """Search Stack Overflow for questions matching keyword variants.

    Uses the Stack Exchange API v2.3.
    Free tier: 300 requests/day without auth.
    Set STACKEXCHANGE_KEY env var for 10,000 requests/day.

    Args:
        keywords: List of search query strings.

    Returns:
        Aggregated results with total question count, top questions, and evidence.
    """
    now = datetime.now(timezone.utc)
    three_months_ago = int((now - timedelta(days=90)).timestamp())
    key = _api_key()

    max_count = 0
    best_ratio: float | None = None
    all_questions: list[dict] = []
    seen_ids: set[int] = set()
    evidence: list[dict] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in keywords:
            params: dict = {
                "order": "desc",
                "sort": "relevance",
                "intitle": query,
                "site": "stackoverflow",
                "pagesize": 10,
                "filter": "!9_bDDxJY5",  # include question_id, title, link, score, answer_count, is_answered, creation_date, tags
            }
            if key:
                params["key"] = key

            try:
                resp = await client.get(SO_API, params=params)
                resp.raise_for_status()
                data = resp.json()

                items = data.get("items", [])
                # The SO API does not return a reliable total in search; use quota_remaining
                # and items count. We use len(items) + has_more as a lower-bound indicator,
                # but treat total as the max items count seen (consistent with HN pattern).
                count = len(items)
                if data.get("has_more"):
                    # Bump count to signal there are more results beyond pagesize
                    count = count + 1

                ratio = _compute_recent_ratio(items, three_months_ago)

                if count > max_count:
                    max_count = count
                    best_ratio = ratio

                # Collect unique questions (dedup by question_id)
                for item in items:
                    qid = item.get("question_id")
                    if qid and qid not in seen_ids:
                        seen_ids.add(qid)
                        all_questions.append({
                            "title": item.get("title", ""),
                            "link": item.get("link", ""),
                            "score": item.get("score", 0),
                            "answer_count": item.get("answer_count", 0),
                            "is_answered": item.get("is_answered", False),
                            "creation_date": item.get("creation_date", 0),
                            "tags": item.get("tags", []),
                        })

                evidence.append({
                    "source": "stackoverflow",
                    "type": "question_count",
                    "query": query,
                    "count": count,
                    "detail": f"{count} Stack Overflow questions found for '{query}'",
                })
            except httpx.HTTPError:
                evidence.append({
                    "source": "stackoverflow",
                    "type": "error",
                    "query": query,
                    "count": 0,
                    "detail": f"Failed to query Stack Overflow for '{query}'",
                })

    # Sort by score descending and keep top 5
    all_questions.sort(key=lambda q: q["score"], reverse=True)
    top_questions = all_questions[:5]

    return StackOverflowResults(
        total_count=max_count,
        top_questions=top_questions,
        evidence=evidence,
        recent_question_ratio=best_ratio,
    )
