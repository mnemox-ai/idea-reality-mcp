"""PyPI search source — two-tier approach.

Tier 1 (keyless): PyPI JSON API — exact package name lookup.
Tier 2 (with key): libraries.io API — fuzzy search across PyPI packages.

Falls back gracefully: Tier 2 → Tier 1 → skipped.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import httpx

PYPI_JSON_URL = "https://pypi.org/pypi/{package}/json"
LIBRARIES_IO_URL = "https://libraries.io/api/search"


@dataclass
class PyPIResults:
    """Aggregated PyPI search results."""

    total_count: int = 0
    top_packages: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    skipped: bool = False


def _keyword_to_package_names(keyword: str) -> list[str]:
    """Convert a keyword query to candidate PyPI package names.

    'todo app' -> ['todo-app', 'todoapp', 'todo', 'app']
    'web framework' -> ['web-framework', 'webframework', 'web', 'framework']
    """
    words = re.sub(r"[^a-zA-Z0-9\s]", " ", keyword.lower()).split()
    if not words:
        return []
    candidates = []
    if len(words) > 1:
        candidates.append("-".join(words))       # todo-app
        candidates.append("".join(words))         # todoapp
    for w in words:
        if len(w) >= 3:  # skip very short words
            candidates.append(w)
    return candidates


async def _search_pypi_json(keywords: list[str]) -> PyPIResults:
    """Tier 1: Query PyPI JSON API for exact package name matches."""
    found_count = 0
    all_packages: list[dict] = []
    evidence: list[dict] = []
    seen: set[str] = set()

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for keyword in keywords:
            keyword_count = 0
            candidates = _keyword_to_package_names(keyword)
            for pkg_name in candidates:
                if pkg_name in seen:
                    continue
                seen.add(pkg_name)
                try:
                    url = PYPI_JSON_URL.format(package=pkg_name)
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        info = data.get("info", {})
                        found_count += 1
                        keyword_count += 1
                        all_packages.append({
                            "name": info.get("name", pkg_name),
                            "url": f"https://pypi.org/project/{info.get('name', pkg_name)}/",
                            "version": info.get("version", ""),
                            "description": (info.get("summary") or "")[:200],
                        })
                    # 404 = package doesn't exist, that's fine
                except (httpx.HTTPError, Exception):
                    pass  # graceful degradation

            evidence.append({
                "source": "pypi",
                "type": "package_count",
                "query": keyword,
                "count": keyword_count,
                "detail": f"{keyword_count} PyPI packages found for '{keyword}'",
            })

    # Deduplicate by name
    deduped: list[dict] = []
    seen_names: set[str] = set()
    for pkg in all_packages:
        if pkg["name"] not in seen_names:
            seen_names.add(pkg["name"])
            deduped.append(pkg)

    return PyPIResults(
        total_count=found_count,
        top_packages=deduped[:5],
        evidence=evidence,
        skipped=False,
    )


async def _search_libraries_io(keywords: list[str], api_key: str) -> PyPIResults | None:
    """Tier 2: Query libraries.io for fuzzy PyPI package search.

    Returns None on failure (caller falls back to Tier 1).
    """
    max_count = 0
    all_packages: list[dict] = []
    evidence: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            for keyword in keywords:
                try:
                    resp = await client.get(
                        LIBRARIES_IO_URL,
                        params={
                            "q": keyword,
                            "platforms": "pypi",
                            "api_key": api_key,
                            "per_page": 5,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()

                    if not isinstance(data, list):
                        continue

                    count = len(data)
                    if count > max_count:
                        max_count = count

                    for pkg in data:
                        all_packages.append({
                            "name": pkg.get("name", ""),
                            "url": f"https://pypi.org/project/{pkg.get('name', '')}/",
                            "version": pkg.get("latest_release_number", ""),
                            "description": (pkg.get("description") or "")[:200],
                        })

                    evidence.append({
                        "source": "pypi",
                        "type": "package_count",
                        "query": keyword,
                        "count": count,
                        "detail": f"{count} PyPI packages found for '{keyword}'",
                    })
                except httpx.HTTPError:
                    evidence.append({
                        "source": "pypi",
                        "type": "error",
                        "query": keyword,
                        "count": 0,
                        "detail": f"Failed to query libraries.io for '{keyword}'",
                    })
    except Exception:
        return None  # total failure, fall back to Tier 1

    # Deduplicate
    seen: set[str] = set()
    deduped: list[dict] = []
    for pkg in all_packages:
        name = pkg["name"]
        if name and name not in seen:
            seen.add(name)
            deduped.append(pkg)

    return PyPIResults(
        total_count=max_count,
        top_packages=deduped[:5],
        evidence=evidence,
        skipped=False,
    )


async def search_pypi(keywords: list[str]) -> PyPIResults:
    """Search PyPI for packages matching keyword variants.

    Two-tier approach:
    - Tier 2 (libraries.io): fuzzy search if LIBRARIES_IO_KEY env var is set
    - Tier 1 (PyPI JSON): exact package name lookup (always available)

    Falls back gracefully through tiers.
    """
    # Try Tier 2 first (libraries.io — fuzzy search)
    lib_key = os.environ.get("LIBRARIES_IO_KEY")
    if lib_key:
        result = await _search_libraries_io(keywords, lib_key)
        if result is not None and result.total_count > 0:
            return result

    # Fall back to Tier 1 (PyPI JSON — exact match)
    return await _search_pypi_json(keywords)
