"""Tests for GitHub and Hacker News source adapters."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from idea_reality_mcp.sources.github import GitHubResults, search_github_repos
from idea_reality_mcp.sources.hn import HNResults, search_hn


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _github_repo_item(
    full_name: str,
    stars: int = 100,
    description: str = "A repo",
    html_url: str | None = None,
    updated_at: str = "2025-06-01T00:00:00Z",
) -> dict:
    return {
        "full_name": full_name,
        "html_url": html_url or f"https://github.com/{full_name}",
        "stargazers_count": stars,
        "updated_at": updated_at,
        "description": description,
    }


# ===========================================================================
# GitHub tests
# ===========================================================================


class TestSearchGitHubReposSuccess:
    @pytest.mark.asyncio
    async def test_search_github_repos_success(self):
        """Mock a successful API response with repos and verify GitHubResults."""
        items = [
            _github_repo_item("owner/repo-a", stars=500, description="Alpha"),
            _github_repo_item("owner/repo-b", stars=200, description="Beta"),
        ]
        api_response = {"total_count": 42, "items": items}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(api_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.github.httpx.AsyncClient", return_value=mock_client):
            result = await search_github_repos(["test query"])

        assert isinstance(result, GitHubResults)
        assert result.total_repo_count == 42
        assert result.max_stars == 500
        assert len(result.top_repos) == 2
        assert result.top_repos[0]["name"] == "owner/repo-a"
        assert result.top_repos[0]["stars"] == 500
        assert result.top_repos[1]["name"] == "owner/repo-b"


class TestSearchGitHubReposEmpty:
    @pytest.mark.asyncio
    async def test_search_github_repos_empty(self):
        """Mock empty API results."""
        api_response = {"total_count": 0, "items": []}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(api_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.github.httpx.AsyncClient", return_value=mock_client):
            result = await search_github_repos(["nonexistent xyz"])

        assert isinstance(result, GitHubResults)
        assert result.total_repo_count == 0
        assert result.max_stars == 0
        assert result.top_repos == []


class TestSearchGitHubReposMissingName:
    @pytest.mark.asyncio
    async def test_search_github_repos_missing_name(self):
        """Ignore items without a full_name to avoid empty repo entries."""
        items = [
            _github_repo_item("owner/repo-a", stars=500, description="Alpha"),
            {"full_name": "", "stargazers_count": 999, "html_url": "", "updated_at": ""},
        ]
        api_response = {"total_count": 2, "items": items}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(api_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.github.httpx.AsyncClient", return_value=mock_client):
            result = await search_github_repos(["test query"])

        assert isinstance(result, GitHubResults)
        assert result.total_repo_count == 2
        assert result.max_stars == 500
        assert len(result.top_repos) == 1
        assert result.top_repos[0]["name"] == "owner/repo-a"


class TestSearchGitHubReposApiError:
    @pytest.mark.asyncio
    async def test_search_github_repos_api_error(self):
        """Mock an HTTP error and verify graceful degradation (empty results)."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response({}, status_code=403)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.github.httpx.AsyncClient", return_value=mock_client):
            result = await search_github_repos(["will fail"])

        assert isinstance(result, GitHubResults)
        assert result.total_repo_count == 0
        assert result.max_stars == 0
        assert result.top_repos == []


class TestSearchGitHubReposDeduplication:
    @pytest.mark.asyncio
    async def test_search_github_repos_deduplication(self):
        """Mock responses with duplicate repo names across keyword queries, verify dedup."""
        shared_repo = _github_repo_item("owner/shared-repo", stars=300)
        unique_repo_a = _github_repo_item("owner/unique-a", stars=150)
        unique_repo_b = _github_repo_item("owner/unique-b", stars=100)

        response_1 = {"total_count": 10, "items": [shared_repo, unique_repo_a]}
        response_2 = {"total_count": 8, "items": [shared_repo, unique_repo_b]}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = [
            _mock_response(response_1),
            _mock_response(response_2),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.github.httpx.AsyncClient", return_value=mock_client):
            result = await search_github_repos(["keyword1", "keyword2"])

        assert isinstance(result, GitHubResults)
        # total_count is summed across queries
        assert result.total_repo_count == 18
        # Should have 3 unique repos (shared appears once)
        names = [r["name"] for r in result.top_repos]
        assert len(names) == 3
        assert len(set(names)) == 3
        assert "owner/shared-repo" in names
        assert "owner/unique-a" in names
        assert "owner/unique-b" in names
        # Should be sorted by stars descending
        stars = [r["stars"] for r in result.top_repos]
        assert stars == sorted(stars, reverse=True)


# ===========================================================================
# Hacker News tests
# ===========================================================================


class TestSearchHNSuccess:
    @pytest.mark.asyncio
    async def test_search_hn_success(self):
        """Mock a successful HN API response and verify HNResults."""
        api_response = {"nbHits": 15, "hits": []}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(api_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.hn.httpx.AsyncClient", return_value=mock_client):
            result = await search_hn(["test query"])

        assert isinstance(result, HNResults)
        assert result.total_mentions == 15
        assert len(result.evidence) == 1
        assert result.evidence[0]["source"] == "hackernews"
        assert result.evidence[0]["type"] == "mention_count"
        assert result.evidence[0]["query"] == "test query"
        assert result.evidence[0]["count"] == 15


class TestSearchHNEmpty:
    @pytest.mark.asyncio
    async def test_search_hn_empty(self):
        """Mock empty HN results."""
        api_response = {"nbHits": 0, "hits": []}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(api_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.hn.httpx.AsyncClient", return_value=mock_client):
            result = await search_hn(["nothing here"])

        assert isinstance(result, HNResults)
        assert result.total_mentions == 0
        assert len(result.evidence) == 1
        assert result.evidence[0]["count"] == 0


class TestSearchHNApiError:
    @pytest.mark.asyncio
    async def test_search_hn_api_error(self):
        """Mock an HTTP error and verify error evidence is added."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response({}, status_code=500)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.hn.httpx.AsyncClient", return_value=mock_client):
            result = await search_hn(["broken query"])

        assert isinstance(result, HNResults)
        assert result.total_mentions == 0
        assert len(result.evidence) == 1
        assert result.evidence[0]["type"] == "error"
        assert result.evidence[0]["query"] == "broken query"
        assert "Failed" in result.evidence[0]["detail"]


class TestSearchHNMultipleKeywords:
    @pytest.mark.asyncio
    async def test_search_hn_multiple_keywords(self):
        """Mock responses for multiple keywords and verify aggregation."""
        response_1 = {"nbHits": 10, "hits": []}
        response_2 = {"nbHits": 5, "hits": []}
        response_3 = {"nbHits": 20, "hits": []}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = [
            _mock_response(response_1),
            _mock_response(response_2),
            _mock_response(response_3),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.hn.httpx.AsyncClient", return_value=mock_client):
            result = await search_hn(["kw1", "kw2", "kw3"])

        assert isinstance(result, HNResults)
        assert result.total_mentions == 35
        assert len(result.evidence) == 3
        assert result.evidence[0]["query"] == "kw1"
        assert result.evidence[0]["count"] == 10
        assert result.evidence[1]["query"] == "kw2"
        assert result.evidence[1]["count"] == 5
        assert result.evidence[2]["query"] == "kw3"
        assert result.evidence[2]["count"] == 20
