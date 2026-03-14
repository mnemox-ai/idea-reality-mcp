"""Tests for Stack Overflow source adapter."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from idea_reality_mcp.sources.stackoverflow import StackOverflowResults, search_stackoverflow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response."""
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


def _so_item(
    question_id: int,
    title: str = "How to implement X?",
    link: str = "https://stackoverflow.com/questions/1/how-to-implement-x",
    score: int = 10,
    answer_count: int = 3,
    is_answered: bool = True,
    creation_date: int = 1700000000,
    tags: list[str] | None = None,
) -> dict:
    return {
        "question_id": question_id,
        "title": title,
        "link": link,
        "score": score,
        "answer_count": answer_count,
        "is_answered": is_answered,
        "creation_date": creation_date,
        "tags": tags or ["python", "api"],
    }


SAMPLE_ITEMS = [
    _so_item(1, title="How to build a CLI in Python?", score=42, answer_count=5),
    _so_item(2, title="Python CLI argument parsing best practices", score=27, answer_count=3),
    _so_item(3, title="Comparing Python CLI frameworks", score=15, answer_count=2),
]

SAMPLE_RESPONSE = {
    "items": SAMPLE_ITEMS,
    "has_more": False,
    "quota_remaining": 298,
}


# ===========================================================================
# Tests
# ===========================================================================


