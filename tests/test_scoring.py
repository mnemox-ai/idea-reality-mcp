"""Tests for the scoring engine."""

from idea_reality_mcp.scoring.engine import (
    COMPOUND_TERMS,
    TECH_KEYWORDS,
    _duplicate_likelihood,
    _github_repo_score,
    _github_star_score,
    _hn_score,
    _npm_score,
    _pypi_score,
    _ph_score,
    compute_signal,
    extract_keywords,
)
from idea_reality_mcp.scoring.synonyms import INTENT_ANCHORS, SYNONYMS
from idea_reality_mcp.sources.github import GitHubResults
from idea_reality_mcp.sources.hn import HNResults
from idea_reality_mcp.sources.npm import NpmResults
from idea_reality_mcp.sources.pypi import PyPIResults
from idea_reality_mcp.sources.producthunt import ProductHuntResults


# ===========================================================================
# Keyword extraction tests (v0.3 Stage A/B/C pipeline)
# ===========================================================================


class TestExtractKeywords:
    # ---- Basic contract ----

    def test_returns_at_least_three_variants(self):
        result = extract_keywords("AI-powered code review bot for GitHub PRs")
        assert len(result) >= 3
        assert all(isinstance(v, str) for v in result)

    def test_returns_at_most_eight_variants(self):
        result = extract_keywords("LLM monitoring observability tracing evaluation pipeline agent")
        assert len(result) <= 8

    def test_removes_stop_words(self):
        result = extract_keywords("a tool for the best code review")
        for variant in result:
            assert "the" not in variant.split()
            assert "for" not in variant.split()

    def test_empty_after_filtering_falls_back(self):
        result = extract_keywords("a the is")
        assert len(result) >= 3
        assert all(len(v) > 0 for v in result)

    def test_short_input(self):
        result = extract_keywords("redis")
        assert len(result) >= 3

    # ---- Stage A: Boilerplate filter ----

    def test_boilerplate_ai_filtered(self):
        """'ai' alone should not dominate queries (Stage A hard filter)."""
        result = extract_keywords("an AI tool for monitoring")
        all_text = " ".join(result)
        # "monitoring" must appear — "ai" and "tool" should be filtered
        assert "monitoring" in all_text

    def test_boilerplate_tool_filtered(self):
        result = extract_keywords("LLM evaluation tool platform")
        all_text = " ".join(result)
        assert "evaluation" in all_text
        # boilerplate words should not be the only content
        for variant in result:
            assert variant.strip() not in ("tool", "platform", "ai", "system")

    def test_boilerplate_platform_system_filtered(self):
        result = extract_keywords("monitoring platform system for agents")
        all_text = " ".join(result)
        # intent anchor should dominate
        assert "monitoring" in all_text or "agent" in all_text

    def test_generic_words_filtered(self):
        result = extract_keywords("build an application platform tool")
        for variant in result:
            words = variant.split()
            assert "build" not in words or len(words) > 1

    def test_tech_keywords_bypass_boilerplate_filter(self):
        """Tech keywords like 'cli', 'mcp', 'api' must never be filtered."""
        result = extract_keywords("mcp server tool")
        all_text = " ".join(result)
        assert "mcp" in all_text

    # ---- Stage A: Compound terms ----

    def test_compound_terms_preserved(self):
        result = extract_keywords("build a machine learning web app")
        assert any("machine learning" in v for v in result)

    def test_model_context_protocol_compound(self):
        result = extract_keywords("model context protocol server for code review")
        all_text = " ".join(result)
        assert "model context protocol" in all_text or "mcp" in all_text

    def test_tech_keywords_prioritised(self):
        result = extract_keywords("build a dashboard with react and postgres")
        all_text = " ".join(result)
        assert "react" in all_text or "postgres" in all_text

    # ---- Stage B: Intent anchor detection ----

    def test_monitoring_anchor_detected(self):
        result = extract_keywords("LLM monitoring and alerting for production")
        all_text = " ".join(result)
        assert "monitoring" in all_text or "observability" in all_text

    def test_evaluation_anchor_detected(self):
        result = extract_keywords("LLM evaluation and benchmarking framework")
        all_text = " ".join(result)
        assert "evaluation" in all_text or "evals" in all_text or "benchmark" in all_text

    def test_agent_anchor_detected(self):
        result = extract_keywords("autonomous agent workflow orchestration for coding tasks")
        all_text = " ".join(result)
        assert "agent" in all_text or "workflow" in all_text or "orchestration" in all_text

    def test_mcp_anchor_detected(self):
        result = extract_keywords("MCP server for GitHub integration")
        all_text = " ".join(result)
        assert "mcp" in all_text

    def test_rag_anchor_detected(self):
        result = extract_keywords("RAG pipeline with vector search and reranking")
        all_text = " ".join(result)
        assert "rag" in all_text or "retrieval" in all_text or "vector" in all_text

    def test_cli_anchor_detected(self):
        result = extract_keywords("CLI tool for database migrations")
        all_text = " ".join(result)
        assert "cli" in all_text or "command line" in all_text or "terminal" in all_text

    # ---- Stage C: Synonym expansion ----

    def test_monitoring_expands_to_observability(self):
        result = extract_keywords("LLM monitoring dashboard")
        all_text = " ".join(result)
        # At least one synonym should appear
        assert any(s in all_text for s in ["observability", "tracing", "telemetry"])

    def test_evaluation_expands_to_evals(self):
        result = extract_keywords("LLM evaluation framework")
        all_text = " ".join(result)
        assert any(s in all_text for s in ["evals", "benchmark", "scoring"])

    def test_rag_expands_synonyms(self):
        result = extract_keywords("RAG system for documentation")
        all_text = " ".join(result)
        assert any(s in all_text for s in ["retrieval", "embedding", "vector"])

    def test_agent_expands_synonyms(self):
        result = extract_keywords("AI agent for task automation")
        all_text = " ".join(result)
        assert any(s in all_text for s in ["workflow", "orchestration", "tool calling", "agentic"])

    # ---- Stage A: Chinese/mixed input ----

    def test_chinese_monitoring_mapped(self):
        result = extract_keywords("LLM 監控 dashboard")
        all_text = " ".join(result)
        assert "monitoring" in all_text

    def test_chinese_evaluation_mapped(self):
        result = extract_keywords("大模型 評測 工具")
        all_text = " ".join(result)
        # "llm" maps from 大模型, "evaluation" from 評測
        assert "evaluation" in all_text or "evals" in all_text

    def test_chinese_scraping_mapped(self):
        result = extract_keywords("Python 爬蟲 框架")
        all_text = " ".join(result)
        assert "scraping" in all_text or "crawler" in all_text or "python" in all_text

    def test_mixed_chinese_english_stable(self):
        """Same idea run twice should produce consistent results."""
        idea = "MCP server 監控 LLM calls"
        r1 = extract_keywords(idea)
        r2 = extract_keywords(idea)
        assert r1 == r2

    # ---- Stage A: Non-tech domain mappings (v0.3.1) ----

    def test_chinese_tcm_mapped(self):
        """中醫 should produce TCM-related queries."""
        result = extract_keywords("中醫針灸穴位查詢")
        all_text = " ".join(result)
        assert "tcm" in all_text
        assert "acupuncture" in all_text

    def test_chinese_legal_document_mapped(self):
        """法律文件 should include 'document' in queries (v0.3.1 fix)."""
        result = extract_keywords("法律文件自動分析")
        all_text = " ".join(result)
        assert "legal" in all_text
        assert "document" in all_text

    def test_chinese_agriculture_mapped(self):
        result = extract_keywords("農業灌溉智慧系統")
        all_text = " ".join(result)
        assert "agriculture" in all_text
        assert "irrigation" in all_text

    def test_chinese_analysis_mapped(self):
        """分析 should map to 'analysis' (not 'analytics') for general use."""
        result = extract_keywords("法律文件自動分析")
        all_text = " ".join(result)
        assert "analysis" in all_text

    def test_chinese_data_analytics_compound(self):
        """數據分析 (compound) should map to 'data analytics' for BI context."""
        result = extract_keywords("數據分析儀表板")
        all_text = " ".join(result)
        assert "data analytics" in all_text or "analytics" in all_text

    def test_chinese_buddhism_scripture_mapped(self):
        result = extract_keywords("佛教經文搜尋 app")
        all_text = " ".join(result)
        assert "buddhism" in all_text
        assert "scripture" in all_text

    def test_chinese_pet_health_mapped(self):
        result = extract_keywords("寵物健康追蹤")
        all_text = " ".join(result)
        assert "pet" in all_text
        assert "health" in all_text

    def test_chinese_consultation_mapped(self):
        """問診 should map to 'consultation'."""
        result = extract_keywords("中醫問診 AI 助手")
        all_text = " ".join(result)
        assert "consultation" in all_text

    def test_domain_first_query_generated(self):
        """Non-tech domains should have a domain-first query variant."""
        result = extract_keywords("法律文件自動分析")
        # At least one query should start with a domain noun, not the anchor verb
        assert any(q.startswith("legal") for q in result)

    # ---- Registry variant ----

    def test_registry_variant_for_tech(self):
        result = extract_keywords("a python fastapi rest api service")
        assert len(result) <= 8
        assert any("python" in v or "fastapi" in v for v in result)

    # ---- Stage B: Event / social planning anchors (v0.5.1) ----

    def test_reunion_anchor_detected(self):
        """Reunion ideas must not be hijacked by incidental workflow/payment words."""
        result = extract_keywords(
            "A reunion planner for friend groups with rotating host and date poll"
        )
        all_text = " ".join(result)
        assert "reunion" in all_text
        # No incidental-word hijack: the primary query must not lead with workflow
        assert not result[0].startswith("workflow ")
        assert not result[0].startswith("payment ")

    def test_event_anchor_detected(self):
        result = extract_keywords("Event planning app for community meetups")
        all_text = " ".join(result)
        assert "event" in all_text or "meetup" in all_text or "gathering" in all_text

    def test_rsvp_anchor_detected(self):
        result = extract_keywords("RSVP tracker for small private events")
        all_text = " ".join(result)
        assert "rsvp" in all_text or "invitation" in all_text or "attendance" in all_text

    def test_poll_anchor_detected(self):
        result = extract_keywords("Poll app for scheduling group dinners")
        all_text = " ".join(result)
        assert "poll" in all_text or "voting" in all_text

    def test_negated_payment_does_not_hijack(self):
        """'no payment processing' must not anchor the query on payment (regression).

        Before v0.5.1, any INTENT_ANCHOR in the first sentence dominated even when
        negated. With reunion/event anchors added, a reunion idea that mentions
        'no payment processing' gets a reunion-anchored primary query instead.
        """
        result = extract_keywords(
            "A reunion and event planner for friend groups. Features include rsvp, "
            "date poll, attendance tracking, and host election — no payment processing."
        )
        assert not result[0].startswith("payment ")
        assert "reunion" in " ".join(result) or "event" in " ".join(result)

    # ---- Stage C: Event / social planning synonym expansion ----

    def test_reunion_expands_synonyms(self):
        result = extract_keywords("reunion planner for alumni groups")
        all_text = " ".join(result)
        assert any(
            s in all_text
            for s in ["alumni reunion", "gathering", "meetup", "class reunion"]
        )

    def test_event_expands_synonyms(self):
        result = extract_keywords("Event app with rsvp and itinerary")
        all_text = " ".join(result)
        assert any(s in all_text for s in ["gathering", "meetup", "party", "function"])

    # ---- Stage A: Chinese event-planning mappings (v0.5.1) ----

    def test_chinese_reunion_mapped(self):
        """同學會 should map to alumni reunion (not lost to ASCII stripping)."""
        result = extract_keywords("同學會 聚會 輪流主辦 app")
        all_text = " ".join(result)
        assert "alumni" in all_text or "reunion" in all_text
        assert "rotating" in all_text or "host" in all_text

    def test_chinese_gathering_mapped(self):
        result = extract_keywords("家族聚會規劃工具 投票 出席")
        all_text = " ".join(result)
        assert "family reunion" in all_text or "gathering" in all_text
        assert "voting" in all_text or "attendance" in all_text

    def test_chinese_rsvp_mapped(self):
        result = extract_keywords("活動邀請 出席回覆 紀錄")
        all_text = " ".join(result)
        assert "event" in all_text or "invitation" in all_text

    def test_compound_chinese_host_rotation(self):
        """輪流主辦 (longer compound) must be matched before 主辦 alone."""
        result = extract_keywords("聚會輪流主辦系統")
        all_text = " ".join(result)
        assert "rotating host" in all_text or "rotating" in all_text


