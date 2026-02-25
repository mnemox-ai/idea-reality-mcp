"""Tests for PyPI search source adapter."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from idea_reality_mcp.sources.pypi import PyPIResults, search_pypi


def _mock_response(text: str = "", status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


SAMPLE_HTML = """
<div class="left-layout__main">
  <form>
    <div class="split-layout split-layout--table">
      <div>
        <p>
          <strong>42</strong> projects match your query
        </p>
      </div>
    </div>
  </form>
  <ul>
    <li>
      <a class="package-snippet" href="/project/cool-package/">
        <h3 class="package-snippet__title">
          <span class="package-snippet__name">cool-package</span>
          <span class="package-snippet__version">2.1.0</span>
        </h3>
        <p class="package-snippet__description">A really cool package</p>
      </a>
    </li>
    <li>
      <a class="package-snippet" href="/project/another-pkg/">
        <h3 class="package-snippet__title">
          <span class="package-snippet__name">another-pkg</span>
          <span class="package-snippet__version">0.3.1</span>
        </h3>
        <p class="package-snippet__description">Another useful package</p>
      </a>
    </li>
  </ul>
</div>
"""


class TestSearchPyPISuccess:
    @pytest.mark.asyncio
    async def test_basic_success(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(text=SAMPLE_HTML)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.pypi.httpx.AsyncClient", return_value=mock_client):
            result = await search_pypi(["test query"])

        assert isinstance(result, PyPIResults)
        assert result.total_count == 42
        assert len(result.top_packages) == 2
        assert result.top_packages[0]["name"] == "cool-package"
        assert result.top_packages[0]["version"] == "2.1.0"
        assert result.top_packages[1]["name"] == "another-pkg"
        assert len(result.evidence) == 1
        assert result.evidence[0]["source"] == "pypi"
        assert result.evidence[0]["type"] == "package_count"
        assert result.evidence[0]["count"] == 42


class TestSearchPyPIEmpty:
    @pytest.mark.asyncio
    async def test_no_results(self):
        html = "<div><p>Your search did not match any projects</p></div>"

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(text=html)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.pypi.httpx.AsyncClient", return_value=mock_client):
            result = await search_pypi(["nonexistent"])

        assert isinstance(result, PyPIResults)
        assert result.total_count == 0
        assert result.top_packages == []
        assert len(result.evidence) == 1
        assert result.evidence[0]["count"] == 0


class TestSearchPyPIApiError:
    @pytest.mark.asyncio
    async def test_http_error(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(status_code=500)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.pypi.httpx.AsyncClient", return_value=mock_client):
            result = await search_pypi(["broken"])

        assert isinstance(result, PyPIResults)
        assert result.total_count == 0
        assert result.top_packages == []
        assert len(result.evidence) == 1
        assert result.evidence[0]["type"] == "error"
        assert "Failed" in result.evidence[0]["detail"]


class TestSearchPyPIDeduplication:
    @pytest.mark.asyncio
    async def test_dedup_across_keywords(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = [
            _mock_response(text=SAMPLE_HTML),
            _mock_response(text=SAMPLE_HTML),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.pypi.httpx.AsyncClient", return_value=mock_client):
            result = await search_pypi(["kw1", "kw2"])

        assert result.total_count == 84  # 42 + 42
        names = [p["name"] for p in result.top_packages]
        assert len(set(names)) == len(names)  # no duplicates
