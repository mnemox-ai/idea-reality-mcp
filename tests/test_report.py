"""Tests for paid report generation engine (api/report.py) — V1.0 redesign."""

import json
import os
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure api/ is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import db as score_db  # noqa: E402
import report  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _use_tmp_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    db_path = str(tmp_path / "test_report.db")
    monkeypatch.setattr(score_db, "DB_PATH", db_path)
    monkeypatch.setattr(score_db, "_use_turso", False)
    score_db.init_db()


SAMPLE_SIGNAL_RESULT = {
    "reality_signal": 65,
    "duplicate_likelihood": "high",
    "evidence": [
        {
            "source": "github",
            "type": "repo_count",
            "query": "code review tool",
            "count": 4500,
            "detail": "4500 repos found across queries",
        },
        {
            "source": "github",
            "type": "max_stars",
            "query": "code review tool",
            "count": 14000,
            "detail": "Top repo has 14000 stars",
        },
        {
            "source": "hackernews",
            "type": "hn_mention_count",
            "query": "code review",
            "count": 87,
            "detail": "87 HN posts",
        },
    ],
    "top_similars": [
        {"name": "semgrep/semgrep", "stars": 14000, "url": "https://github.com/semgrep/semgrep", "description": "Lightweight static analysis"},
        {"name": "reviewdog/reviewdog", "stars": 9000, "url": "https://github.com/reviewdog/reviewdog", "description": "Automated code review"},
    ],
    "pivot_hints": ["hint1", "hint2", "hint3"],
    "meta": {
        "checked_at": "2026-03-06T00:00:00+00:00",
        "sources_used": ["github", "hackernews"],
        "depth": "quick",
        "version": "0.5.0",
    },
}


def _mock_response(content: str):
    """Create a mock Anthropic message response."""
    msg = MagicMock()
    msg.content = [MagicMock(text=content)]
    return msg


def _make_mock_anthropic(mock_client):
    """Create a fake anthropic module."""
    fake_mod = ModuleType("anthropic")
    fake_mod.AsyncAnthropic = MagicMock(return_value=mock_client)
    return fake_mod


# ---------------------------------------------------------------------------
# Section 1: Score Breakdown
# ---------------------------------------------------------------------------

class TestScoreBreakdown:
    def test_moderate_score(self):
        result = report._build_score_breakdown(SAMPLE_SIGNAL_RESULT)
        assert result["score"] == 65
        assert result["level"] == "high"
        assert "High competition" in result["summary"]
        assert result["duplicate_likelihood"] == "high"
        assert len(result["source_bars"]) >= 1

    def test_very_high_score(self):
        sr = {**SAMPLE_SIGNAL_RESULT, "reality_signal": 85}
        result = report._build_score_breakdown(sr)
        assert result["level"] == "very_high"
        assert "Very high" in result["summary"]

    def test_low_score(self):
        sr = {**SAMPLE_SIGNAL_RESULT, "reality_signal": 15}
        result = report._build_score_breakdown(sr)
        assert result["level"] == "very_low"

    def test_empty_evidence(self):
        sr = {"reality_signal": 0, "evidence": []}
        result = report._build_score_breakdown(sr)
        assert result["score"] == 0
        assert result["source_bars"] == []

    def test_source_bars_have_percentage(self):
        result = report._build_score_breakdown(SAMPLE_SIGNAL_RESULT)
        for bar in result["source_bars"]:
            assert "source" in bar
            assert "signals" in bar
            assert "percentage" in bar
            assert 0 <= bar["percentage"] <= 100

    def test_bars_sorted_by_signals_desc(self):
        result = report._build_score_breakdown(SAMPLE_SIGNAL_RESULT)
        bars = result["source_bars"]
        if len(bars) >= 2:
            assert bars[0]["signals"] >= bars[1]["signals"]

    def test_explanation_present_for_all_levels(self):
        levels_and_scores = [
            ("very_low", 10),
            ("low", 25),
            ("moderate", 50),
            ("high", 65),
            ("very_high", 90),
        ]
        for expected_level, score_val in levels_and_scores:
            sr = {**SAMPLE_SIGNAL_RESULT, "reality_signal": score_val}
            result = report._build_score_breakdown(sr)
            assert "explanation" in result, f"Missing explanation for {expected_level}"
            assert isinstance(result["explanation"], str)
            assert len(result["explanation"]) > 10

    def test_explanation_matches_level(self):
        sr_low = {**SAMPLE_SIGNAL_RESULT, "reality_signal": 15}
        result = report._build_score_breakdown(sr_low)
        assert result["level"] == "very_low"
        assert "rare and promising" in result["explanation"]

        sr_high = {**SAMPLE_SIGNAL_RESULT, "reality_signal": 70}
        result = report._build_score_breakdown(sr_high)
        assert result["level"] == "high"
        assert "Strong differentiation" in result["explanation"]


# ---------------------------------------------------------------------------
# Section 2: Crowd Intelligence
# ---------------------------------------------------------------------------

