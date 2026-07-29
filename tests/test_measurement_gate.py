"""Measurement gate — a source that failed must never be scored as a zero.

Before this, a rate-limited GitHub query returned None, fell through the
aggregation loop, and left total_repo_count at 0. "We could not look" was
indistinguishable from "nobody has built this", so the same idea text came back
88 one minute and 44 the next. These tests pin the fix: failures are counted,
the affected dimensions report null, and the composite is withheld entirely.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from idea_reality_mcp.scoring.engine import compute_signal
from idea_reality_mcp.sources.github import GitHubResults, search_github_repos
from idea_reality_mcp.sources.hn import HNResults, search_hn


def _gh(count=100, stars=500, *, attempted=2, failed=0) -> GitHubResults:
    return GitHubResults(
        total_repo_count=count,
        max_stars=stars,
        top_repos=[],
        queries_attempted=attempted,
        queries_failed=failed,
    )


def _hn(mentions=30, *, attempted=1, failed=0) -> HNResults:
    return HNResults(
        total_mentions=mentions,
        evidence=[],
        queries_attempted=attempted,
        queries_failed=failed,
    )


def _signal(github, hn):
    return compute_signal(
        idea_text="a tool that does X",
        keywords=["x tool"],
        github_results=github,
        hn_results=hn,
        depth="quick",
    )


class TestMeasuredFlag:
    def test_all_queries_returned(self):
        assert _gh().measured is True
        assert _hn().measured is True

    def test_any_failure_marks_unmeasured(self):
        assert _gh(attempted=2, failed=1).measured is False
        assert _hn(attempted=3, failed=3).measured is False

    def test_nothing_attempted_is_not_measured(self):
        assert _gh(attempted=0, failed=0).measured is False


class TestSignalWithheld:
    def test_github_failure_withholds_composite_and_its_dimensions(self):
        out = _signal(_gh(attempted=2, failed=2), _hn())

        assert out["reality_signal"] is None, "must not invent a score from data we never collected"
        assert out["duplicate_likelihood"] is None
        assert out["sub_scores"]["competition_density"] is None
        assert out["sub_scores"]["market_maturity"] is None
        # HN was fine, so its dimension survives
        assert out["sub_scores"]["community_buzz"] is not None

        m = out["meta"]["measurement"]
        assert m["complete"] is False
        assert m["sources"]["github"] == "failed"
        assert m["sources"]["hackernews"] == "ok"
        assert "competition_density" in m["unmeasured"]

    def test_hn_failure_withholds_composite(self):
        out = _signal(_gh(), _hn(attempted=2, failed=1))

        assert out["reality_signal"] is None
        assert out["sub_scores"]["community_buzz"] is None
        assert out["sub_scores"]["competition_density"] is not None
        assert out["meta"]["measurement"]["sources"]["hackernews"] == "failed"

    def test_a_failed_scan_is_not_a_low_score(self):
        """The 44-vs-88 bug, pinned.

        A busy space whose GitHub lookup fails must not come back looking like
        an empty one — it must come back saying it does not know.
        """
        busy = _signal(_gh(count=4000, stars=3700), _hn(mentions=30))
        broken = _signal(_gh(count=0, stars=0, attempted=2, failed=2), _hn(mentions=30))

        assert busy["reality_signal"] is not None and busy["reality_signal"] > 60
        assert broken["reality_signal"] is None
        assert broken["meta"]["measurement"]["complete"] is False


class TestUnaffectedPaths:
    def test_fully_measured_scan_is_unchanged(self):
        out = _signal(_gh(count=4000, stars=3700), _hn(mentions=30))

        assert isinstance(out["reality_signal"], int)
        assert out["duplicate_likelihood"] in ("low", "medium", "high")
        assert out["meta"]["measurement"] == {
            "complete": True,
            "sources": {"github": "ok", "hackernews": "ok"},
            "unmeasured": [],
        }

    def test_results_without_counters_are_treated_as_measured(self):
        """Back-compat: callers and fixtures predating the counters still score."""
        legacy_gh = GitHubResults(total_repo_count=100, max_stars=500, top_repos=[])
        legacy_hn = HNResults(total_mentions=10, evidence=[])

        out = _signal(legacy_gh, legacy_hn)
        assert isinstance(out["reality_signal"], int)
        assert out["meta"]["measurement"]["complete"] is True

    def test_evidence_and_hints_survive_a_failure(self):
        """A failed scan still returns what it DID observe — it just refuses to score it."""
        out = _signal(_gh(attempted=2, failed=2), _hn(mentions=5))
        assert "evidence" in out
        assert isinstance(out["pivot_hints"], list)


@pytest.mark.asyncio
class TestSourcesCountFailures:
    async def test_github_counts_failed_queries(self):
        client = MagicMock()
        client.get = AsyncMock(side_effect=httpx.ConnectError("boom"))
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.github.httpx.AsyncClient", return_value=client):
            res = await search_github_repos(["voice agent"])

        assert res.queries_failed > 0
        assert res.measured is False
        assert res.total_repo_count == 0  # still zero, but now knowably untrustworthy

    async def test_hn_counts_failed_queries(self):
        client = MagicMock()
        client.get = AsyncMock(side_effect=httpx.ConnectError("boom"))
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.hn.httpx.AsyncClient", return_value=client):
            res = await search_hn(["voice agent"])

        assert res.queries_attempted == 1
        assert res.queries_failed == 1
        assert res.measured is False


class TestDemandUnit:
    """The two demand paths count different things and must say which.

    topic_demand reads demand_topics.searches_90d, which build_demand_topics.py
    computes as DISTINCT ip_hash per window — people. _demand_heat counts rows in
    score_history — searches, where one person searching ten times counts ten.
    They emitted the same field name and the same wording, so a caller phrasing it
    as "N people" would have been right on one path and wrong on the other.
    """

    def test_semantic_path_declares_searches(self):
        from api.report import _demand_heat
        from datetime import datetime, timedelta, timezone

        recent = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        out = _demand_heat([
            {"similarity": 0.9, "created_at": recent},
            {"similarity": 0.8, "created_at": recent},
        ])
        assert out is not None
        assert out["unit"] == "searches"
        assert "searches" in out["message"]

    def test_topic_path_declares_requesters(self):
        """Shape check on the constant, without standing up embeddings/Turso."""
        import inspect

        from api import report

        src = inspect.getsource(report.topic_demand)
        assert '"unit": "requesters"' in src
        assert "people have" in src