# ===========================================================================
# Score function tests
# ===========================================================================


class TestGitHubRepoScore:
    def test_zero(self):
        assert _github_repo_score(0) == 0

    def test_low(self):
        assert _github_repo_score(5) == 25

    def test_medium(self):
        assert _github_repo_score(30) == 47

    def test_high(self):
        assert _github_repo_score(100) == 63

    def test_very_high(self):
        assert _github_repo_score(300) == 78

    def test_max(self):
        assert _github_repo_score(1000) == 95


class TestGitHubStarScore:
    def test_zero(self):
        assert _github_star_score(5) == 18

    def test_low(self):
        assert _github_star_score(50) == 41

    def test_medium(self):
        assert _github_star_score(300) == 59

    def test_high(self):
        assert _github_star_score(800) == 69

    def test_max(self):
        assert _github_star_score(5000) == 88


class TestHNScore:
    def test_zero(self):
        assert _hn_score(0) == 0

    def test_low(self):
        assert _hn_score(3) == 29

    def test_medium(self):
        assert _hn_score(10) == 49

    def test_high(self):
        assert _hn_score(25) == 67

    def test_max(self):
        assert _hn_score(50) == 81


class TestNpmScore:
    def test_zero(self):
        assert _npm_score(0) == 0

    def test_low(self):
        assert _npm_score(3) == 21

    def test_medium(self):
        assert _npm_score(50) == 60

    def test_high(self):
        assert _npm_score(200) == 81

    def test_max(self):
        assert _npm_score(1000) == 100


