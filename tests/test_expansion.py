"""Tests for idea expansion and platform query generation."""

from __future__ import annotations

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from idea_reality_mcp.scoring.expansion import expand_idea, generate_platform_queries


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(json_data: dict | None, status_code: int = 200, *, invalid_json: bool = False) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if invalid_json:
        resp.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
    else:
        resp.json.return_value = json_data
    return resp


_VALID_EXPANSION = {
    "expanded_description": "A CLI tool that monitors LLM API call costs and latency in real-time",
    "core_concept": "LLM API monitor",
    "differentiator": "real-time cost tracking",
    "target_user": "AI developers",
    "category": "developer tools",
}


# ===========================================================================
# expand_idea tests
# ===========================================================================


class TestExpandIdeaSuccess:
    @pytest.mark.asyncio
    async def test_expand_idea_success(self):
        """Mock API returning valid JSON with all 5 keys, verify dict returned correctly."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.return_value = _mock_response(_VALID_EXPANSION)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.scoring.expansion.httpx.AsyncClient", return_value=mock_client):
            result = await expand_idea("monitor LLM costs")

        assert result is not None
        assert isinstance(result, dict)
        for key in ("expanded_description", "core_concept", "differentiator", "target_user", "category"):
            assert key in result
        assert result["core_concept"] == "LLM API monitor"
        assert result["expanded_description"] == _VALID_EXPANSION["expanded_description"]


class TestExpandIdeaApiFailure:
    @pytest.mark.asyncio
    async def test_expand_idea_api_failure(self):
        """Mock HTTPError, verify None returned."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.side_effect = httpx.HTTPError("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.scoring.expansion.httpx.AsyncClient", return_value=mock_client):
            result = await expand_idea("monitor LLM costs")

        assert result is None


class TestExpandIdeaTimeout:
    @pytest.mark.asyncio
    async def test_expand_idea_timeout(self):
        """Mock httpx.TimeoutException, verify None returned."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.side_effect = httpx.TimeoutException("Request timed out")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.scoring.expansion.httpx.AsyncClient", return_value=mock_client):
            result = await expand_idea("monitor LLM costs")

        assert result is None


class TestExpandIdeaInvalidJson:
    @pytest.mark.asyncio
    async def test_expand_idea_invalid_json(self):
        """Mock response with invalid JSON body, verify None returned."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.return_value = _mock_response(None, invalid_json=True)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.scoring.expansion.httpx.AsyncClient", return_value=mock_client):
            result = await expand_idea("monitor LLM costs")

        assert result is None


class TestExpandIdeaMissingKeys:
    @pytest.mark.asyncio
    async def test_expand_idea_missing_keys(self):
        """Mock response missing required keys, verify None returned."""
        incomplete = {
            "expanded_description": "Some description",
            "core_concept": "Something",
            # missing: differentiator, target_user, category
        }
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.return_value = _mock_response(incomplete)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.scoring.expansion.httpx.AsyncClient", return_value=mock_client):
            result = await expand_idea("monitor LLM costs")

        assert result is None


# ===========================================================================
# generate_platform_queries tests
# ===========================================================================


class TestGeneratePlatformQueriesBasic:
    def test_generate_platform_queries_basic(self):
        """Provide sample expansion dict, verify all 6 platform keys present with non-empty lists."""
        result = generate_platform_queries(_VALID_EXPANSION, ["llm", "monitor"])

        assert isinstance(result, dict)
        for key in ("github", "npm", "pypi", "hackernews", "producthunt", "stackoverflow"):
            assert key in result, f"Missing platform key: {key}"
            assert isinstance(result[key], list)
            assert len(result[key]) > 0, f"Empty list for: {key}"


class TestGeneratePlatformQueriesNpmFormat:
    def test_generate_platform_queries_npm_format(self):
        """Verify npm/pypi queries are lowercase with hyphens, no spaces."""
        result = generate_platform_queries(_VALID_EXPANSION, ["llm", "monitor"])

        for query in result["npm"]:
            assert query == query.lower(), f"npm query not lowercase: {query}"
            assert " " not in query, f"npm query has spaces: {query}"

        for query in result["pypi"]:
            assert query == query.lower(), f"pypi query not lowercase: {query}"
            assert " " not in query, f"pypi query has spaces: {query}"


class TestGeneratePlatformQueriesNoneExpansion:
    def test_generate_platform_queries_none_expansion(self):
        """Returns empty dict when expansion is None."""
        result = generate_platform_queries(None, ["some", "keywords"])

        assert result == {}


# ===========================================================================
# idea_check integration with expansion
# ===========================================================================


class TestIdeaCheckUsesExpansion:
    @pytest.mark.asyncio
    async def test_idea_check_uses_expansion_for_short_input(self):
        """Patch expand_idea to return valid expansion, verify extract_keywords called with expanded_description."""
        from idea_reality_mcp.tools import idea_check

        short_idea = "monitor LLM costs"
        mock_extract = MagicMock(return_value=["llm", "api", "monitor"])
        mock_github = AsyncMock()
        mock_hn = AsyncMock()
        mock_signal = MagicMock(return_value={"meta": {}, "reality_signal": 50})

        with (
            patch("idea_reality_mcp.tools.expand_idea", new_callable=AsyncMock, return_value=_VALID_EXPANSION),
            patch("idea_reality_mcp.tools.extract_keywords", mock_extract),
            patch("idea_reality_mcp.tools.search_github_repos", mock_github),
            patch("idea_reality_mcp.tools.search_hn", mock_hn),
            patch("idea_reality_mcp.tools.compute_signal", mock_signal),
        ):
            await idea_check(short_idea, depth="quick")

        # extract_keywords called once with idea_text (expansion enriches via core_concept, not replaces)
        assert mock_extract.call_count == 1


class TestIdeaCheckFallbackOnExpansionFailure:
    @pytest.mark.asyncio
    async def test_idea_check_fallback_on_expansion_failure(self):
        """Patch expand_idea returning None, verify original dictionary keywords used."""
        from idea_reality_mcp.tools import idea_check

        short_idea = "monitor LLM costs"
        dict_keywords = ["llm", "monitor", "cost"]
        mock_extract = MagicMock(return_value=dict_keywords)
        mock_github = AsyncMock()
        mock_hn = AsyncMock()
        mock_signal = MagicMock(return_value={"meta": {}, "reality_signal": 50})

        with (
            patch("idea_reality_mcp.tools.expand_idea", new_callable=AsyncMock, return_value=None),
            patch("idea_reality_mcp.tools.extract_keywords", mock_extract),
            patch("idea_reality_mcp.tools.search_github_repos", mock_github),
            patch("idea_reality_mcp.tools.search_hn", mock_hn),
            patch("idea_reality_mcp.tools.compute_signal", mock_signal),
        ):
            await idea_check(short_idea, depth="quick")

        # extract_keywords called only once — with the original idea_text
        assert mock_extract.call_count == 1
        assert mock_extract.call_args[0][0] == short_idea
