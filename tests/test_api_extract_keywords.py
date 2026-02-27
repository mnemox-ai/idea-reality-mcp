"""Tests for the /api/extract-keywords endpoint in api/main.py.

Requires ``fastapi`` and ``anthropic`` — skipped in CI where only core deps
are installed.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Skip entire module if fastapi is not installed (CI only has core deps)
fastapi = pytest.importorskip("fastapi", reason="fastapi not installed (API server tests)")

# Add project root to path so ``api.main`` is importable
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from fastapi.testclient import TestClient  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Create a TestClient for the FastAPI app."""
    from api.main import app  # noqa: E402
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestExtractKeywordsEndpoint:
    """Tests for POST /api/extract-keywords."""

    def test_success(self, client: TestClient):
        """Valid request with ANTHROPIC_API_KEY → 200 + keywords."""
        mock_keywords = ["mcp monitoring", "llm observability", "api tracing"]

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "api.main._extract_keywords_via_haiku",
                new_callable=AsyncMock,
                return_value=mock_keywords,
            ):
                resp = client.post(
                    "/api/extract-keywords",
                    json={"idea_text": "MCP server for monitoring LLM calls"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["keywords"] == mock_keywords

    def test_no_api_key_returns_503(self, client: TestClient):
        """No ANTHROPIC_API_KEY → 503."""
        with patch.dict("os.environ", {}, clear=True):
            # Ensure the key is absent
            import os
            os.environ.pop("ANTHROPIC_API_KEY", None)

            resp = client.post(
                "/api/extract-keywords",
                json={"idea_text": "test idea"},
            )

        assert resp.status_code == 503
        assert "not available" in resp.json()["detail"]

    def test_empty_input_returns_422(self, client: TestClient):
        """Empty idea_text → 422."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            resp = client.post(
                "/api/extract-keywords",
                json={"idea_text": ""},
            )

        assert resp.status_code == 422

    def test_haiku_failure_returns_502(self, client: TestClient):
        """Haiku returns None → 502."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "api.main._extract_keywords_via_haiku",
                new_callable=AsyncMock,
                return_value=None,
            ):
                resp = client.post(
                    "/api/extract-keywords",
                    json={"idea_text": "test idea"},
                )

        assert resp.status_code == 502
        assert "failed" in resp.json()["detail"]

    def test_rate_limit_exceeded(self, client: TestClient):
        """51st request from same IP → 429."""
        from api.main import _rate_limits, DAILY_LIMIT

        # Clear rate limits first
        _rate_limits.clear()

        mock_keywords = ["test query", "another query"]

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "api.main._extract_keywords_via_haiku",
                new_callable=AsyncMock,
                return_value=mock_keywords,
            ):
                # Make DAILY_LIMIT requests (should all succeed)
                for i in range(DAILY_LIMIT):
                    resp = client.post(
                        "/api/extract-keywords",
                        json={"idea_text": f"idea {i}"},
                    )
                    assert resp.status_code == 200, f"Request {i+1} should succeed"

                # The next request should be rate-limited
                resp = client.post(
                    "/api/extract-keywords",
                    json={"idea_text": "one too many"},
                )

        assert resp.status_code == 429
        assert "rate limit" in resp.json()["detail"].lower()

        # Clean up
        _rate_limits.clear()

    def test_rate_limit_resets_daily(self, client: TestClient):
        """Rate limit resets when the date changes."""
        from api.main import _rate_limits

        # Clear rate limits
        _rate_limits.clear()

        mock_keywords = ["test query", "another query"]

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "api.main._extract_keywords_via_haiku",
                new_callable=AsyncMock,
                return_value=mock_keywords,
            ):
                # Simulate yesterday's exhausted quota
                _rate_limits["testclient"]["count"] = 999
                _rate_limits["testclient"]["reset_date"] = "2020-01-01"

                # Should succeed because date has changed
                resp = client.post(
                    "/api/extract-keywords",
                    json={"idea_text": "new day new chance"},
                )

        assert resp.status_code == 200

        # Clean up
        _rate_limits.clear()


class TestCheckEndpointWithLlm:
    """Test that /api/check uses LLM keywords when available."""

    def test_check_uses_llm_keywords(self, client: TestClient):
        """/api/check should try LLM first, add keyword_source to meta."""
        llm_keywords = ["llm generated query", "second query"]

        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            with patch(
                "api.main._extract_keywords_via_haiku",
                new_callable=AsyncMock,
                return_value=llm_keywords,
            ):
                # Mock source searches to avoid real HTTP calls
                with patch("api.main.search_github_repos", new_callable=AsyncMock) as mock_gh, \
                     patch("api.main.search_hn", new_callable=AsyncMock) as mock_hn:

                    from idea_reality_mcp.sources.github import GitHubResults
                    from idea_reality_mcp.sources.hn import HNResults

                    mock_gh.return_value = GitHubResults(
                        total_repo_count=10,
                        max_stars=100,
                        top_repos=[],
                    )
                    mock_hn.return_value = HNResults(
                        total_mentions=5,
                        evidence=[],
                    )

                    resp = client.post(
                        "/api/check",
                        json={"idea_text": "test idea"},
                    )

        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["keyword_source"] == "llm"

    def test_check_falls_back_to_dictionary(self, client: TestClient):
        """/api/check falls back to dictionary when LLM is unavailable."""
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("ANTHROPIC_API_KEY", None)

            # Mock source searches
            with patch("api.main.search_github_repos", new_callable=AsyncMock) as mock_gh, \
                 patch("api.main.search_hn", new_callable=AsyncMock) as mock_hn:

                from idea_reality_mcp.sources.github import GitHubResults
                from idea_reality_mcp.sources.hn import HNResults

                mock_gh.return_value = GitHubResults(
                    total_repo_count=10,
                    max_stars=100,
                    top_repos=[],
                )
                mock_hn.return_value = HNResults(
                    total_mentions=5,
                    evidence=[],
                )

                resp = client.post(
                    "/api/check",
                    json={"idea_text": "monitoring llm api calls"},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["meta"]["keyword_source"] == "dictionary"
