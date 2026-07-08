"""AngelRun cross-sell CTA — the idea-reality -> AngelRun funnel.

idea-reality senses demand ("what people want AI to build"); AngelRun is where you
build it in public, climb the season, and get seen by angels. Every reality check is
a moment of intent, so we attach a `next_step` pointing at AngelRun's /new page.

Single source of truth: the REST API (api/main.py), the MCP tool (tools.py), and any
future entry all import `angelrun_next_step` so the copy + UTM tagging stay consistent.
The field is additive — existing clients that ignore `next_step` are unaffected.
"""

from __future__ import annotations

from urllib.parse import urlencode

ANGELRUN_NEW_URL = "https://angelrun.vercel.app/new"

# Keep the label aligned with AngelRun's hero voice ("climb the season", "seen by angels").
_LABEL = "Build this in public on AngelRun — ship updates, climb the season, and get seen by angels."
_CTA = "Open a project"


def angelrun_next_step(idea_text: str, medium: str) -> dict:
    """Build the AngelRun call-to-action attached to a reality check.

    Args:
        idea_text: The user's idea. Passed through (capped) so AngelRun /new can
            prefill the compose box — harmless if the consumer ignores it.
        medium: UTM medium identifying the entry point ("api" | "mcp" | "readme" | "site")
            so we can measure which funnel actually converts.

    Returns:
        ``{"label", "cta", "url"}`` — a small, ignorable hint.
    """
    idea = (idea_text or "").strip()[:200]
    query = {
        "utm_source": "idea-reality",
        "utm_medium": medium,
        "utm_campaign": "demand-cta",
    }
    if idea:
        query["idea"] = idea
    return {
        "label": _LABEL,
        "cta": _CTA,
        "url": f"{ANGELRUN_NEW_URL}?{urlencode(query)}",
    }
