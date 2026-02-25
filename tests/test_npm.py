"""Tests for npm registry source adapter."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from idea_reality_mcp.sources.npm import NpmResults, search_npm


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
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


def _npm_object(name: str, version: str = "1.0.0", description: str = "A package", score: float = 0.5) -> dict:
    return {
        "package": {
            "name": name,
            "version": version,
            "description": description,
            "links": {"npm": f"https://www.npmjs.com/package/{name}"},
        },
        "score": {"final": score},
    }


class TestSearchNpmSuccess:
    @pytest.mark.asyncio
    async def test_basic_success(self):
        api_response = {
            "total": 42,
            "objects": [
                _npm_object("foo-bar", score=0.8),
                _npm_object("baz-qux", score=0.6),
            ],
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(api_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.npm.httpx.AsyncClient", return_value=mock_client):
            result = await search_npm(["test query"])

        assert isinstance(result, NpmResults)
        assert result.total_count == 42
        assert len(result.top_packages) == 2
        assert result.top_packages[0]["name"] == "foo-bar"
        assert result.top_packages[0]["score"] == 0.8
        assert len(result.evidence) == 1
        assert result.evidence[0]["source"] == "npm"
        assert result.evidence[0]["type"] == "package_count"
        assert result.evidence[0]["count"] == 42


class TestSearchNpmEmpty:
    @pytest.mark.asyncio
    async def test_empty_results(self):
        api_response = {"total": 0, "objects": []}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(api_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.npm.httpx.AsyncClient", return_value=mock_client):
            result = await search_npm(["nonexistent"])

        assert isinstance(result, NpmResults)
        assert result.total_count == 0
        assert result.top_packages == []
        assert len(result.evidence) == 1


class TestSearchNpmApiError:
    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response({}, status_code=500)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.npm.httpx.AsyncClient", return_value=mock_client):
            result = await search_npm(["broken query"])

        assert isinstance(result, NpmResults)
        assert result.total_count == 0
        assert result.top_packages == []
        assert len(result.evidence) == 1
        assert result.evidence[0]["type"] == "error"
        assert "Failed" in result.evidence[0]["detail"]


class TestSearchNpmDeduplication:
    @pytest.mark.asyncio
    async def test_dedup_across_keywords(self):
        response_1 = {
            "total": 10,
            "objects": [
                _npm_object("shared-pkg", score=0.9),
                _npm_object("unique-a", score=0.7),
            ],
        }
        response_2 = {
            "total": 8,
            "objects": [
                _npm_object("shared-pkg", score=0.8),
                _npm_object("unique-b", score=0.5),
            ],
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = [
            _mock_response(response_1),
            _mock_response(response_2),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.npm.httpx.AsyncClient", return_value=mock_client):
            result = await search_npm(["kw1", "kw2"])

        assert result.total_count == 18
        names = [p["name"] for p in result.top_packages]
        assert len(names) == 3
        assert len(set(names)) == 3
        # shared-pkg should keep highest score (0.9)
        shared = next(p for p in result.top_packages if p["name"] == "shared-pkg")
        assert shared["score"] == 0.9