class TestPyPIScore:
    def test_zero(self):
        assert _pypi_score(0) == 0

    def test_low(self):
        assert _pypi_score(3) == 21

    def test_medium(self):
        assert _pypi_score(50) == 60

    def test_high(self):
        assert _pypi_score(200) == 81

    def test_max(self):
        assert _pypi_score(1000) == 100


class TestPHScore:
    def test_zero(self):
        assert _ph_score(0) == 0

    def test_low(self):
        assert _ph_score(2) == 23

    def test_medium(self):
        assert _ph_score(20) == 63

    def test_high(self):
        assert _ph_score(50) == 81

    def test_max(self):
        assert _ph_score(200) == 100


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


# ===========================================================================
# compute_signal tests
# ===========================================================================


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


class TestComputeSignalQuick:
    def test_full_output_structure(self):
        result = compute_signal(
            idea_text="test idea",
            keywords=["test", "idea", "test idea"],
            github_results=_make_github(150, 2000),
            hn_results=_make_hn(20),
            depth="quick",
        )

        assert "reality_signal" in result
        assert 0 <= result["reality_signal"] <= 100
        assert result["duplicate_likelihood"] in ("low", "medium", "high")
        assert isinstance(result["evidence"], list)
        assert isinstance(result["top_similars"], list)
        assert isinstance(result["pivot_hints"], list)
        assert len(result["pivot_hints"]) == 3
        assert result["meta"]["version"] == "0.5.1"
        assert result["meta"]["depth"] == "quick"
        assert result["meta"]["sources_used"] == ["github", "hackernews"]
        assert "checked_at" in result["meta"]
        # Temporal fields
        assert "market_momentum" in result["sub_scores"]
        assert 0 <= result["sub_scores"]["market_momentum"] <= 100
        assert result["trend"] in ("accelerating", "declining", "stable")

    def test_zero_signal(self):
        result = compute_signal(
            idea_text="xyz",
            keywords=["xyz"],
            github_results=_make_github(),
            hn_results=_make_hn(),
            depth="quick",
        )
        assert result["reality_signal"] == 0
        assert result["duplicate_likelihood"] == "low"

    def test_high_signal(self):
        result = compute_signal(
            idea_text="popular thing",
            keywords=["popular", "thing", "popular thing"],
            github_results=_make_github(1000, 50000),
            hn_results=_make_hn(100),
            depth="quick",
        )
        assert result["reality_signal"] == 96
        assert result["duplicate_likelihood"] == "high"


