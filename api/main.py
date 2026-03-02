"""FastAPI REST wrapper for idea-reality-mcp.

Exposes:
  GET  /health                — liveness probe
  POST /api/check             — idea reality check
  POST /api/extract-keywords  — LLM-powered keyword extraction (rate-limited)
  ANY  /mcp                   — MCP Streamable HTTP transport (for Smithery / MCP clients)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Literal

import httpx

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from idea_reality_mcp.scoring.engine import compute_signal, extract_keywords
from idea_reality_mcp.server import mcp  # registers all tools via server.py
from idea_reality_mcp.sources.github import search_github_repos
from idea_reality_mcp.sources.hn import search_hn
from idea_reality_mcp.sources.npm import search_npm
from idea_reality_mcp.sources.producthunt import search_producthunt
from idea_reality_mcp.sources.pypi import search_pypi

import sys
sys.path.insert(0, os.path.dirname(__file__))
import db as score_db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Discord webhook — passive query intelligence (fire-and-forget, no PII)
# ---------------------------------------------------------------------------

async def _notify_discord(
    idea_text: str,
    keywords: list[str],
    score: int,
    depth: str,
    lang: str,
    keyword_source: str,
    pivot_source: str,
    top_similar: str | None = None,
) -> None:
    """Fire-and-forget Discord webhook notification. Never raises."""
    webhook_url = (os.environ.get("DISCORD_WEBHOOK_URL") or "").strip()
    if not webhook_url:
        logger.info("[DISCORD] skipped — no DISCORD_WEBHOOK_URL")
        return
    try:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        # Truncate idea for readability
        idea_short = idea_text[:120] + ("..." if len(idea_text) > 120 else "")

        embed = {
            "title": f"{'🔴' if score >= 80 else '🟡' if score >= 40 else '🟢'} Signal {score}/100",
            "description": idea_short,
            "color": 0xFF4444 if score >= 80 else 0xFFAA00 if score >= 40 else 0x00CC66,
            "fields": [
                {"name": "Keywords", "value": ", ".join(keywords[:6]), "inline": False},
                {"name": "Depth", "value": depth, "inline": True},
                {"name": "Lang", "value": lang, "inline": True},
                {"name": "KW Source", "value": keyword_source, "inline": True},
                {"name": "Pivot Source", "value": pivot_source, "inline": True},
            ],
            "footer": {"text": ts},
        }
        if top_similar:
            embed["fields"].insert(1, {"name": "Top Competitor", "value": top_similar, "inline": False})

        payload = {"embeds": [embed]}
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(webhook_url, json=payload)
            logger.info("[DISCORD] sent — status %d, idea: %s", resp.status_code, idea_short[:50])
    except Exception:
        logger.warning("[DISCORD] webhook failed (non-fatal)", exc_info=True)


# ---------------------------------------------------------------------------
# MCP HTTP sub-app — must be created BEFORE FastAPI app so lifespan can be passed
# ---------------------------------------------------------------------------

mcp_http = mcp.http_app(path="/mcp", transport="streamable-http", stateless_http=True)

# ---------------------------------------------------------------------------
# App — lifespan=mcp_http.lifespan initialises the MCP task group on startup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="idea-reality-mcp API",
    description="Pre-build reality check for AI coding agents.",
    version="0.4.0",
    lifespan=mcp_http.lifespan,
)

# Initialize DB tables (idempotent — CREATE TABLE IF NOT EXISTS)
score_db.init_db()
score_db.init_subscribers_table()

# CORS — allow GitHub Pages and local dev
ALLOWED_ORIGINS = [
    "https://mnemox.ai",
    "https://www.mnemox.ai",
    "https://mnemox-ai.github.io",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:5500",  # VS Code Live Server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CheckRequest(BaseModel):
    idea_text: str
    depth: Literal["quick", "deep"] = "quick"
    lang: Literal["en", "zh"] = "en"


class ExtractKeywordsRequest(BaseModel):
    idea_text: str


class SubscribeRequest(BaseModel):
    email: str
    idea_hash: str


# ---------------------------------------------------------------------------
# Rate limiter (in-memory, resets on deploy — acceptable for free tier)
# ---------------------------------------------------------------------------

DAILY_LIMIT = 50
_rate_limits: dict[str, dict] = defaultdict(lambda: {"count": 0, "reset_date": ""})


def _check_rate_limit(client_ip: str) -> bool:
    """Return *True* if the request is within the daily limit."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    entry = _rate_limits[client_ip]
    if entry["reset_date"] != today:
        entry["count"] = 0
        entry["reset_date"] = today
    entry["count"] += 1
    return entry["count"] <= DAILY_LIMIT


