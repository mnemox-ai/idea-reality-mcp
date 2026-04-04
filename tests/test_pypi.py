"""Tests for PyPI search source adapter (two-tier: PyPI JSON + libraries.io)."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from idea_reality_mcp.sources.pypi import PyPIResults, search_pypi, _keyword_to_package_names


def _mock_response(json_data=None, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    if json_data is not None:
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


SAMPLE_PYPI_JSON = {
    "info": {
        "name": "flask",
        "version": "3.0.0",
        "summary": "A simple framework for building complex web applications.",
        "home_page": "https://flask.palletsprojects.com",
        "project_url": "https://pypi.org/project/flask/",
    }
}

SAMPLE_LIBRARIES_IO = [
    {
        "name": "flask",
        "platform": "Pypi",
        "description": "A simple framework for building complex web applications.",
        "repository_url": "https://github.com/pallets/flask",
        "stars": 68000,
        "latest_release_number": "3.0.0",
    },
    {
        "name": "django",
        "platform": "Pypi",
        "description": "A high-level Python web framework.",
        "repository_url": "https://github.com/django/django",
        "stars": 80000,
        "latest_release_number": "5.0",
    },
]


class TestKeywordToPackageNames:
    def test_single_word(self):
        result = _keyword_to_package_names("flask")
        assert "flask" in result

    def test_multi_word(self):
        result = _keyword_to_package_names("todo app")
        assert "todo-app" in result
        assert "todoapp" in result
        assert "todo" in result

    def test_empty_input(self):
        assert _keyword_to_package_names("") == []

    def test_short_words_filtered(self):
        result = _keyword_to_package_names("a b cde")
        assert "cde" in result
        # 'a' and 'b' are too short (< 3 chars)
        assert "a" not in result
        assert "b" not in result


class TestSearchPyPIJsonTier:
    """Tier 1: PyPI JSON API (keyless)."""

    @pytest.mark.asyncio
    async def test_exact_match_found(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(json_data=SAMPLE_PYPI_JSON)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        import os
        env = {k: v for k, v in os.environ.items() if k != "LIBRARIES_IO_KEY"}

        with patch("idea_reality_mcp.sources.pypi.httpx.AsyncClient", return_value=mock_client):
            with patch.dict("os.environ", env, clear=True):
                result = await search_pypi(["flask"])

        assert isinstance(result, PyPIResults)
        assert result.total_count >= 1
        assert not result.skipped
        assert len(result.top_packages) >= 1
        assert result.top_packages[0]["name"] == "flask"

    @pytest.mark.asyncio
    async def test_no_match_returns_zero(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(status_code=404)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        import os
        env = {k: v for k, v in os.environ.items() if k != "LIBRARIES_IO_KEY"}

        with patch("idea_reality_mcp.sources.pypi.httpx.AsyncClient", return_value=mock_client):
            with patch.dict("os.environ", env, clear=True):
                result = await search_pypi(["xyznonexistent123"])

        assert isinstance(result, PyPIResults)
        assert result.total_count == 0
        assert not result.skipped


class TestSearchPyPILibrariesIoTier:
    """Tier 2: libraries.io API (with key)."""

    @pytest.mark.asyncio
    async def test_libraries_io_success(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(json_data=SAMPLE_LIBRARIES_IO)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.pypi.httpx.AsyncClient", return_value=mock_client):
            with patch.dict("os.environ", {"LIBRARIES_IO_KEY": "test-key"}):
                result = await search_pypi(["web framework"])

        assert isinstance(result, PyPIResults)
        assert result.total_count >= 2
        assert not result.skipped


class TestSearchPyPISkipped:
    def test_skipped_field_exists(self):
        result = PyPIResults()
        assert hasattr(result, "skipped")
        assert result.skipped is False

    def test_skipped_field_settable(self):
        result = PyPIResults(skipped=True)
        assert result.skipped is True


class TestSearchPyPIDeduplication:
    @pytest.mark.asyncio
    async def test_dedup_across_keywords(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = [
            _mock_response(json_data=SAMPLE_PYPI_JSON),
            _mock_response(json_data=SAMPLE_PYPI_JSON),  # same package
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        import os
        env = {k: v for k, v in os.environ.items() if k != "LIBRARIES_IO_KEY"}

        with patch("idea_reality_mcp.sources.pypi.httpx.AsyncClient", return_value=mock_client):
            with patch.dict("os.environ", env, clear=True):
                result = await search_pypi(["flask", "flask-web"])

        names = [p["name"] for p in result.top_packages]
        assert len(set(names)) == len(names)  # no duplicates
