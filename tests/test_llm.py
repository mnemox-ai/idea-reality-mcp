"""Tests for LLM-powered keyword extraction (MCP client side)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from idea_reality_mcp.scoring.llm import extract_keywords_llm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status_code: int, json_data: dict | None = None) -> httpx.Response:
    """Build a fake httpx.Response."""
    if json_data is not None:
        content = json.dumps(json_data).encode()
    else:
        content = b""
    return httpx.Response(status_code=status_code, content=content)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExtractKeywordsLlm:
    """Tests for the MCP-side LLM keyword extraction client."""

    @pytest.mark.asyncio
    async def test_success_returns_keywords(self):
        """200 with valid JSON → returns keyword list."""
        keywords = ["mcp monitoring llm", "llm observability", "llm api tracing"]
        mock_resp = _mock_response(200, {"keywords": keywords})

        with patch("idea_reality_mcp.scoring.llm.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await extract_keywords_llm("MCP server for monitoring LLM calls")

        assert result == keywords

    @pytest.mark.asyncio
    async def test_rate_limited_returns_none(self):
        """429 → returns None (caller should fall back to dictionary)."""
        mock_resp = _mock_response(429)

        with patch("idea_reality_mcp.scoring.llm.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await extract_keywords_llm("test idea")

        assert result is None

    @pytest.mark.asyncio
    async def test_server_error_returns_none(self):
        """500 → returns None."""
        mock_resp = _mock_response(500)

        with patch("idea_reality_mcp.scoring.llm.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await extract_keywords_llm("test idea")

        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_returns_none(self):
        """Connection timeout → returns None."""
        with patch("idea_reality_mcp.scoring.llm.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await extract_keywords_llm("test idea")

        assert result is None

    @pytest.mark.asyncio
    async def test_connection_error_returns_none(self):
        """Connection refused → returns None."""
        with patch("idea_reality_mcp.scoring.llm.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await extract_keywords_llm("test idea")

        assert result is None

    @pytest.mark.asyncio
    async def test_invalid_json_returns_none(self):
        """200 but non-JSON body → returns None."""
        resp = httpx.Response(200, content=b"not json at all")

        with patch("idea_reality_mcp.scoring.llm.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await extract_keywords_llm("test idea")

        assert result is None

    @pytest.mark.asyncio
    async def test_too_few_keywords_returns_none(self):
        """200 but only 1 keyword → returns None (minimum 2 required)."""
        mock_resp = _mock_response(200, {"keywords": ["only one"]})

        with patch("idea_reality_mcp.scoring.llm.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await extract_keywords_llm("test idea")

        assert result is None

    @pytest.mark.asyncio
    async def test_caps_at_eight_keywords(self):
        """If API returns >8 keywords, result is capped at 8."""
        many = [f"keyword{i}" for i in range(12)]
        mock_resp = _mock_response(200, {"keywords": many})

        with patch("idea_reality_mcp.scoring.llm.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await extract_keywords_llm("test idea")

        assert result is not None
        assert len(result) == 8

    @pytest.mark.asyncio
    async def test_custom_url_via_env_var(self):
        """IDEA_REALITY_API_URL overrides the default API base URL."""
        keywords = ["custom url test", "second query"]
        mock_resp = _mock_response(200, {"keywords": keywords})

        with patch("idea_reality_mcp.scoring.llm.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            with patch.dict(
                "os.environ",
                {"IDEA_REALITY_API_URL": "http://localhost:9999"},
            ):
                result = await extract_keywords_llm("test idea")

            # Verify the custom URL was used
            call_args = instance.post.call_args
            assert "localhost:9999" in call_args[0][0]

        assert result == keywords

    @pytest.mark.asyncio
    async def test_empty_strings_filtered(self):
        """Empty strings in keyword list are filtered out."""
        mock_resp = _mock_response(200, {"keywords": ["valid", "", "  ", "also valid"]})

        with patch("idea_reality_mcp.scoring.llm.httpx.AsyncClient") as MockClient:
            instance = AsyncMock()
            instance.post = AsyncMock(return_value=mock_resp)
            instance.__aenter__ = AsyncMock(return_value=instance)
            instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = instance

            result = await extract_keywords_llm("test idea")

        assert result == ["valid", "also valid"]
