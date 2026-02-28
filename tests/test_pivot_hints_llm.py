"""Tests for LLM-powered pivot hints generation."""

import json
import os
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure api/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

# Import the function under test
pytest.importorskip("fastapi")

from main import _generate_pivot_hints_llm  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

SAMPLE_SIMILARS = [
    {"name": "semgrep", "stars": 14000, "url": "https://github.com/semgrep/semgrep", "description": "Lightweight static analysis"},
    {"name": "reviewdog", "stars": 9000, "url": "https://github.com/reviewdog/reviewdog", "description": "Automated code review tool"},
    {"name": "npm:eslint-plugin-security", "stars": 0, "url": "https://npmjs.com/package/eslint-plugin-security", "description": "ESLint rules for security"},
]

SAMPLE_EVIDENCE = [
    {"source": "github", "type": "repo_count", "detail": "4523 repos found across queries", "count": 4523},
    {"source": "github", "type": "max_stars", "detail": "Top repo has 14000 stars", "count": 14000},
    {"source": "hackernews", "type": "hn_mention_count", "detail": "87 HN posts in last 12 months for code review", "count": 87},
]


def _mock_haiku_response(content: str):
    """Create a mock Anthropic message response."""
    msg = MagicMock()
    msg.content = [MagicMock(text=content)]
    return msg


def _make_mock_anthropic(mock_client):
    """Create a fake anthropic module with AsyncAnthropic returning mock_client."""
    fake_mod = ModuleType("anthropic")
    fake_mod.AsyncAnthropic = MagicMock(return_value=mock_client)
    return fake_mod


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_returns_none_without_api_key(monkeypatch):
    """Should return None when ANTHROPIC_API_KEY is not set."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    result = await _generate_pivot_hints_llm(
        idea_text="AI code review tool",
        reality_signal=75,
        top_similars=SAMPLE_SIMILARS,
        evidence=SAMPLE_EVIDENCE,
    )
    assert result is None


@pytest.mark.asyncio
async def test_returns_3_hints_on_success(monkeypatch):
    """Should return exactly 3 string hints when Haiku succeeds."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    hints_json = json.dumps([
        "semgrep (14K stars) focuses on SAST but lacks AI-assisted auto-fix. Build an AI-powered fix suggestion layer.",
        "reviewdog (9K stars) only does CI integration with no IDE plugin. A VS Code extension could capture that gap.",
        "eslint-plugin-security has 0 stars on npm — the npm security linting space is underserved for modern frameworks.",
    ])

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_mock_haiku_response(hints_json))

    with patch.dict("sys.modules", {"anthropic": _make_mock_anthropic(mock_client)}):
        result = await _generate_pivot_hints_llm(
            idea_text="AI code review tool",
            reality_signal=75,
            top_similars=SAMPLE_SIMILARS,
            evidence=SAMPLE_EVIDENCE,
        )

    assert result is not None
    assert len(result) == 3
    assert all(isinstance(h, str) for h in result)
    assert "semgrep" in result[0]


@pytest.mark.asyncio
async def test_strips_code_fences(monkeypatch):
    """Should handle Haiku wrapping JSON in markdown code fences."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    fenced = '```json\n["hint one", "hint two", "hint three"]\n```'
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_mock_haiku_response(fenced))

    with patch.dict("sys.modules", {"anthropic": _make_mock_anthropic(mock_client)}):
        result = await _generate_pivot_hints_llm(
            idea_text="test",
            reality_signal=50,
            top_similars=[],
            evidence=[],
        )

    assert result is not None
    assert len(result) == 3
    assert result[0] == "hint one"


@pytest.mark.asyncio
async def test_returns_none_on_invalid_json(monkeypatch):
    """Should return None when Haiku returns non-JSON."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=_mock_haiku_response("Here are some suggestions:\n1. Do X\n2. Do Y")
    )

    with patch.dict("sys.modules", {"anthropic": _make_mock_anthropic(mock_client)}):
        result = await _generate_pivot_hints_llm(
            idea_text="test",
            reality_signal=50,
            top_similars=[],
            evidence=[],
        )

    assert result is None