# ---------------------------------------------------------------------------
# LLM keyword extraction (internal, shared by endpoints)
# ---------------------------------------------------------------------------

_HAIKU_SYSTEM_PROMPT = """You are a search query generator for developer tool market research.

Given a product idea description (English or Chinese), generate 4-6 search queries
optimized for finding similar projects on GitHub, npm, and PyPI.

Rules:
1. Output ONLY a JSON array of strings. No explanation, no markdown.
2. Each query should be 2-5 words.
3. Include queries for: GitHub repo search, npm/PyPI package search, HN discussion search.
4. Use English terms even if input is in Chinese.
5. Prioritize specific technical terms over generic words.
6. Never include: "tool", "app", "platform", "system", "AI", "powered", "smart", "build"."""


async def _extract_keywords_via_haiku(idea_text: str) -> list[str] | None:
    """Call Claude Haiku 4.5 to extract search keywords.

    Returns a list of keyword strings, or *None* on any failure.
    Requires ``ANTHROPIC_API_KEY`` environment variable.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=200,
            system=_HAIKU_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": idea_text}],
        )

        raw = message.content[0].text.strip()

        # Strip markdown code fences if present (e.g. ```json ... ```)
        if raw.startswith("```"):
            lines = raw.split("\n")
            # Remove first line (```json) and last line (```)
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            raw = "\n".join(lines).strip()

        keywords = json.loads(raw)

        if not isinstance(keywords, list) or len(keywords) < 2:
            return None

        cleaned = [str(k).strip() for k in keywords if str(k).strip()]
        if len(cleaned) < 2:
            return None

        return cleaned[:8]

    except Exception:
        logger.exception("Haiku keyword extraction failed")
        return None


# ---------------------------------------------------------------------------
# LLM pivot hints (replaces template hints with data-driven suggestions)
# ---------------------------------------------------------------------------

_PIVOT_SYSTEM_PROMPT = """You are a startup advisor analyzing real market competition data.
Given an idea and actual search results from GitHub/HN/npm/PyPI, generate 3 specific,
actionable pivot suggestions.

