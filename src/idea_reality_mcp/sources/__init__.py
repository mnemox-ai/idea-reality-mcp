"""Data source adapters for idea-reality-mcp."""

from .github import GitHubResults, search_github_repos
from .hn import HNResults, search_hn
from .npm import NpmResults, search_npm
from .pypi import PyPIResults, search_pypi
from .producthunt import ProductHuntResults, search_producthunt

__all__ = [
    "GitHubResults",
    "search_github_repos",
    "HNResults",
    "search_hn",
    "NpmResults",
    "search_npm",
    "PyPIResults",
    "search_pypi",
    "ProductHuntResults",
    "search_producthunt",
]
