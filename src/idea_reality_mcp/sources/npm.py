"""npm Registry search source."""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

NPM_SEARCH_API = "https://registry.npmjs.org/-/v1/search"


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
    total_count = 0
    all_packages: list[dict] = []
    evidence: list[dict] = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in keywords:
            try:
                resp = await client.get(
                    NPM_SEARCH_API,
                    params={"text": query, "size": 5},
                )
                resp.raise_for_status()
                data = resp.json()
                count = data.get("total", 0)
                total_count += count

                for obj in data.get("objects", []):
                    pkg = obj.get("package", {})
                    score = obj.get("score", {})
                    all_packages.append({
                        "name": pkg.get("name", ""),
                        "url": pkg.get("links", {}).get("npm", f"https://www.npmjs.com/package/{pkg.get('name', '')}"),
                        "version": pkg.get("version", ""),
                        "description": (pkg.get("description") or "")[:200],
                        "score": round(score.get("final", 0), 3),
                    })

                evidence.append({
                    "source": "npm",
                    "type": "package_count",
                    "query": query,
                    "count": count,
                    "detail": f"{count} npm packages found for '{query}'",
                })
            except httpx.HTTPError:
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
        total_count=total_count,
        top_packages=unique[:5],
        evidence=evidence,
    )