Rules:
- Reference actual competitor names and their star counts from the data provided
- Suggest specific gaps or underserved niches based on the evidence
- Be concrete, not generic. NEVER say "consider differentiating" or "explore niche opportunities"
- Each suggestion should be 1-2 sentences, actionable, and reference real data
- If lang=zh, respond entirely in Traditional Chinese (繁體中文)
- Output ONLY a JSON array of exactly 3 strings. No markdown, no explanation, no code fences."""


async def _generate_pivot_hints_llm(
    idea_text: str,
    reality_signal: int,
    top_similars: list[dict],
    evidence: list[dict],
    lang: str = "en",
) -> list[str] | None:
    """Generate pivot hints via Claude Haiku using real search data.

    Returns a list of 3 hint strings, or *None* on any failure.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("[PIVOT] skipped — no ANTHROPIC_API_KEY")
        return None

    logger.info("[PIVOT] LLM attempt for: %s (signal=%d, lang=%s)", idea_text[:60], reality_signal, lang)

    # Build competitor summary (top 3)
    competitors = []
    for s in top_similars[:3]:
        stars = f", {s['stars']} stars" if s.get("stars") else ""
        desc = f" — {s['description']}" if s.get("description") else ""
        competitors.append(f"- {s['name']}{stars}{desc}")
    competitors_text = "\n".join(competitors) if competitors else "(none found)"

    # Build evidence summary
    ev_lines = []
    for e in evidence:
        ev_lines.append(f"- [{e.get('source', '?')}] {e.get('detail', e.get('type', ''))}")
    evidence_text = "\n".join(ev_lines[:8]) if ev_lines else "(no evidence)"

    user_prompt = f"""Idea: {idea_text}
Reality Signal: {reality_signal}/100 (higher = more competition)
Lang: {lang}

Top Competitors:
{competitors_text}

Evidence:
{evidence_text}"""

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=500,
            system=_PIVOT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = message.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            raw = "\n".join(lines).strip()

        hints = json.loads(raw)

        if not isinstance(hints, list) or len(hints) < 2:
            logger.warning("[PIVOT] LLM returned invalid list (len=%d): %s", len(hints) if isinstance(hints, list) else -1, raw[:100])
            return None

        result_hints = [str(h).strip() for h in hints[:3]]
        logger.info("[PIVOT] LLM success — %d hints generated", len(result_hints))
        return result_hints

    except json.JSONDecodeError:
        logger.warning("[PIVOT] LLM returned non-JSON: %s", raw[:200])
        return None
    except Exception:
        logger.exception("[PIVOT] LLM call failed")
        return None


