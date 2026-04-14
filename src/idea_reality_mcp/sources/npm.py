"""npm Registry search source."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger(__name__)

NPM_SEARCH_API = "https://registry.npmjs.org/-/v1/search"

# npm full-text search returns wildly inflated totals (e.g., 500K+ for any
# multi-word query).  We cap the raw total and use relevance-filtered counts
# to produce a meaningful signal for the scoring engine.
_MAX_RAW_TOTAL_CAP = 500
_RELEVANCE_MULTIPLIER = 20  # estimate: relevant results ≈ matched_in_page × 20


@dataclass
class NpmResults:
    """Aggregated npm registry search results."""

    total_count: int = 0
    top_packages: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)


async def search_npm(keywords: list[str]) -> NpmResults:
    """Search the npm registry for packages matching keyword variants.

    Args:
        keywords: List of search query strings (typically 3 variants).

    Returns:
        Aggregated results with total count, top packages, and evidence.
    """
    max_total_count = 0
    all_packages: list[dict] = []
    evidence: list[dict] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in keywords:
            try:
                resp = await client.get(
                    NPM_SEARCH_API,
                    params={"text": query, "size": 10},
                )
                resp.raise_for_status()
                data = resp.json()
                raw_total = data.get("total", 0)

                # --- Relevance filtering ---
                # npm full-text search returns inflated totals (e.g., 500K+).
                # Count only packages whose name or description contains at
                # least one meaningful query word (4+ chars).
                query_words = [w.lower() for w in query.split() if len(w) >= 4]
                relevant_in_page = 0

                for obj in data.get("objects", []):
                    pkg = obj.get("package", {})
                    score = obj.get("score", {})
                    pkg_name = (pkg.get("name") or "").lower()
                    pkg_desc = (pkg.get("description") or "").lower()

                    name_match = any(w in pkg_name for w in query_words)
                    desc_match = any(w in pkg_desc for w in query_words)
                    is_relevant = name_match or desc_match

                    if is_relevant:
                        relevant_in_page += 1

                    all_packages.append({
                        "name": pkg.get("name", ""),
                        "url": pkg.get("links", {}).get("npm", f"https://www.npmjs.com/package/{pkg.get('name', '')}"),
                        "version": pkg.get("version", ""),
                        "description": (pkg.get("description") or "")[:200],
                        "score": round(score.get("final", 0), 3),
                    })

                # Estimate true relevant count:
                # - If many results in page are relevant, extrapolate
                # - Cap at _MAX_RAW_TOTAL_CAP to prevent score inflation
                if query_words and relevant_in_page > 0:
                    estimated = min(relevant_in_page * _RELEVANCE_MULTIPLIER, raw_total)
                    count = min(estimated, _MAX_RAW_TOTAL_CAP)
                elif not query_words:
                    # No meaningful words to filter — use raw but capped
                    count = min(raw_total, _MAX_RAW_TOTAL_CAP)
                else:
                    # No relevant results in page — likely noise
                    count = 0

                if count > max_total_count:
                    max_total_count = count

                logger.debug(
                    "[npm] query=%r raw_total=%d relevant=%d/%d estimated=%d",
                    query, raw_total, relevant_in_page,
                    len(data.get("objects", [])), count,
                )

                evidence.append({
                    "source": "npm",
                    "type": "package_count",
                    "query": query,
                    "count": count,
                    "detail": f"{count} relevant npm packages for '{query}' (raw: {raw_total})",
                })
            except httpx.HTTPError as exc:
                logger.warning("[npm] query=%r failed: %s", query, exc)
                evidence.append({
                    "source": "npm",
                    "type": "error",
                    "query": query,
                    "count": 0,
                    "detail": f"Failed to query npm for '{query}'",
                })

    # Deduplicate by name, keep highest score
    seen: dict[str, dict] = {}
    for pkg in all_packages:
        name = pkg["name"]
        if name not in seen or pkg["score"] > seen[name]["score"]:
            seen[name] = pkg
    unique = sorted(seen.values(), key=lambda p: p["score"], reverse=True)

    return NpmResults(
        total_count=max_total_count,
        top_packages=unique[:5],
        evidence=evidence,
    )
