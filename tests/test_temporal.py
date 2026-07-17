"""Tests for temporal signals and score recalibration.

(a) GitHub temporal — recent_ratio / recently_updated_ratio from mocked updated_at dates
(b) HN temporal — recent_mention_ratio from mocked created_at_i timestamps
(c) PH temporal — recent_launch_ratio from mocked createdAt dates
(d) Score recalibration — log-curve calibration points within ±3
(e) Temporal boost — momentum > 0.6 positive, < 0.3 negative
(f) Trend label — accelerating/stable/declining boundary thresholds
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from idea_reality_mcp.scoring.engine import (
    _github_repo_score,
    _github_star_score,
    _hn_score,
    _npm_score,
    _ph_score,
    _pypi_score,
    compute_signal,
)
from idea_reality_mcp.sources.github import GitHubResults, search_github_repos
from idea_reality_mcp.sources.hn import HNResults, _compute_recent_ratio, search_hn
from idea_reality_mcp.sources.npm import NpmResults
from idea_reality_mcp.sources.pypi import PyPIResults
from idea_reality_mcp.sources.producthunt import ProductHuntResults, search_producthunt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


def _make_github(
    count: int = 0, stars: int = 0, recent_ratio: float = 0.5,
) -> GitHubResults:
    repos = []
    if count > 0:
        repos = [{
            "name": "user/repo",
            "url": "https://github.com/user/repo",
            "stars": stars,
            "updated": "2025-01-01T00:00:00Z",
            "description": "A project",
        }]
    return GitHubResults(
        total_repo_count=count, max_stars=stars, top_repos=repos,
        recent_ratio=recent_ratio,
    )


def _make_hn(
    mentions: int = 0, recent_mention_ratio: float | None = None,
) -> HNResults:
    evidence = []
    if mentions > 0:
        evidence = [{
            "source": "hackernews",
            "type": "mention_count",
            "query": "test",
            "count": mentions,
            "detail": f"{mentions} mentions",
        }]
    return HNResults(
        total_mentions=mentions, evidence=evidence,
        recent_mention_ratio=recent_mention_ratio,
    )


def _graphql_response(total: int, products: list[dict]) -> dict:
    edges = [{"node": p} for p in products]
    return {"data": {"posts": {"totalCount": total, "edges": edges}}}


# ===========================================================================
# (a) GitHub temporal — updated_at dates → recent_ratio / recently_updated_ratio
# ===========================================================================


class TestGitHubTemporal:
    @pytest.mark.asyncio
    async def test_recent_ratio_from_created_filter(self):
        """recent_ratio = recent_created_count / total_repo_count."""
        now = datetime.now(timezone.utc)
        recent_date = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        old_date = (now - timedelta(days=400)).strftime("%Y-%m-%dT%H:%M:%SZ")

        items = [
            {
                "full_name": "owner/new-repo",
                "html_url": "https://github.com/owner/new-repo",
                "stargazers_count": 100,
                "updated_at": recent_date,
                "description": "A recently created test project",
            },
            {
                "full_name": "owner/old-repo",
                "html_url": "https://github.com/owner/old-repo",
                "stargazers_count": 200,
                "updated_at": old_date,
                "description": "An older test project still active",
            },
        ]
        main_response = {"total_count": 20, "items": items}
        recent_response = {"total_count": 6, "items": []}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = [
            _mock_response(main_response),
            _mock_response(recent_response),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.github.httpx.AsyncClient", return_value=mock_client):
            result = await search_github_repos(["test project"])

        assert isinstance(result, GitHubResults)
        # recent_ratio = 6 / 20 = 0.3
        assert abs(result.recent_ratio - 0.3) < 0.01
        assert result.recent_created_count == 6

    @pytest.mark.asyncio
    async def test_recently_updated_ratio(self):
        """recently_updated_ratio = fraction of top repos updated within 6 months."""
        now = datetime.now(timezone.utc)
        recent_date = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        old_date = (now - timedelta(days=300)).strftime("%Y-%m-%dT%H:%M:%SZ")

        items = [
            {
                "full_name": "owner/recent-update",
                "html_url": "https://github.com/owner/recent-update",
                "stargazers_count": 300,
                "updated_at": recent_date,
                "description": "Recently updated test project",
            },
            {
                "full_name": "owner/stale-update",
                "html_url": "https://github.com/owner/stale-update",
                "stargazers_count": 150,
                "updated_at": old_date,
                "description": "Stale test project not updated",
            },
        ]
        main_response = {"total_count": 10, "items": items}
        recent_response = {"total_count": 3, "items": []}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = [
            _mock_response(main_response),
            _mock_response(recent_response),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.github.httpx.AsyncClient", return_value=mock_client):
            result = await search_github_repos(["test project"])

        # 1 of 2 repos updated recently → 0.5
        assert abs(result.recently_updated_ratio - 0.5) < 0.01

    @pytest.mark.asyncio
    async def test_all_repos_recently_updated(self):
        """All top repos updated within 6 months → ratio 1.0."""
        now = datetime.now(timezone.utc)
        recent_date = (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")

        items = [
            {
                "full_name": "owner/repo-a",
                "html_url": "https://github.com/owner/repo-a",
                "stargazers_count": 500,
                "updated_at": recent_date,
                "description": "Active test project alpha",
            },
            {
                "full_name": "owner/repo-b",
                "html_url": "https://github.com/owner/repo-b",
                "stargazers_count": 400,
                "updated_at": recent_date,
                "description": "Active test project beta",
            },
        ]
        main_response = {"total_count": 50, "items": items}
        recent_response = {"total_count": 50, "items": []}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = [
            _mock_response(main_response),
            _mock_response(recent_response),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.github.httpx.AsyncClient", return_value=mock_client):
            result = await search_github_repos(["test project"])

        assert abs(result.recently_updated_ratio - 1.0) < 0.01
        # recent_ratio = 50/50 = 1.0 (capped)
        assert abs(result.recent_ratio - 1.0) < 0.01

    @pytest.mark.asyncio
    async def test_zero_total_gives_zero_ratio(self):
        """No repos → recent_ratio = 0.0."""
        main_response = {"total_count": 0, "items": []}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = [
            _mock_response(main_response),
            _mock_response({"total_count": 0, "items": []}),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.github.httpx.AsyncClient", return_value=mock_client):
            result = await search_github_repos(["nonexistent xyz"])

        assert result.recent_ratio == 0.0
        assert result.recently_updated_ratio == 0.0


# ===========================================================================
# (b) HN temporal — created_at_i timestamps → recent_mention_ratio
# ===========================================================================


class TestHNTemporal:
    def test_compute_recent_ratio_all_recent(self):
        """All hits within 3 months → ratio 1.0."""
        now = int(time.time())
        hits = [
            {"created_at_i": now - 86400},       # 1 day ago
            {"created_at_i": now - 86400 * 30},   # 30 days ago
            {"created_at_i": now - 86400 * 60},   # 60 days ago
        ]
        three_months_ago = now - 86400 * 90
        ratio = _compute_recent_ratio(hits, three_months_ago)
        assert ratio == 1.0

    def test_compute_recent_ratio_none_recent(self):
        """All hits older than 3 months → ratio 0.0."""
        now = int(time.time())
        hits = [
            {"created_at_i": now - 86400 * 100},  # 100 days ago
            {"created_at_i": now - 86400 * 200},  # 200 days ago
            {"created_at_i": now - 86400 * 300},  # 300 days ago
        ]
        three_months_ago = now - 86400 * 90
        ratio = _compute_recent_ratio(hits, three_months_ago)
        assert ratio == 0.0

    def test_compute_recent_ratio_mixed(self):
        """2 of 4 hits recent → ratio 0.5."""
        now = int(time.time())
        hits = [
            {"created_at_i": now - 86400 * 10},   # recent
            {"created_at_i": now - 86400 * 50},   # recent
            {"created_at_i": now - 86400 * 120},  # old
            {"created_at_i": now - 86400 * 200},  # old
        ]
        three_months_ago = now - 86400 * 90
        ratio = _compute_recent_ratio(hits, three_months_ago)
        assert ratio == 0.5

    def test_compute_recent_ratio_empty(self):
        """Empty hits → None."""
        ratio = _compute_recent_ratio([], 0)
        assert ratio is None

    @pytest.mark.asyncio
    async def test_search_hn_recent_mention_ratio(self):
        """Mock HN response with created_at_i timestamps, verify ratio propagation."""
        now = int(time.time())
        hits = [
            {"created_at_i": now - 86400 * 5, "objectID": "1"},    # 5 days ago
            {"created_at_i": now - 86400 * 30, "objectID": "2"},   # 30 days ago
            {"created_at_i": now - 86400 * 120, "objectID": "3"},  # 120 days ago
            {"created_at_i": now - 86400 * 200, "objectID": "4"},  # 200 days ago
        ]
        api_response = {"nbHits": 25, "hits": hits}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(api_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.hn.httpx.AsyncClient", return_value=mock_client):
            result = await search_hn(["test query"])

        assert isinstance(result, HNResults)
        assert result.total_mentions == 25
        # 2 of 4 hits within 3 months → 0.5
        assert result.recent_mention_ratio is not None
        assert abs(result.recent_mention_ratio - 0.5) < 0.01

    @pytest.mark.asyncio
    async def test_search_hn_all_recent_ratio(self):
        """All HN hits recent → ratio 1.0."""
        now = int(time.time())
        hits = [
            {"created_at_i": now - 86400, "objectID": "1"},
            {"created_at_i": now - 86400 * 10, "objectID": "2"},
        ]
        api_response = {"nbHits": 10, "hits": hits}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(api_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.hn.httpx.AsyncClient", return_value=mock_client):
            result = await search_hn(["trending topic"])

        assert result.recent_mention_ratio == 1.0

    @pytest.mark.asyncio
    async def test_search_hn_no_hits_ratio_none(self):
        """No hits returned → recent_mention_ratio is None."""
        api_response = {"nbHits": 0, "hits": []}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(api_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.hn.httpx.AsyncClient", return_value=mock_client):
            result = await search_hn(["nothing here"])

        assert result.recent_mention_ratio is None


# ===========================================================================
# (c) PH temporal — createdAt dates → recent_launch_ratio
# ===========================================================================


class TestPHTemporal:
    """Product Hunt is permanently disabled, so its temporal signal is always absent.

    These four tests used to mock a GraphQL reply Product Hunt cannot give — the query
    asks for posts(search:), which the live API rejects — then asserted the parser read
    the mock's invented createdAt dates correctly. They passed for four months against a
    source that has never returned a single row. See tests/test_producthunt.py.

    recent_launch_ratio must stay 0.0 AND skipped must stay True: engine.py only reads
    the ratio when `not ph_results.skipped` (engine.py:750), so the skip flag is what
    keeps a fabricated 0.0 out of the temporal boost.
    """

    @pytest.mark.asyncio
    async def test_no_temporal_signal_and_no_token_can_restore_it(self, monkeypatch):
        monkeypatch.setenv("PRODUCTHUNT_TOKEN", "a-real-looking-token")
        result = await search_producthunt(["test query"])

        assert result.skipped is True
        assert result.recent_launch_ratio == 0.0
        assert result.top_products == []


# ===========================================================================
# (d) Score recalibration — log-curve calibration points within ±3
# ===========================================================================


class TestScoreCalibration:
    """Verify continuous log-curve scoring hits documented calibration points."""

    # GitHub repo: 1→10, 50→54, 200→73, 1000→95
    @pytest.mark.parametrize("count,expected", [
        (1, 10), (50, 54), (200, 73), (1000, 95),
    ])
    def test_github_repo_calibration(self, count, expected):
        actual = _github_repo_score(count)
        assert abs(actual - expected) <= 3, (
            f"github_repo_score({count}) = {actual}, expected ~{expected} (±3)"
        )

    # GitHub stars: 10→25, 500→64, 1000→71, 10000→95
    @pytest.mark.parametrize("stars,expected", [
        (10, 25), (500, 64), (1000, 71), (10000, 95),
    ])
    def test_github_star_calibration(self, stars, expected):
        actual = _github_star_score(stars)
        assert abs(actual - expected) <= 3, (
            f"github_star_score({stars}) = {actual}, expected ~{expected} (±3)"
        )

    # HN: 1→14, 15→57, 30→71, 100→95
    @pytest.mark.parametrize("mentions,expected", [
        (1, 14), (15, 57), (30, 71), (100, 95),
    ])
    def test_hn_calibration(self, mentions, expected):
        actual = _hn_score(mentions)
        assert abs(actual - expected) <= 3, (
            f"hn_score({mentions}) = {actual}, expected ~{expected} (±3)"
        )

    # npm: 1→11, 20→47, 100→71, 500→95
    @pytest.mark.parametrize("count,expected", [
        (1, 11), (20, 47), (100, 71), (500, 95),
    ])
    def test_npm_calibration(self, count, expected):
        actual = _npm_score(count)
        assert abs(actual - expected) <= 3, (
            f"npm_score({count}) = {actual}, expected ~{expected} (±3)"
        )

    # PyPI: same curve as npm
    @pytest.mark.parametrize("count,expected", [
        (1, 11), (20, 47), (100, 71), (500, 95),
    ])
    def test_pypi_calibration(self, count, expected):
        actual = _pypi_score(count)
        assert abs(actual - expected) <= 3, (
            f"pypi_score({count}) = {actual}, expected ~{expected} (±3)"
        )

    # PH: 1→14, 10→49, 30→71, 100→95
    @pytest.mark.parametrize("count,expected", [
        (1, 14), (10, 49), (30, 71), (100, 95),
    ])
    def test_ph_calibration(self, count, expected):
        actual = _ph_score(count)
        assert abs(actual - expected) <= 3, (
            f"ph_score({count}) = {actual}, expected ~{expected} (±3)"
        )

    def test_all_zero_inputs(self):
        """All score functions return 0 for count=0."""
        assert _github_repo_score(0) == 0
        assert _github_star_score(0) == 0
        assert _hn_score(0) == 0
        assert _npm_score(0) == 0
        assert _pypi_score(0) == 0
        assert _ph_score(0) == 0

    def test_scores_monotonically_increasing(self):
        """Scores should increase as count increases."""
        for score_fn in [_github_repo_score, _github_star_score, _hn_score,
                         _npm_score, _pypi_score, _ph_score]:
            prev = 0
            for count in [1, 5, 10, 50, 100, 500, 1000]:
                current = score_fn(count)
                assert current >= prev, (
                    f"{score_fn.__name__}({count})={current} < "
                    f"{score_fn.__name__}(prev)={prev}"
                )
                prev = current

    def test_scores_capped_at_100(self):
        """No score function should exceed 100."""
        for score_fn in [_github_repo_score, _github_star_score, _hn_score,
                         _npm_score, _pypi_score, _ph_score]:
            assert score_fn(1_000_000) <= 100


# ===========================================================================
# (e) Temporal boost — momentum > 0.6 positive, < 0.3 negative
# ===========================================================================


class TestTemporalBoostMagnitude:
    def test_high_momentum_positive_boost(self):
        """Momentum > 0.6 should add positive boost to signal."""
        # Use moderate base signal so boost is visible
        base = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(50, 200, recent_ratio=0.5),
            hn_results=_make_hn(5),
            depth="quick",
        )
        high = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(50, 200, recent_ratio=0.8),
            hn_results=_make_hn(5, recent_mention_ratio=0.9),
            depth="quick",
        )
        # momentum = (0.8+0.9)/2 = 0.85 > 0.6 → positive boost
        assert high["sub_scores"]["market_momentum"] == 85
        assert high["reality_signal"] > base["reality_signal"]

    def test_low_momentum_negative_boost(self):
        """Momentum < 0.3 should add negative boost (decrease signal)."""
        base = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(50, 200, recent_ratio=0.5),
            hn_results=_make_hn(5),
            depth="quick",
        )
        low = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(50, 200, recent_ratio=0.1),
            hn_results=_make_hn(5, recent_mention_ratio=0.1),
            depth="quick",
        )
        # momentum = (0.1+0.1)/2 = 0.1 < 0.3 → negative boost
        assert low["sub_scores"]["market_momentum"] == 10
        assert low["reality_signal"] < base["reality_signal"]

    def test_neutral_momentum_no_boost(self):
        """Momentum = 0.5 → boost = 0, signal unchanged."""
        result = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(50, 200, recent_ratio=0.5),
            hn_results=_make_hn(5, recent_mention_ratio=0.5),
            depth="quick",
        )
        # momentum = 0.5 → boost = (0.5 - 0.5) * 20 = 0
        assert result["sub_scores"]["market_momentum"] == 50

    def test_boost_magnitude_calculation(self):
        """Verify boost = (momentum - 0.5) * 20 at known points."""
        # momentum 0.8 → boost = (0.8 - 0.5) * 20 = +6
        high = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(50, 200, recent_ratio=0.8),
            hn_results=_make_hn(5, recent_mention_ratio=0.8),
            depth="quick",
        )
        neutral = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(50, 200, recent_ratio=0.5),
            hn_results=_make_hn(5, recent_mention_ratio=0.5),
            depth="quick",
        )
        # Expected boost delta ≈ 6
        assert abs((high["reality_signal"] - neutral["reality_signal"]) - 6) <= 1

    def test_deep_mode_momentum_includes_ph(self):
        """In deep mode, PH recent_launch_ratio contributes to momentum."""
        result = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(50, 200, recent_ratio=0.4),
            hn_results=_make_hn(5, recent_mention_ratio=0.4),
            depth="deep",
            npm_results=NpmResults(total_count=10, top_packages=[], evidence=[]),
            pypi_results=PyPIResults(total_count=5, top_packages=[], evidence=[]),
            ph_results=ProductHuntResults(
                total_count=8, top_products=[], evidence=[],
                recent_launch_ratio=0.7, skipped=False,
            ),
        )
        # momentum = (0.4 + 0.4 + 0.7) / 3 = 0.5
        assert result["sub_scores"]["market_momentum"] == 50


# ===========================================================================
# (f) Trend label — accelerating/stable/declining boundary thresholds
# ===========================================================================


class TestTrendLabel:
    def test_accelerating_above_0_6(self):
        """Momentum 0.7 > 0.6 → accelerating."""
        result = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(100, 500, recent_ratio=0.7),
            hn_results=_make_hn(10, recent_mention_ratio=0.7),
            depth="quick",
        )
        assert result["trend"] == "accelerating"

    def test_declining_below_0_3(self):
        """Momentum 0.2 < 0.3 → declining."""
        result = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(100, 500, recent_ratio=0.2),
            hn_results=_make_hn(10, recent_mention_ratio=0.2),
            depth="quick",
        )
        assert result["trend"] == "declining"

    def test_stable_at_0_5(self):
        """Momentum 0.5 → stable."""
        result = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(100, 500, recent_ratio=0.5),
            hn_results=_make_hn(10, recent_mention_ratio=0.5),
            depth="quick",
        )
        assert result["trend"] == "stable"

    def test_boundary_exactly_0_6(self):
        """Momentum exactly 0.6 → stable (> 0.6 required for accelerating)."""
        result = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(100, 500, recent_ratio=0.6),
            hn_results=_make_hn(10, recent_mention_ratio=0.6),
            depth="quick",
        )
        assert result["trend"] == "stable"

    def test_boundary_exactly_0_3(self):
        """Momentum exactly 0.3 → stable (< 0.3 required for declining)."""
        result = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(100, 500, recent_ratio=0.3),
            hn_results=_make_hn(10, recent_mention_ratio=0.3),
            depth="quick",
        )
        assert result["trend"] == "stable"

    def test_boundary_just_above_0_6(self):
        """Momentum 0.61 → accelerating."""
        # Use values that average to just above 0.6
        result = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(100, 500, recent_ratio=0.61),
            hn_results=_make_hn(10, recent_mention_ratio=0.61),
            depth="quick",
        )
        assert result["trend"] == "accelerating"

    def test_boundary_just_below_0_3(self):
        """Momentum 0.29 → declining."""
        result = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(100, 500, recent_ratio=0.29),
            hn_results=_make_hn(10, recent_mention_ratio=0.29),
            depth="quick",
        )
        assert result["trend"] == "declining"

    def test_no_temporal_data_defaults_stable(self):
        """No temporal data → momentum 0.5 → stable."""
        result = compute_signal(
            idea_text="xyz",
            keywords=["xyz"],
            github_results=_make_github(),
            hn_results=_make_hn(),
            depth="quick",
        )
        assert result["trend"] == "stable"
        assert result["sub_scores"]["market_momentum"] == 50