# ---------------------------------------------------------------------------
# Routes — MUST be defined BEFORE app.mount("/", mcp_http)
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Liveness probe — called by /check page on load."""
    return {"status": "ok"}


@app.post("/api/extract-keywords")
async def extract_keywords_endpoint(req: ExtractKeywordsRequest, request: Request):
    """LLM-powered keyword extraction via Claude Haiku 4.5.

    Body: { "idea_text": "..." }
    Returns: { "keywords": ["query1", "query2", ...] }

    Rate-limited to 50 requests per IP per day.
    """
    if not req.idea_text or not req.idea_text.strip():
        raise HTTPException(status_code=422, detail="idea_text cannot be empty")

    # Check ANTHROPIC_API_KEY availability
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="LLM extraction not available")

    # Rate limit
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Daily rate limit exceeded (50/day)")

    keywords = await _extract_keywords_via_haiku(req.idea_text.strip())
    if keywords is None:
        raise HTTPException(status_code=502, detail="LLM extraction failed")

    return {"keywords": keywords}


@app.post("/api/check")
async def check(req: CheckRequest):
    """Run an idea reality check.

    Body: { "idea_text": "...", "depth": "quick" | "deep" }
    Returns the full reality check report dict.
    """
    if not req.idea_text or not req.idea_text.strip():
        raise HTTPException(status_code=422, detail="idea_text cannot be empty")

    idea_text = req.idea_text.strip()

    # Try LLM keywords first (no rate limit for /api/check — internal usage)
    keyword_source = "llm"
    keywords = await _extract_keywords_via_haiku(idea_text)
    if keywords is None:
        keyword_source = "dictionary"
        keywords = extract_keywords(idea_text)

    try:
        if req.depth == "deep":
            (
                github_results,
                hn_results,
                npm_results,
                pypi_results,
                ph_results,
            ) = await asyncio.gather(
                search_github_repos(keywords),
                search_hn(keywords),
                search_npm(keywords),
                search_pypi(keywords),
                search_producthunt(keywords),
            )
            result = compute_signal(
                idea_text=idea_text,
                keywords=keywords,
                github_results=github_results,
                hn_results=hn_results,
                depth=req.depth,
                npm_results=npm_results,
                pypi_results=pypi_results,
                ph_results=ph_results,
            )
        else:
            # Quick mode: GitHub + HN only
            github_results, hn_results = await asyncio.gather(
                search_github_repos(keywords),
                search_hn(keywords),
            )
            result = compute_signal(
                idea_text=idea_text,
                keywords=keywords,
                github_results=github_results,
                hn_results=hn_results,
                depth=req.depth,
            )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    result["meta"]["keyword_source"] = keyword_source
    result["meta"]["lang"] = req.lang

    # LLM pivot hints — replace template hints with data-driven suggestions
    pivot_source = "template"
    llm_hints = await _generate_pivot_hints_llm(
        idea_text=idea_text,
        reality_signal=result["reality_signal"],
        top_similars=result.get("top_similars", []),
        evidence=result.get("evidence", []),
        lang=req.lang,
    )
    if llm_hints:
        result["pivot_hints"] = llm_hints
        pivot_source = "llm"
    result["meta"]["pivot_source"] = pivot_source

    # Always include idea_hash (needed for subscribe flow)
    result["idea_hash"] = score_db.idea_hash(idea_text)

    # Save to score history
    try:
        score_db.save_score(
            idea_text=idea_text,
            score=result["reality_signal"],
            breakdown=json.dumps(result),
            keywords=json.dumps(keywords),
            depth=req.depth,
            keyword_source=keyword_source,
        )
    except Exception:
        logger.exception("Failed to save score history")
        # Non-fatal — still return the result

    # Discord webhook — query intelligence (no PII, 5s timeout, non-fatal)
    top_sim_name = None
    if result.get("top_similars"):
        ts = result["top_similars"][0]
        stars_str = f" ({ts['stars']}★)" if ts.get("stars") else ""
        top_sim_name = f"{ts['name']}{stars_str}"
    await _notify_discord(
        idea_text=idea_text,
        keywords=keywords,
        score=result["reality_signal"],
        depth=req.depth,
        lang=req.lang,
        keyword_source=keyword_source,
        pivot_source=pivot_source,
        top_similar=top_sim_name,
    )

    return result


@app.get("/api/history/{idea_hash}")
async def get_history(idea_hash: str):
    """Get score history for an idea by its hash."""
    records = score_db.get_history(idea_hash)
    if not records:
        raise HTTPException(status_code=404, detail="No history found for this idea")
    return {"idea_hash": idea_hash, "records": records}


@app.post("/api/subscribe")
async def subscribe(req: SubscribeRequest, request: Request):
    """Save email for pivot hints unlock. No email validation (MVP).

    Body: { "email": "user@example.com", "idea_hash": "sha256..." }
    Returns: { "unlocked": true }
    """
    if not req.email or not req.email.strip() or "@" not in req.email:
        raise HTTPException(status_code=422, detail="Invalid email")

    # Rate limit (shared with extract-keywords: 50/IP/day)
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    try:
        score_db.save_subscriber(req.email.strip(), req.idea_hash)
    except Exception:
        logger.exception("Failed to save subscriber")
        raise HTTPException(status_code=500, detail="Subscribe failed")

    return {"unlocked": True}


@app.get("/api/subscribers/count")
async def subscribers_count():
    """Return total subscriber count (for internal monitoring)."""
    try:
        count = score_db.get_subscriber_count()
    except Exception:
        count = 0
    return {"count": count}


@app.get("/api/export")
async def export_scores(key: str = ""):
    """Export all score history as JSON (requires secret key).

    Usage: GET /api/export?key=YOUR_SECRET
    Returns: { "count": N, "records": [...] }

    Set EXPORT_KEY env var on Render. No key = endpoint disabled.
    """
    export_key = (os.environ.get("EXPORT_KEY") or "").strip()
    if not export_key or key != export_key:
        raise HTTPException(status_code=403, detail="Invalid or missing export key")
    try:
        records = score_db.get_all_scores()
    except Exception:
        logger.exception("Export failed")
        raise HTTPException(status_code=500, detail="Export failed")
    return {"count": len(records), "records": records}


# ---------------------------------------------------------------------------
# Mount MCP Streamable HTTP at /mcp
# Enables Smithery and MCP HTTP clients to connect via:
#   https://idea-reality-mcp.onrender.com/mcp
# ---------------------------------------------------------------------------

app.mount("/", mcp_http)