class TestComputeSignalDeep:
    def test_deep_mode_with_all_sources(self):
        result = compute_signal(
            idea_text="test idea",
            keywords=["test", "idea", "test idea"],
            github_results=_make_github(100, 500),
            hn_results=_make_hn(10),
            depth="deep",
            npm_results=NpmResults(total_count=50, top_packages=[{
                "name": "test-pkg",
                "url": "https://npmjs.com/package/test-pkg",
                "version": "1.0.0",
                "description": "Test package",
                "score": 0.8,
            }], evidence=[]),
            pypi_results=PyPIResults(total_count=20, top_packages=[{
                "name": "test-pkg",
                "url": "https://pypi.org/project/test-pkg/",
                "version": "1.0.0",
                "description": "Test package",
            }], evidence=[]),
            ph_results=ProductHuntResults(
                total_count=5, top_products=[], evidence=[], skipped=False,
            ),
        )

        assert 0 <= result["reality_signal"] <= 100
        assert result["meta"]["depth"] == "deep"
        assert "npm" in result["meta"]["sources_used"]
        assert "pypi" in result["meta"]["sources_used"]
        assert "producthunt" in result["meta"]["sources_used"]

    def test_deep_mode_ph_skipped_redistributes_weight(self):
        result = compute_signal(
            idea_text="test idea",
            keywords=["test", "idea", "test idea"],
            github_results=_make_github(100, 500),
            hn_results=_make_hn(10),
            depth="deep",
            npm_results=NpmResults(total_count=50, top_packages=[], evidence=[]),
            pypi_results=PyPIResults(total_count=20, top_packages=[], evidence=[]),
            ph_results=ProductHuntResults(skipped=True, evidence=[{
                "source": "producthunt",
                "type": "skipped",
                "query": "",
                "count": 0,
                "detail": "Skipped",
            }]),
        )

        assert 0 <= result["reality_signal"] <= 100
        assert "producthunt" not in result["meta"]["sources_used"]
        assert any(e["source"] == "producthunt" for e in result["evidence"])

    def test_deep_mode_top_similars_includes_npm_pypi(self):
        result = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(10, 100),
            hn_results=_make_hn(5),
            depth="deep",
            npm_results=NpmResults(total_count=5, top_packages=[{
                "name": "npm-pkg",
                "url": "https://npmjs.com/package/npm-pkg",
                "version": "1.0.0",
                "description": "NPM package",
                "score": 0.5,
            }], evidence=[]),
            pypi_results=PyPIResults(total_count=3, top_packages=[{
                "name": "pypi-pkg",
                "url": "https://pypi.org/project/pypi-pkg/",
                "version": "0.1.0",
                "description": "PyPI package",
            }], evidence=[]),
        )

        names = [s["name"] for s in result["top_similars"]]
        assert any(n.startswith("npm:") for n in names)
        assert any(n.startswith("pypi:") for n in names)