class TestSearchStackOverflowSuccess:
    @pytest.mark.asyncio
    async def test_basic_success(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(SAMPLE_RESPONSE)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.stackoverflow.httpx.AsyncClient", return_value=mock_client):
            result = await search_stackoverflow(["python cli"])

        assert isinstance(result, StackOverflowResults)
        assert result.total_count == 3
        assert len(result.top_questions) == 3
        assert result.top_questions[0]["title"] == "How to build a CLI in Python?"
        assert result.top_questions[0]["score"] == 42
        assert len(result.evidence) == 1
        assert result.evidence[0]["source"] == "stackoverflow"
        assert result.evidence[0]["type"] == "question_count"
        assert result.evidence[0]["count"] == 3

    @pytest.mark.asyncio
    async def test_has_more_bumps_count(self):
        """When has_more is True, total_count should be pagesize + 1."""
        response_with_more = {
            "items": SAMPLE_ITEMS,
            "has_more": True,
            "quota_remaining": 290,
        }
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(response_with_more)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.stackoverflow.httpx.AsyncClient", return_value=mock_client):
            result = await search_stackoverflow(["python cli"])

        assert result.total_count == 4  # 3 items + 1 for has_more

    @pytest.mark.asyncio
    async def test_top_questions_sorted_by_score(self):
        """top_questions must be sorted by score descending."""
        items = [
            _so_item(10, score=5),
            _so_item(11, score=99),
            _so_item(12, score=30),
        ]
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response({"items": items, "has_more": False})
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.stackoverflow.httpx.AsyncClient", return_value=mock_client):
            result = await search_stackoverflow(["test"])

        scores = [q["score"] for q in result.top_questions]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_api_key_passed_when_env_set(self):
        """STACKEXCHANGE_KEY env var should be included in request params."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(SAMPLE_RESPONSE)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.stackoverflow.httpx.AsyncClient", return_value=mock_client):
            with patch.dict("os.environ", {"STACKEXCHANGE_KEY": "test-api-key"}):
                await search_stackoverflow(["python cli"])

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params", call_kwargs.args[1] if len(call_kwargs.args) > 1 else {})
        assert params.get("key") == "test-api-key"

    @pytest.mark.asyncio
    async def test_no_api_key_when_env_not_set(self):
        """Without STACKEXCHANGE_KEY, key param must not be sent."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response(SAMPLE_RESPONSE)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        import os
        env = {k: v for k, v in os.environ.items() if k != "STACKEXCHANGE_KEY"}

        with patch("idea_reality_mcp.sources.stackoverflow.httpx.AsyncClient", return_value=mock_client):
            with patch.dict("os.environ", env, clear=True):
                await search_stackoverflow(["python cli"])

        call_kwargs = mock_client.get.call_args
        params = call_kwargs.kwargs.get("params", {})
        assert "key" not in params


class TestSearchStackOverflowEmpty:
    @pytest.mark.asyncio
    async def test_empty_results(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response({"items": [], "has_more": False})
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.stackoverflow.httpx.AsyncClient", return_value=mock_client):
            result = await search_stackoverflow(["very obscure topic xyz123"])

        assert isinstance(result, StackOverflowResults)
        assert result.total_count == 0
        assert result.top_questions == []
        assert result.recent_question_ratio is None
        assert len(result.evidence) == 1
        assert result.evidence[0]["count"] == 0


class TestSearchStackOverflowApiError:
    @pytest.mark.asyncio
    async def test_http_error(self):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response({}, status_code=500)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.stackoverflow.httpx.AsyncClient", return_value=mock_client):
            result = await search_stackoverflow(["broken query"])

        assert isinstance(result, StackOverflowResults)
        assert result.total_count == 0
        assert result.top_questions == []
        assert len(result.evidence) == 1
        assert result.evidence[0]["type"] == "error"
        assert "Failed" in result.evidence[0]["detail"]

    @pytest.mark.asyncio
    async def test_returns_results_from_successful_queries_when_one_fails(self):
        """If second keyword fails, results from first keyword are preserved."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = [
            _mock_response(SAMPLE_RESPONSE),
            _mock_response({}, status_code=429),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.stackoverflow.httpx.AsyncClient", return_value=mock_client):
            result = await search_stackoverflow(["kw1", "kw2"])

        assert result.total_count == 3  # from first successful query
        assert len(result.top_questions) == 3
        assert len(result.evidence) == 2
        assert result.evidence[0]["type"] == "question_count"
        assert result.evidence[1]["type"] == "error"


class TestSearchStackOverflowMultipleKeywords:
    @pytest.mark.asyncio
    async def test_dedup_by_question_id(self):
        """Same question_id appearing in multiple keyword queries must be deduplicated."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        # Both keywords return overlapping question_ids 1 and 2, plus unique ones
        items_kw1 = [
            _so_item(1, title="Shared question A", score=50),
            _so_item(2, title="Shared question B", score=30),
            _so_item(3, title="Unique to kw1", score=10),
        ]
        items_kw2 = [
            _so_item(1, title="Shared question A", score=50),  # duplicate
            _so_item(2, title="Shared question B", score=30),  # duplicate
            _so_item(4, title="Unique to kw2", score=20),
        ]
        mock_client.get.side_effect = [
            _mock_response({"items": items_kw1, "has_more": False}),
            _mock_response({"items": items_kw2, "has_more": False}),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.stackoverflow.httpx.AsyncClient", return_value=mock_client):
            result = await search_stackoverflow(["kw1", "kw2"])

        question_ids_in_result = {
            q["title"] for q in result.top_questions
        }
        # All 4 unique questions should be present, not 6
        assert len(result.top_questions) == 4
        assert "Shared question A" in question_ids_in_result
        assert "Shared question B" in question_ids_in_result
        assert "Unique to kw1" in question_ids_in_result
        assert "Unique to kw2" in question_ids_in_result

    @pytest.mark.asyncio
    async def test_max_count_across_keywords(self):
        """total_count should be the max across queries, not the sum."""
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = [
            _mock_response({"items": [_so_item(1)], "has_more": False}),
            _mock_response({"items": [_so_item(2), _so_item(3)], "has_more": False}),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.stackoverflow.httpx.AsyncClient", return_value=mock_client):
            result = await search_stackoverflow(["kw1", "kw2"])

        assert result.total_count == 2  # max(1, 2), not 3

    @pytest.mark.asyncio
    async def test_top_questions_capped_at_five(self):
        """top_questions should contain at most 5 items."""
        items = [_so_item(i, score=100 - i) for i in range(1, 9)]
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response({"items": items, "has_more": False})
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.stackoverflow.httpx.AsyncClient", return_value=mock_client):
            result = await search_stackoverflow(["broad topic"])

        assert len(result.top_questions) == 5

    @pytest.mark.asyncio
    async def test_recent_question_ratio_computed(self):
        """recent_question_ratio should reflect portion of recent questions."""
        import time
        now_ts = int(time.time())
        recent_ts = now_ts - (30 * 24 * 3600)   # 30 days ago — within 3 months
        old_ts = now_ts - (200 * 24 * 3600)     # 200 days ago — outside 3 months

        items = [
            _so_item(1, creation_date=recent_ts),
            _so_item(2, creation_date=recent_ts),
            _so_item(3, creation_date=old_ts),
            _so_item(4, creation_date=old_ts),
        ]
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = _mock_response({"items": items, "has_more": False})
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("idea_reality_mcp.sources.stackoverflow.httpx.AsyncClient", return_value=mock_client):
            result = await search_stackoverflow(["some topic"])

        assert result.recent_question_ratio == pytest.approx(0.5)
