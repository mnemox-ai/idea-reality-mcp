"""Tests for the scoring engine."""

from idea_reality_mcp.scoring.engine import (
    _duplicate_likelihood,
    _github_repo_score,
    _github_star_score,
    _hn_score,
    compute_signal,
    extract_keywords,
)
from idea_reality_mcp.sources.github import GitHubResults
from idea_reality_mcp.sources.hn import HNResults


class TestExtractKeywords:
    def test_returns_three_variants(self):
        result = extract_keywords("AI-powered code review bot for GitHub PRs")
        assert len(result) == 3
        assert all(isinstance(v, str) for v in result)

    def test_removes_stop_words(self):
        result = extract_keywords("a tool for the best code review")
        for variant in result:
            assert "the" not in variant.split()
            assert "for" not in variant.split()

    def test_empty_after_filtering_falls_back(self):
        result = extract_keywords("a the is")
        assert len(result) == 3
        assert all(len(v) > 0 for v in result)

    def test_short_input(self):
        result = extract_keywords("redis")
        assert len(result) == 3


class TestGitHubRepoScore:
    def test_zero(self):
        assert _github_repo_score(0) == 0

    def test_low(self):
        assert _github_repo_score(5) == 20

    def test_medium(self):
        assert _github_repo_score(30) == 40

    def test_high(self):
        assert _github_repo_score(100) == 60

    def test_very_high(self):
        assert _github_repo_score(300) == 75

    def test_max(self):
        assert _github_repo_score(1000) == 90


class TestGitHubStarScore:
    def test_zero(self):
        assert _github_star_score(5) == 0

    def test_low(self):
        assert _github_star_score(50) == 30

    def test_medium(self):
        assert _github_star_score(300) == 50

    def test_high(self):
        assert _github_star_score(800) == 70

    def test_max(self):
        assert _github_star_score(5000) == 90


class TestHNScore:
    def test_zero(self):
        assert _hn_score(0) == 0

    def test_low(self):
        assert _hn_score(3) == 25

    def test_medium(self):
        assert _hn_score(10) == 50

    def test_high(self):
        assert _hn_score(25) == 70

    def test_max(self):
        assert _hn_score(50) == 90


class TestDuplicateLikelihood:
    def test_low(self):
        assert _duplicate_likelihood(10) == "low"

    def test_medium(self):
        assert _duplicate_likelihood(45) == "medium"

    def test_high(self):
        assert _duplicate_likelihood(75) == "high"

    def test_boundary_30(self):
        assert _duplicate_likelihood(30) == "medium"

    def test_boundary_60(self):
        assert _duplicate_likelihood(60) == "medium"


class TestComputeSignal:
    def test_full_output_structure(self):
        github = GitHubResults(
            total_repo_count=150,
            max_stars=2000,
            top_repos=[
                {
                    "name": "user/repo",
                    "url": "https://github.com/user/repo",
                    "stars": 2000,
                    "updated": "2025-01-01T00:00:00Z",
                    "description": "A cool project",
                }
            ],
        )
        hn = HNResults(
            total_mentions=20,
            evidence=[
                {
                    "source": "hackernews",
                    "type": "mention_count",
                    "query": "test",
                    "count": 20,
                    "detail": "20 mentions",
                }
            ],
        )
        result = compute_signal(
            idea_text="test idea",
            keywords=["test", "idea", "test idea"],
            github_results=github,
            hn_results=hn,
            depth="quick",
        )

        assert "reality_signal" in result
        assert 0 <= result["reality_signal"] <= 100
        assert result["duplicate_likelihood"] in ("low", "medium", "high")
        assert isinstance(result["evidence"], list)
        assert isinstance(result["top_similars"], list)
        assert isinstance(result["pivot_hints"], list)
        assert len(result["pivot_hints"]) == 3
        assert result["meta"]["version"] == "0.1.0"
        assert result["meta"]["depth"] == "quick"
        assert "checked_at" in result["meta"]

    def test_zero_signal(self):
        github = GitHubResults(total_repo_count=0, max_stars=0, top_repos=[])
        hn = HNResults(total_mentions=0, evidence=[])
        result = compute_signal(
            idea_text="xyz",
            keywords=["xyz"],
            github_results=github,
            hn_results=hn,
            depth="quick",
        )
        assert result["reality_signal"] == 0
        assert result["duplicate_likelihood"] == "low"

    def test_high_signal(self):
        github = GitHubResults(
            total_repo_count=1000,
            max_stars=50000,
            top_repos=[
                {
                    "name": "big/project",
                    "url": "https://github.com/big/project",
                    "stars": 50000,
                    "updated": "2025-06-01T00:00:00Z",
                    "description": "Huge project",
                }
            ],
        )
        hn = HNResults(
            total_mentions=100,
            evidence=[],
        )
        result = compute_signal(
            idea_text="popular thing",
            keywords=["popular", "thing", "popular thing"],
            github_results=github,
            hn_results=hn,
            depth="quick",
        )
        assert result["reality_signal"] == 90
        assert result["duplicate_likelihood"] == "high"