# ===========================================================================
# Temporal boost tests
# ===========================================================================


class TestTemporalBoost:
    def test_accelerating_trend(self):
        """High recent_ratio → accelerating trend, positive boost."""
        result = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(100, 500, recent_ratio=0.8),
            hn_results=_make_hn(10, recent_mention_ratio=0.9),
            depth="quick",
        )
        assert result["trend"] == "accelerating"
        assert result["sub_scores"]["market_momentum"] == 85  # (0.8+0.9)/2=0.85

    def test_declining_trend(self):
        """Low recent_ratio → declining trend, negative boost."""
        result = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(100, 500, recent_ratio=0.1),
            hn_results=_make_hn(10, recent_mention_ratio=0.1),
            depth="quick",
        )
        assert result["trend"] == "declining"
        assert result["sub_scores"]["market_momentum"] == 10

    def test_stable_trend(self):
        """Mid-range ratios → stable trend."""
        result = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(100, 500, recent_ratio=0.5),
            hn_results=_make_hn(10, recent_mention_ratio=0.4),
            depth="quick",
        )
        assert result["trend"] == "stable"
        assert result["sub_scores"]["market_momentum"] == 45

    def test_boost_increases_signal(self):
        """High momentum should increase signal vs neutral."""
        neutral = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(50, 200, recent_ratio=0.5),
            hn_results=_make_hn(5),
            depth="quick",
        )
        boosted = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(50, 200, recent_ratio=1.0),
            hn_results=_make_hn(5, recent_mention_ratio=1.0),
            depth="quick",
        )
        assert boosted["reality_signal"] > neutral["reality_signal"]

    def test_boost_decreases_signal(self):
        """Low momentum should decrease signal vs neutral."""
        neutral = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(50, 200, recent_ratio=0.5),
            hn_results=_make_hn(5),
            depth="quick",
        )
        dampened = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(50, 200, recent_ratio=0.0),
            hn_results=_make_hn(5, recent_mention_ratio=0.0),
            depth="quick",
        )
        assert dampened["reality_signal"] < neutral["reality_signal"]

    def test_no_temporal_data_neutral(self):
        """No sources with data → momentum 0.5, no boost."""
        result = compute_signal(
            idea_text="xyz",
            keywords=["xyz"],
            github_results=_make_github(),  # count=0, skipped
            hn_results=_make_hn(),  # no recent_mention_ratio
            depth="quick",
        )
        assert result["sub_scores"]["market_momentum"] == 50
        assert result["trend"] == "stable"

    def test_temporal_evidence_present(self):
        """Temporal evidence entries added when data available."""
        result = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(100, 500, recent_ratio=0.7),
            hn_results=_make_hn(10, recent_mention_ratio=0.6),
            depth="quick",
        )
        types = [e["type"] for e in result["evidence"]]
        assert "recent_ratio" in types
        assert "recent_mention_ratio" in types

    def test_deep_mode_ph_temporal(self):
        """PH recent_launch_ratio included in deep mode."""
        result = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(100, 500, recent_ratio=0.5),
            hn_results=_make_hn(10),
            depth="deep",
            npm_results=NpmResults(total_count=10, top_packages=[], evidence=[]),
            pypi_results=PyPIResults(total_count=5, top_packages=[], evidence=[]),
            ph_results=ProductHuntResults(
                total_count=8, top_products=[], evidence=[],
                recent_launch_ratio=0.9, skipped=False,
            ),
        )
        # momentum = (0.5 + 0.9) / 2 = 0.7 (HN has no ratio)
        assert result["sub_scores"]["market_momentum"] == 70
        assert result["trend"] == "accelerating"
        types = [e["type"] for e in result["evidence"]]
        assert "recent_launch_ratio" in types

    def test_boost_clamped_at_zero(self):
        """Signal can't go below 0 with negative boost."""
        result = compute_signal(
            idea_text="xyz",
            keywords=["xyz"],
            github_results=_make_github(1, 0, recent_ratio=0.0),
            hn_results=_make_hn(0, recent_mention_ratio=0.0),
            depth="quick",
        )
        assert result["reality_signal"] >= 0

    def test_boost_clamped_at_100(self):
        """Signal can't exceed 100 with positive boost."""
        result = compute_signal(
            idea_text="test",
            keywords=["test"],
            github_results=_make_github(1000, 50000, recent_ratio=1.0),
            hn_results=_make_hn(100, recent_mention_ratio=1.0),
            depth="quick",
        )
        assert result["reality_signal"] <= 100