@pytest.mark.asyncio
async def test_returns_none_on_too_few_hints(monkeypatch):
    """Should return None when Haiku returns fewer than 2 hints."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(
        return_value=_mock_haiku_response('["only one hint"]')
    )

    with patch.dict("sys.modules", {"anthropic": _make_mock_anthropic(mock_client)}):
        result = await _generate_pivot_hints_llm(
            idea_text="test",
            reality_signal=50,
            top_similars=[],
            evidence=[],
        )

    assert result is None


@pytest.mark.asyncio
async def test_returns_none_on_api_exception(monkeypatch):
    """Should return None gracefully when the API call throws."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=Exception("API error"))

    with patch.dict("sys.modules", {"anthropic": _make_mock_anthropic(mock_client)}):
        result = await _generate_pivot_hints_llm(
            idea_text="test",
            reality_signal=50,
            top_similars=[],
            evidence=[],
        )

    assert result is None


@pytest.mark.asyncio
async def test_passes_lang_zh_in_prompt(monkeypatch):
    """Should include lang=zh in the user prompt when specified."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    hints_json = json.dumps(["提示一", "提示二", "提示三"])
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_mock_haiku_response(hints_json))

    with patch.dict("sys.modules", {"anthropic": _make_mock_anthropic(mock_client)}):
        result = await _generate_pivot_hints_llm(
            idea_text="AI 程式碼審查工具",
            reality_signal=75,
            top_similars=SAMPLE_SIMILARS,
            evidence=SAMPLE_EVIDENCE,
            lang="zh",
        )

    assert result is not None
    assert len(result) == 3

    # Verify the prompt included lang=zh
    call_args = mock_client.messages.create.call_args
    user_msg = call_args.kwargs["messages"][0]["content"]
    assert "Lang: zh" in user_msg


@pytest.mark.asyncio
async def test_truncates_to_3_hints(monkeypatch):
    """Should truncate to 3 hints if Haiku returns more."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    hints_json = json.dumps(["one", "two", "three", "four", "five"])
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=_mock_haiku_response(hints_json))

    with patch.dict("sys.modules", {"anthropic": _make_mock_anthropic(mock_client)}):
        result = await _generate_pivot_hints_llm(
            idea_text="test",
            reality_signal=50,
            top_similars=[],
            evidence=[],
        )

    assert result is not None
    assert len(result) == 3


# ---------------------------------------------------------------------------
# Integration test: /api/check returns pivot_source in meta
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_check_endpoint_includes_pivot_source(monkeypatch, tmp_path):
    """The /api/check response should include meta.pivot_source."""
    import db as sdb

    monkeypatch.setattr(sdb, "DB_PATH", str(tmp_path / "test.db"))
    sdb.init_db()
    sdb.init_subscribers_table()

    # Force LLM to fail → should fallback to template
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    from httpx import ASGITransport, AsyncClient
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/check", json={"idea_text": "test idea for pivot"})

    assert resp.status_code == 200
    data = resp.json()
    assert "meta" in data
    assert data["meta"]["pivot_source"] == "template"
    assert isinstance(data["pivot_hints"], list)
    assert len(data["pivot_hints"]) >= 2


@pytest.mark.asyncio
async def test_check_endpoint_accepts_lang_param(monkeypatch, tmp_path):
    """The /api/check should accept lang parameter and include it in meta."""
    import db as sdb

    monkeypatch.setattr(sdb, "DB_PATH", str(tmp_path / "test.db"))
    sdb.init_db()
    sdb.init_subscribers_table()

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    from httpx import ASGITransport, AsyncClient
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/check", json={"idea_text": "test idea", "lang": "zh"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["meta"]["lang"] == "zh"
