"""Tests for Product Hunt source adapter."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from idea_reality_mcp.sources.producthunt import ProductHuntResults, search_producthunt


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


def _graphql_response(total: int, products: list[dict]) -> dict:
    edges = [{"node": p} for p in products]
    return {"data": {"posts": {"totalCount": total, "edges": edges}}}


class TestSearchProductHuntNoToken:
    @pytest.mark.asyncio
    async def test_skipped_without_token(self):
        with patch("idea_reality_mcp.sources.producthunt._token", return_value=None):
            result = await search_producthunt(["test query"])

        assert isinstance(result, ProductHuntResults)
        assert result.skipped is True
        assert result.total_count == 0
        assert result.top_products == []
        assert len(result.evidence) == 1
        assert result.evidence[0]["type"] == "skipped"


class TestSearchProductHuntSuccess:
    @pytest.mark.asyncio
    async def test_basic_success(self):
        products = [
            {
                "name": "CoolApp",
                "tagline": "The coolest app ever",
                "url": "https://www.producthunt.com/posts/coolapp",
                "votesCount": 500,
                "createdAt": "2025-06-01T00:00:00Z",
            },
            {
                "name": "NiceApp",
                "tagline": "A nice application",
                "url": "https://www.producthunt.com/posts/niceapp",
                "votesCount": 200,
                "createdAt": "2025-05-01T00:00:00Z",
            },
        ]
        api_response = _graphql_response(total=15, products=products)

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.return_value = _mock_response(api_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("idea_reality_mcp.sources.producthunt._token", return_value="fake-token"),
            patch("idea_reality_mcp.sources.producthunt.httpx.AsyncClient", return_value=mock_client),
        ):
            result = await search_producthunt(["test query"])

        assert isinstance(result, ProductHuntResults)
        assert result.skipped is False
        assert result.total_count == 15
        assert len(result.top_products) == 2
        assert result.top_products[0]["name"] == "CoolApp"
        assert result.top_products[0]["votes"] == 500
        assert len(result.evidence) == 1
        assert result.evidence[0]["source"] == "producthunt"
        assert result.evidence[0]["type"] == "product_count"


class TestSearchProductHuntApiError:
    @pytest.mark.asyncio
    async def test_api_error(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.return_value = _mock_response({}, status_code=401)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("idea_reality_mcp.sources.producthunt._token", return_value="bad-token"),
            patch("idea_reality_mcp.sources.producthunt.httpx.AsyncClient", return_value=mock_client),
        ):
            result = await search_producthunt(["broken"])

        assert isinstance(result, ProductHuntResults)
        assert result.total_count == 0
        assert result.top_products == []
        assert len(result.evidence) == 1
        assert result.evidence[0]["type"] == "error"


class TestSearchProductHuntDeduplication:
    @pytest.mark.asyncio
    async def test_dedup_across_keywords(self):
        shared = {
            "name": "SharedApp",
            "tagline": "Shared",
            "url": "https://www.producthunt.com/posts/shared",
            "votesCount": 300,
            "createdAt": "2025-06-01T00:00:00Z",
        }
        unique_a = {
            "name": "UniqueA",
            "tagline": "Unique A",
            "url": "https://www.producthunt.com/posts/uniquea",
            "votesCount": 100,
            "createdAt": "2025-05-01T00:00:00Z",
        }
        response_1 = _graphql_response(total=5, products=[shared, unique_a])
        response_2 = _graphql_response(total=3, products=[shared])

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.side_effect = [
            _mock_response(response_1),
            _mock_response(response_2),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("idea_reality_mcp.sources.producthunt._token", return_value="token"),
            patch("idea_reality_mcp.sources.producthunt.httpx.AsyncClient", return_value=mock_client),
        ):
            result = await search_producthunt(["kw1", "kw2"])

        assert result.total_count == 8
        names = [p["name"] for p in result.top_products]
        assert len(names) == 2
        assert len(set(names)) == 2