class TestCrowdIntelligence:
    def test_no_similar_ideas(self):
        result = report._build_crowd_intelligence(
            "unique quantum widget xyz", "fakehash", 50
        )
        assert result["similar_count"] == 0

    def test_with_matching_ideas(self):
        for i, sc in enumerate([40, 50, 60, 70]):
            score_db.save_score(
                idea_text=f"code review tool variant {i}",
                score=sc, breakdown="{}", keywords="[]",
            )
        result = report._build_crowd_intelligence(
            "code review automation", "excludeme", 55
        )
        assert result["similar_count"] >= 1
        assert result["avg_score"] > 0
        assert "total_database_queries" in result

    def test_no_causal_reasoning_in_message(self):
        """Message should NOT contain causal claims like 'entry angles'."""
        for i in range(5):
            score_db.save_score(
                idea_text=f"monitoring dashboard {i}",
                score=40 + i * 10, breakdown="{}", keywords="[]",
            )
        result = report._build_crowd_intelligence(
            "monitoring dashboard", "excludeme", 45
        )
        msg = result.get("message", "")
        assert "entry" not in msg.lower()
        assert "angle" not in msg.lower()
        assert "opportunity" not in msg.lower()

    def test_short_idea_text(self):
        result = report._build_crowd_intelligence("ab", "hash", 50)
        assert result["similar_count"] == 0

    def test_empty_idea_text(self):
        result = report._build_crowd_intelligence("", "hash", 50)
        assert result["similar_count"] == 0

    def test_unique_message_includes_total_checks(self):
        result = report._build_crowd_intelligence(
            "unique quantum widget xyz", "fakehash", 50
        )
        assert result["similar_count"] == 0
        assert "unique" in result["message"].lower()
        assert "total_database_queries" in result

    def test_score_comparison_higher(self):
        for i, sc in enumerate([30, 35, 40]):
            score_db.save_score(
                idea_text=f"code review tool higher {i}",
                score=sc, breakdown="{}", keywords="[]",
            )
        result = report._build_crowd_intelligence(
            "code review automation", "excludeme", 60
        )
        if result["similar_count"] > 0:
            assert result.get("score_comparison") == "higher than"

    def test_score_comparison_lower(self):
        for i, sc in enumerate([80, 85, 90]):
            score_db.save_score(
                idea_text=f"monitoring dashboard lower {i}",
                score=sc, breakdown="{}", keywords="[]",
            )
        result = report._build_crowd_intelligence(
            "monitoring dashboard tool", "excludeme", 50
        )
        if result["similar_count"] > 0:
            assert result.get("score_comparison") == "lower than"

    def test_score_comparison_similar(self):
        for i, sc in enumerate([48, 50, 52]):
            score_db.save_score(
                idea_text=f"task manager similar {i}",
                score=sc, breakdown="{}", keywords="[]",
            )
        result = report._build_crowd_intelligence(
            "task manager app", "excludeme", 50
        )
        if result["similar_count"] > 0:
            assert result.get("score_comparison") == "similar to"


# ---------------------------------------------------------------------------
# Section 3: Competitors with activity badges
# ---------------------------------------------------------------------------

class TestActivityBadge:
    def test_active_badge(self):
        recent = "2026-03-05T12:00:00Z"
        result = report._activity_badge(recent)
        assert result["badge"] == "🔥"
        assert result["label"] == "active"

    def test_inactive_badge(self):
        old = "2025-01-01T12:00:00Z"
        result = report._activity_badge(old)
        assert result["badge"] == "💤"
        assert result["label"] == "inactive"

    def test_recent_badge(self):
        mid = "2025-12-01T12:00:00Z"
        result = report._activity_badge(mid)
        assert result["badge"] == "⚡"
        assert result["label"] == "recent"

    def test_empty_timestamp(self):
        result = report._activity_badge("")
        assert result["badge"] == "❓"

    def test_invalid_timestamp(self):
        result = report._activity_badge("not-a-date")
        assert result["badge"] == "❓"