class TestKeywordSynonymExpansion:
    """Verify dictionary extraction produces search-friendly queries for common ideas."""

    def test_todo_generates_task_manager_query(self):
        """'todo list app' must produce at least one query containing 'task manager'."""
        result = extract_keywords("todo list app")
        all_text = " ".join(result).lower()
        assert "task manager" in all_text or "checklist" in all_text or "to-do" in all_text

    def test_expense_generates_budget_query(self):
        result = extract_keywords("expense tracker app")
        all_text = " ".join(result).lower()
        assert "budget" in all_text or "finance" in all_text or "money" in all_text

    def test_chat_generates_messaging_query(self):
        result = extract_keywords("chat application")
        all_text = " ".join(result).lower()
        assert "messaging" in all_text or "real-time chat" in all_text

    def test_synonym_expansion_respects_8_query_cap(self):
        result = extract_keywords("todo list productivity checklist task manager")
        assert len(result) <= 8


class TestPyPIWeightRedistribution:
    """Verify PyPI weight is redistributed when skipped."""

    def test_pypi_skipped_redistributes_weight_to_increase_score(self):
        """When PyPI is skipped, its 13% weight goes to sources with data -> higher score."""
        github = GitHubResults(
            total_repo_count=100, max_stars=1000, top_repos=[],
            recent_ratio=0.3, recently_updated_ratio=0.5, recent_created_count=30,
        )
        hn = HNResults(total_mentions=50, evidence=[], recent_mention_ratio=0.4)
        npm = NpmResults(total_count=100, top_packages=[], evidence=[])

        # PyPI skipped: its 13% weight redistributed to GitHub/HN/npm (which have data)
        pypi_skipped = PyPIResults(total_count=0, skipped=True, evidence=[])
        result_skipped = compute_signal(
            idea_text="test", keywords=["test"], github_results=github,
            hn_results=hn, depth="deep", npm_results=npm, pypi_results=pypi_skipped,
        )

        # PyPI NOT skipped: 13% weight x score(0) = 0 contribution, dilutes total
        pypi_zero = PyPIResults(total_count=0, skipped=False, evidence=[])
        result_zero = compute_signal(
            idea_text="test", keywords=["test"], github_results=github,
            hn_results=hn, depth="deep", npm_results=npm, pypi_results=pypi_zero,
        )

        # With redistribution, score should be HIGHER because PyPI's zero-weight
        # goes to sources that have data (GitHub=100, HN=50, npm=100)
        assert result_skipped["reality_signal"] >= result_zero["reality_signal"]
        assert 0 <= result_skipped["reality_signal"] <= 100

    def test_pypi_skipped_not_in_sources_used(self):
        github = GitHubResults(
            total_repo_count=10, max_stars=100, top_repos=[],
            recent_ratio=0.5, recently_updated_ratio=0.5, recent_created_count=5,
        )
        hn = HNResults(total_mentions=5, evidence=[], recent_mention_ratio=0.5)
        npm = NpmResults(total_count=10, top_packages=[], evidence=[])
        pypi_skipped = PyPIResults(total_count=0, skipped=True, evidence=[])

        result = compute_signal(
            idea_text="test", keywords=["test"], github_results=github,
            hn_results=hn, depth="deep", npm_results=npm, pypi_results=pypi_skipped,
        )

        assert "pypi" not in result["meta"]["sources_used"]
