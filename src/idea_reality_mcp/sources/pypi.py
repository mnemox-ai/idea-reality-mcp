"""PyPI search source.

PyPI does not offer a public JSON search API, so we scrape the search page
and parse results with simple regex. If parsing fails we degrade gracefully.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import httpx

PYPI_SEARCH_URL = "https://pypi.org/search/"


@dataclass
class PyPIResults:
    """Aggregated PyPI search results."""

    total_count: int = 0
    top_packages: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)


# Patterns for scraping pypi.org/search HTML
_COUNT_PATTERN = re.compile(r'<strong>(?P<count>[\d,]+)</strong>\s*project', re.IGNORECASE)
_PACKAGE_PATTERN = re.compile(
    r'<a\s+class="package-snippet"[^>]*href="(?P<url>/project/[^"]+/)"[^>]*>'
    r'.*?<span\s+class="package-snippet__name"[^>]*>(?P<name>[^<]+)</span>'
    r'.*?<span\s+class="package-snippet__version"[^>]*>(?P<version>[^<]+)</span>'
    r'.*?<p\s+class="package-snippet__description"[^>]*>(?P<desc>[^<]*)</p>',
    re.DOTALL,
)


async def search_pypi(keywords: list[str]) -> PyPIResults:
    """Search PyPI for packages matching keyword variants.

    Args:
        keywords: List of search query strings.

    Returns:
        Aggregated results with total count, top packages, and evidence.
    """
    total_count = 0
    all_packages: list[dict] = []
    evidence: list[dict] = []

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for query in keywords:
            try:
                resp = await client.get(
                    PYPI_SEARCH_URL,
                    params={"q": query},
                )
                resp.raise_for_status()
                html = resp.text

                # Extract total result count
                count_match = _COUNT_PATTERN.search(html)
                count = int(count_match.group("count").replace(",", "")) if count_match else 0
                total_count += count

                # Extract package snippets
                for m in _PACKAGE_PATTERN.finditer(html):
                    all_packages.append({
                        "name": m.group("name").strip(),
                        "url": f"https://pypi.org{m.group('url').strip()}",
                        "version": m.group("version").strip(),
                        "description": m.group("desc").strip()[:200],
                    })

                evidence.append({
                    "source": "pypi",
                    "type": "package_count",
                    "query": query,
                    "count": count,
                    "detail": f"{count} PyPI packages found for '{query}'",
                })
            except httpx.HTTPError:
                evidence.append({
                    "source": "pypi",
                    "type": "error",
                    "query": query,
                    "count": 0,
                    "detail": f"Failed to query PyPI for '{query}'",
                })
            except Exception:
                # HTML parsing failures
                evidence.append({
                    "source": "pypi",
                    "type": "error",
                    "query": query,
                    "count": 0,
                    "detail": f"Failed to parse PyPI results for '{query}'",
                })

    # Deduplicate by name
    seen: set[str] = set()
    unique: list[dict] = []
    for pkg in all_packages:
        if pkg["name"] not in seen:
            seen.add(pkg["name"])
            unique.append(pkg)

    return PyPIResults(
        total_count=total_count,
        top_packages=unique[:5],
        evidence=evidence,
    )