class TestCompetitorAnalysis:
    @pytest.mark.asyncio
    async def test_returns_repos_from_github(self):
        github_response = {
            "total_count": 100,
            "items": [
                {
                    "full_name": "owner/repo1",
                    "html_url": "https://github.com/owner/repo1",
                    "stargazers_count": 5000,
                    "description": "A great code review tool",
                    "updated_at": "2026-03-01T00:00:00Z",
                    "created_at": "2025-01-01T00:00:00Z",
                    "language": "Python",
                },
                {
                    "full_name": "owner/repo2",
                    "html_url": "https://github.com/owner/repo2",
                    "stargazers_count": 3000,
                    "description": "Another review tool",
                    "updated_at": "2026-02-15T00:00:00Z",
                    "created_at": "2024-06-01T00:00:00Z",
                    "language": "Go",
                },
            ],
        }

        mock_resp = MagicMock()
        mock_resp.json.return_value = github_response
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await report._build_competitor_analysis(SAMPLE_SIGNAL_RESULT)

        assert len(result) >= 1
        assert result[0]["name"] == "owner/repo1"
        assert "activity" in result[0]
        assert result[0]["activity"]["badge"] in ("🔥", "⚡", "💤", "❓")

    @pytest.mark.asyncio
    async def test_fallback_when_no_keywords(self):
        sr = {
            "reality_signal": 50,
            "evidence": [],
            "top_similars": [
                {"name": "fallback/repo", "stars": 100, "updated": "2026-03-01T00:00:00Z"},
            ],
        }
        result = await report._build_competitor_analysis(sr)
        assert len(result) == 1
        assert result[0]["name"] == "fallback/repo"
        assert "activity" in result[0]

    @pytest.mark.asyncio
    async def test_handles_http_error(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        sr = {
            "reality_signal": 50,
            "evidence": [{"query": "test", "source": "github", "count": 10, "detail": ""}],
            "top_similars": [],
        }

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await report._build_competitor_analysis(sr)

        assert result == []


# ---------------------------------------------------------------------------
# Section 4: Strategic Analysis
# ---------------------------------------------------------------------------

class TestStrategicAnalysis:
    @pytest.mark.asyncio
    async def test_fallback_without_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        result = await report._generate_strategic_analysis(
            "test idea", SAMPLE_SIGNAL_RESULT, [], {}, "en",
        )
        assert isinstance(result, str)
        assert "could not be generated" in result.lower() or len(result) > 10

    @pytest.mark.asyncio
    async def test_successful_llm_call(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        analysis_text = (
            "The competitive landscape for code review tools is dominated by semgrep (14000 stars, active). "
            "A gap exists in real-time review integration. "
            "Position as a lightweight alternative for small teams."
        )

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response(analysis_text)
        )

        with patch.dict("sys.modules", {"anthropic": _make_mock_anthropic(mock_client)}):
            result = await report._generate_strategic_analysis(
                "AI code review", SAMPLE_SIGNAL_RESULT, [], {}, "en",
            )

        assert isinstance(result, str)
        assert "semgrep" in result

    @pytest.mark.asyncio
    async def test_fallback_on_api_exception(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(side_effect=Exception("API down"))

        with patch.dict("sys.modules", {"anthropic": _make_mock_anthropic(mock_client)}):
            result = await report._generate_strategic_analysis(
                "test", SAMPLE_SIGNAL_RESULT, [], {}, "en",
            )

        assert isinstance(result, str)
        assert "could not be generated" in result.lower()

    @pytest.mark.asyncio
    async def test_passes_language_in_prompt(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response("分析結果")
        )

        with patch.dict("sys.modules", {"anthropic": _make_mock_anthropic(mock_client)}):
            await report._generate_strategic_analysis(
                "AI 工具", SAMPLE_SIGNAL_RESULT, [], {}, "zh",
            )

        call_args = mock_client.messages.create.call_args
        user_msg = call_args.kwargs["messages"][0]["content"]
        assert "Language: zh" in user_msg

    @pytest.mark.asyncio
    async def test_uses_sonnet_model(self, monkeypatch):
        """Paid report should use Sonnet, not Haiku."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mock_client = AsyncMock()
        mock_client.messages.create = AsyncMock(
            return_value=_mock_response("analysis")
        )

        with patch.dict("sys.modules", {"anthropic": _make_mock_anthropic(mock_client)}):
            await report._generate_strategic_analysis(
                "test", SAMPLE_SIGNAL_RESULT, [], {}, "en",
            )

        call_args = mock_client.messages.create.call_args
        assert "sonnet" in call_args.kwargs["model"]


# ---------------------------------------------------------------------------
# Integration: generate_report()
# ---------------------------------------------------------------------------

class TestGenerateReport:
    @pytest.mark.asyncio
    async def test_returns_all_sections(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with patch.object(
            report, "_build_competitor_analysis", new_callable=AsyncMock
        ) as mock_comp:
            mock_comp.return_value = [
                {"name": "owner/repo", "stars": 1000, "description": "Test",
                 "activity": {"badge": "🔥", "label": "active", "days_since_update": 5}},
            ]

            result = await report.generate_report(
                "AI code review tool",
                SAMPLE_SIGNAL_RESULT,
                language="en",
            )

        assert "score_breakdown" in result
        assert "crowd_intelligence" in result
        assert "competitors" in result
        assert "strategic_analysis" in result

        assert result["score_breakdown"]["score"] == 65
        assert isinstance(result["crowd_intelligence"]["similar_count"], int)
        assert isinstance(result["competitors"], list)
        assert isinstance(result["strategic_analysis"], str)

    @pytest.mark.asyncio
    async def test_default_language_is_en(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        with patch.object(
            report, "_build_competitor_analysis", new_callable=AsyncMock
        ) as mock_comp:
            mock_comp.return_value = []

            result = await report.generate_report(
                "test idea", SAMPLE_SIGNAL_RESULT,
            )

        # Should return fallback text (not crash)
        assert isinstance(result["strategic_analysis"], str)
