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


# ===========================================================================
# Score function tests
# ===========================================================================


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


class TestNpmScore:
    def test_zero(self):
        assert _npm_score(0) == 0

    def test_low(self):
        assert _npm_score(3) == 15

    def test_medium(self):
        assert _npm_score(50) == 55

    def test_high(self):
        assert _npm_score(200) == 75

    def test_max(self):
        assert _npm_score(1000) == 90


class TestPyPIScore:
    def test_zero(self):
        assert _pypi_score(0) == 0

    def test_low(self):
        assert _pypi_score(3) == 15

    def test_medium(self):
        assert _pypi_score(50) == 55

    def test_high(self):
        assert _pypi_score(200) == 75

    def test_max(self):
        assert _pypi_score(1000) == 90


class TestPHScore:
    def test_zero(self):
        assert _ph_score(0) == 0

    def test_low(self):
        assert _ph_score(2) == 20

    def test_medium(self):
        assert _ph_score(20) == 60

    def test_high(self):
        assert _ph_score(50) == 80

    def test_max(self):
        assert _ph_score(200) == 90


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


def _make_github(count: int = 0, stars: int = 0) -> GitHubResults:
    repos = []
    if count > 0:
        repos = [{
            "name": "user/repo",
            "url": "https://github.com/user/repo",
            "stars": stars,
            "updated": "2025-01-01T00:00:00Z",
            "description": "A project",
        }]
    return GitHubResults(total_repo_count=count, max_stars=stars, top_repos=repos)


def _make_hn(mentions: int = 0) -> HNResults:
    evidence = []
    if mentions > 0:
        evidence = [{
            "source": "hackernews",
            "type": "mention_count",
            "query": "test",
            "count": mentions,
            "detail": f"{mentions} mentions",
        }]
    return HNResults(total_mentions=mentions, evidence=evidence)


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
        assert result["meta"]["version"] == "0.3.1"
        assert result["meta"]["depth"] == "quick"
        assert result["meta"]["sources_used"] == ["github", "hackernews"]
        assert "checked_at" in result["meta"]

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
        assert result["reality_signal"] == 90
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
