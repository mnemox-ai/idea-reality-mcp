"""Tests for GitHub source adapter — retry logic and query normalization."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from idea_reality_mcp.sources.github import (
    GitHubResults,
    _normalize_query,
    _github_get_with_retry,
    search_github_repos,
)


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.request = MagicMock()
    if status_code >= 400 and status_code not in (403, 429):
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=resp.request,
            response=resp,
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


class TestNormalizeQuery:
    def test_hyphens_to_spaces(self):
        assert _normalize_query("voice-scheduling-agent") == "voice scheduling agent"

    def test_no_hyphens(self):
        assert _normalize_query("voice scheduling agent") == "voice scheduling agent"

    def test_mixed(self):
        assert _normalize_query("tia-portal mcp-server") == "tia portal mcp server"

    def test_empty(self):
        assert _normalize_query("") == ""


class TestGitHubGetWithRetry:
    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        """200 response — no retry needed."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response({"total_count": 5, "items": []})

        result = await _github_get_with_retry(
            mock_client, params={"q": "test"}, label="test"
        )
        assert result.json()["total_count"] == 5
        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_429_then_success(self):
        """429 on first attempt, 200 on second."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = [
            _mock_response({}, status_code=429),
            _mock_response({"total_count": 10, "items": []}, status_code=200),
        ]

        with patch("idea_reality_mcp.sources.github.asyncio.sleep", new_callable=AsyncMock):
            result = await _github_get_with_retry(
                mock_client, params={"q": "test"}, label="test"
            )
        assert result.json()["total_count"] == 10
        assert mock_client.get.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_403_then_success(self):
        """403 on first attempt, 200 on second."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = [
            _mock_response({}, status_code=403),
            _mock_response({"total_count": 3, "items": []}, status_code=200),
        ]

        with patch("idea_reality_mcp.sources.github.asyncio.sleep", new_callable=AsyncMock):
            result = await _github_get_with_retry(
                mock_client, params={"q": "test"}, label="test"
            )
        assert result.json()["total_count"] == 3

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        """429 on all attempts — raises HTTPStatusError."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response({}, status_code=429)

        with patch("idea_reality_mcp.sources.github.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(httpx.HTTPStatusError):
                await _github_get_with_retry(
                    mock_client, params={"q": "test"}, label="test"
                )
        # 1 initial + 2 retries = 3 attempts
        assert mock_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_non_rate_limit_error_raises_immediately(self):
        """500 error — raises immediately, no retry."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        resp = _mock_response({}, status_code=500)
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=resp
        )
        mock_client.get.return_value = resp

        with pytest.raises(httpx.HTTPStatusError):
            await _github_get_with_retry(
                mock_client, params={"q": "test"}, label="test"
            )
        assert mock_client.get.call_count == 1


class TestSearchGitHubReposNormalization:
    @pytest.mark.asyncio
    async def test_keywords_normalized(self):
        """Verify hyphens in keywords are converted to spaces for GitHub API."""
        api_response = {"total_count": 0, "items": []}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(api_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.github.httpx.AsyncClient", return_value=mock_client):
            with patch("idea_reality_mcp.sources.github._github_get_with_retry", new_callable=AsyncMock) as mock_retry:
                mock_retry.return_value = _mock_response(api_response)
                await search_github_repos(["tia-portal-mcp"])

                # Check the first call's query has spaces (not hyphens)
                first_call = mock_retry.call_args_list[0]
                params = first_call.kwargs.get("params") or first_call[1].get("params", {})
                assert "tia portal mcp" in params["q"]
                assert "-" not in params["q"]
