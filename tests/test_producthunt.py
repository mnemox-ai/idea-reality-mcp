"""Tests for the Product Hunt source — which is permanently disabled.

WHAT THESE TESTS USED TO BE, AND WHY IT MATTERS
------------------------------------------------
This file previously held four tests that passed for four months, proving Product Hunt
search worked. It never worked once.

They passed because of this helper::

    def _graphql_response(total, products):
        return {"data": {"posts": {"totalCount": total, "edges": edges}}}

That is a reply Product Hunt cannot give to our query. The query asked for
``posts(search: $query)`` and the live API answers::

    Field 'posts' doesn't accept argument 'search'

So the tests invented the API's response, fed it to the parser, and asserted the parser
could read the invention. The one thing that was broken — the query — was the one thing
the mock replaced. Green tests, dead source, and a README selling it as a feature.

That lesson is worth more than the source ever was: a mock standing in for a call you
have never made against the real service does not test that call, it hides it.

WHAT THEY TEST NOW
------------------
That the source stays skipped no matter what — because a live-but-empty Product Hunt is
worse than an absent one. scoring/engine.py redistributes Product Hunt's 14% deep-mode
weight when ``skipped`` is True, but scores a fabricated "zero competitors found" when
it is False. See sources/producthunt.py for the full autopsy.
"""

from __future__ import annotations

import pytest

from idea_reality_mcp.sources.producthunt import ProductHuntResults, search_producthunt


class TestProductHuntIsDisabled:
    @pytest.mark.asyncio
    async def test_skipped_without_token(self, monkeypatch):
        monkeypatch.delenv("PRODUCTHUNT_TOKEN", raising=False)
        result = await search_producthunt(["test query"])

        assert isinstance(result, ProductHuntResults)
        assert result.skipped is True
        assert result.total_count == 0
        assert result.top_products == []
        assert result.evidence[0]["type"] == "skipped"

    @pytest.mark.asyncio
    async def test_still_skipped_WITH_a_valid_token(self, monkeypatch):
        """The regression that matters — a token must never re-enable this source.

        On 2026-07-17 a real token was set on prod for ~1 hour. The source stopped being
        skipped, the invalid query failed, the exception was swallowed, total_count stayed
        0, and engine.py scored that as "no competitors on Product Hunt" across 14% of the
        deep-mode weight — inflating every idea's originality, silently, with no error.
        """
        monkeypatch.setenv("PRODUCTHUNT_TOKEN", "a-real-looking-token")
        result = await search_producthunt(["mcp server", "idea checker"])

        assert result.skipped is True, (
            "PRODUCTHUNT_TOKEN re-enabled the source. engine.py will now score a "
            "fabricated zero across 14% of deep mode instead of redistributing it."
        )
        assert result.total_count == 0
        assert result.recent_launch_ratio == 0.0

    @pytest.mark.asyncio
    async def test_never_makes_a_network_call(self, monkeypatch):
        monkeypatch.setenv("PRODUCTHUNT_TOKEN", "a-real-looking-token")

        def explode(*args, **kwargs):
            raise AssertionError("Product Hunt must not make network calls while disabled")

        monkeypatch.setattr("idea_reality_mcp.sources.producthunt.httpx.AsyncClient", explode)
        result = await search_producthunt(["anything"])

        assert result.skipped is True

    @pytest.mark.asyncio
    async def test_explains_itself_to_whoever_reads_the_evidence(self):
        """The skip reason must say WHY, or someone sets the token again in six months."""
        result = await search_producthunt(["test"])
        detail = result.evidence[0]["detail"].lower()
        assert "no post text search" in detail
        assert "redistributed" in detail
