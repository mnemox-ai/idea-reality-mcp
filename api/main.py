"""FastAPI REST wrapper for idea-reality-mcp.

Exposes:
  GET  /health                — liveness probe
  POST /api/check             — idea reality check
  POST /api/extract-keywords  — LLM-powered keyword extraction (rate-limited)
  ANY  /mcp                   — MCP Streamable HTTP transport (for Smithery / MCP clients)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time as _time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Literal

import httpx

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from html import escape as html_escape

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
import report as report_mod
import lemon_utils

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GitHub stars — cached fetch (1-hour TTL)
# ---------------------------------------------------------------------------
_github_stars_cache = {"value": 290, "fetched_at": 0}


async def _get_github_stars():
    """Fetch GitHub stars with 1-hour cache."""
    now = _time.time()
    if now - _github_stars_cache["fetched_at"] < 3600:
        return _github_stars_cache["value"]
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                "https://api.github.com/repos/mnemox-ai/idea-reality-mcp",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            if resp.status_code == 200:
                _github_stars_cache["value"] = resp.json().get(
                    "stargazers_count", 290
                )
                _github_stars_cache["fetched_at"] = now
    except Exception:
        pass
    return _github_stars_cache["value"]


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
score_db.init_db()  # creates all tables: score_history, query_log, reports, page_views, subscribers

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


class CheckoutRequest(BaseModel):
    idea_text: str
    idea_hash: str
    language: Literal["en", "zh"] = "en"
    depth: Literal["quick", "deep"] = "quick"
    success_url: str
    tier: Literal["single", "pro"] = "single"


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
# Accept-Language country extraction
# ---------------------------------------------------------------------------

_LANG_TO_COUNTRY: dict[str, str] = {
    "en": "US", "zh": "CN", "ja": "JP", "ko": "KR", "de": "DE",
    "fr": "FR", "es": "ES", "pt": "BR", "ru": "RU", "it": "IT",
    "nl": "NL", "sv": "SE", "pl": "PL", "ar": "SA", "hi": "IN",
    "th": "TH", "vi": "VN", "tr": "TR", "uk": "UA", "cs": "CZ",
    "ro": "RO", "id": "ID", "ms": "MY",
}


def _extract_country(request: Request) -> str | None:
    """Best-effort country code from Accept-Language header."""
    raw = request.headers.get("accept-language", "")
    if not raw:
        return None
    first = raw.split(",")[0].strip().split(";")[0].strip()
    if not first:
        return None
    if "-" in first:
        return first.split("-", 1)[1].upper()
    return _LANG_TO_COUNTRY.get(first.lower())


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


@app.get("/api/stats")
async def get_stats():
    """Public stats for the /check hero section."""
    total = score_db.get_total_checks()
    last_check = score_db.get_last_check_time()
    unique_countries = score_db.get_unique_countries()
    return {
        "total_ideas_scanned": total,
        "sources_count": 5,
        "last_updated": last_check or datetime.now(timezone.utc).isoformat(),
        "unique_countries": unique_countries,
    }


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
async def check(req: CheckRequest, request: Request):
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
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.") from exc

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

    # Save query log (SHA256 hashed IP, no PII)
    try:
        client_ip = request.client.host if request.client else "unknown"
        ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()
        country = _extract_country(request)
        score_db.save_query_log(
            ip_hash=ip_hash,
            idea_hash=result["idea_hash"],
            depth=req.depth,
            score=result["reality_signal"],
            country=country,
        )
    except Exception:
        logger.exception("Failed to save query log")

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


@app.get("/api/query-stats")
async def query_stats():
    """Return query usage stats (total queries, unique IPs, return rate)."""
    try:
        stats = score_db.get_query_stats()
    except Exception:
        logger.exception("Failed to get query stats")
        raise HTTPException(status_code=500, detail="Stats unavailable")
    return stats


class PageViewRequest(BaseModel):
    page: str


@app.post("/api/view")
async def record_page_view(req: PageViewRequest):
    """Record a page view.

    Body: { "page": "report" }
    """
    if not req.page or not req.page.strip():
        raise HTTPException(status_code=422, detail="page cannot be empty")
    try:
        score_db.save_page_view(req.page.strip())
    except Exception:
        logger.exception("Failed to save page view")
    return {"ok": True}


@app.get("/api/social-proof")
async def social_proof():
    """Return social proof stats for the landing page."""
    total_checks = 0
    last_check_ago = None
    try:
        total_checks = score_db.get_total_checks()
        last_check_ts = score_db.get_last_check_time()
        if last_check_ts:
            last_dt = datetime.fromisoformat(last_check_ts)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - last_dt
            secs = int(delta.total_seconds())
            if secs < 60:
                last_check_ago = f"{secs}s ago"
            elif secs < 3600:
                last_check_ago = f"{secs // 60}m ago"
            elif secs < 86400:
                last_check_ago = f"{secs // 3600}h ago"
            else:
                last_check_ago = f"{secs // 86400}d ago"
    except Exception:
        logger.exception("Failed to get social proof stats")
    return {
        "total_checks": total_checks,
        "github_stars": await _get_github_stars(),
        "countries": "30+",
        "last_check_ago": last_check_ago,
    }


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


_SOURCE_COLORS = {
    "github": "#00cc66",
    "hackernews": "#ff6600",
    "npm": "#cb3837",
    "pypi": "#3775a9",
    "producthunt": "#da552f",
}


def _build_report_html(record: dict, report_id: str) -> str:
    """Build a self-contained dark-theme HTML report for download."""
    report_data = record.get("report_data", {})
    if isinstance(report_data, str):
        try:
            report_data = json.loads(report_data)
        except (json.JSONDecodeError, TypeError):
            report_data = {}

    report = report_data.get("report", report_data)
    score_breakdown = report.get("score_breakdown", {})
    crowd = report.get("crowd_intelligence", {})
    competitors = report.get("competitors", [])
    strategic = report.get("strategic_analysis", "")
    score = record.get("score", 0)
    idea_text = record.get("idea_text", "")
    sub_scores = report.get("sub_scores", {})
    search_angles = report.get("search_angles", [])
    verified_at = report.get("verified_at", record.get("created_at", ""))
    evidence = report_data.get("evidence", report.get("evidence", []))
    if isinstance(evidence, str):
        try:
            evidence = json.loads(evidence)
        except (json.JSONDecodeError, TypeError):
            evidence = []

    # Score circle color
    if score >= 70:
        score_color = "#ff4444"
    elif score >= 40:
        score_color = "#ff9800"
    else:
        score_color = "#00b4ff"

    # Duplicate likelihood styling
    dup = score_breakdown.get("duplicate_likelihood", "unknown")
    dup_colors = {"high": "#ff4444", "medium": "#ff9800", "low": "#00b4ff"}
    dup_color = dup_colors.get(dup, "#888")

    # --- Section: Sub-Dimension Scores bars ---
    _SUB_LABELS = {
        "competition_density": "Competition Density",
        "market_maturity": "Market Maturity",
        "community_buzz": "Community Buzz",
        "ecosystem_depth": "Ecosystem Depth",
    }
    _SUB_EXPLAIN = {
        "competition_density": "GitHub repos found",
        "market_maturity": "Top project star count",
        "community_buzz": "HN + Product Hunt mentions",
        "ecosystem_depth": "npm + PyPI packages",
    }
    # Compute ecosystem_depth as max of npm/pypi if available
    eco_npm = sub_scores.get("ecosystem_depth_npm")
    eco_pypi = sub_scores.get("ecosystem_depth_pypi")
    eco_parts = [v for v in [eco_npm, eco_pypi] if v is not None]
    ecosystem_depth = max(eco_parts) if eco_parts else None
    merged_sub = {
        "competition_density": sub_scores.get("competition_density"),
        "market_maturity": sub_scores.get("market_maturity"),
        "community_buzz": sub_scores.get("community_buzz"),
        "ecosystem_depth": ecosystem_depth,
    }

    sub_bars_html = ""
    for key in ["competition_density", "market_maturity", "community_buzz", "ecosystem_depth"]:
        val = merged_sub.get(key)
        if val is None:
            continue
        pct = min(int(val), 100)
        label = _SUB_LABELS[key]
        explain = _SUB_EXPLAIN[key]
        sub_bars_html += (
            f'<div class="sub-row">'
            f'<span class="sub-label">{label}</span>'
            f'<div class="sub-track"><div class="sub-fill" style="width:{pct}%"></div></div>'
            f'<span class="sub-val">{pct}</span>'
            f'<span class="sub-explain">{explain}</span>'
            f'</div>'
        )
    if not sub_bars_html:
        sub_bars_html = '<p class="empty">Sub-dimension data not available.</p>'

    # --- Section: Search Angles ---
    angles_html = ""
    if search_angles:
        for i, angle in enumerate(search_angles, 1):
            angles_html += f'<li>{html_escape(angle)}</li>'
        angles_html = f'<ol class="angles-list">{angles_html}</ol>'

    # --- Section: Crowd Intelligence ---
    crowd_msg = html_escape(crowd.get("message", "No similar queries found."))

    # --- Section: Competitors (up to 15) ---
    comp_html = ""
    for c in competitors[:15]:
        activity = c.get("activity", {})
        badge = activity.get("badge", "")
        label = activity.get("label", "")
        days = activity.get("days_since_update")
        days_str = f" &middot; Updated {days}d ago" if days is not None else ""
        lang = c.get("language", "")
        lang_tag = f'<span class="lang-tag">{html_escape(lang)}</span>' if lang else ""
        url = c.get("url", "")
        name = html_escape(c.get("name", ""))
        desc = html_escape(c.get("description", ""))
        stars_val = c.get("stars", 0)
        found_via = c.get("found_via_angles", [])
        via_html = ""
        if found_via:
            via_tags = " ".join(
                f'<span class="angle-tag">{html_escape(a)}</span>' for a in found_via
            )
            via_html = f'<div class="comp-via">Found via: {via_tags}</div>'
        comp_html += (
            f'<div class="comp">'
            f'<div class="comp-header">'
            f'<span class="badge">{badge}</span> '
            f'<a href="{html_escape(url)}" class="comp-name">{name}</a>'
            f'<span class="comp-stars">{stars_val:,} stars</span>'
            f'{lang_tag}'
            f'</div>'
            f'<p class="comp-desc">{desc}</p>'
            f'{via_html}'
            f'<span class="comp-meta">{html_escape(label.capitalize())}{days_str}</span>'
            f'</div>'
        )
    if not comp_html:
        comp_html = '<p class="empty">No competitors found.</p>'

    # --- Section: Strategic Analysis ---
    strat_html = ""
    if strategic:
        for p in strategic.split("\n\n"):
            p = p.strip()
            if p:
                strat_html += f"<p>{html_escape(p)}</p>"
    else:
        strat_html = "<p>Strategic analysis not available.</p>"

    # --- Section: Source Evidence ---
    evidence_html = ""
    if isinstance(evidence, list) and evidence:
        for ev in evidence:
            if isinstance(ev, dict):
                src = html_escape(ev.get("source", "unknown"))
                desc = html_escape(ev.get("description", str(ev.get("detail", ""))))
                evidence_html += f'<div class="ev-item"><span class="ev-src">[{src}]</span> {desc}</div>'
            elif isinstance(ev, str):
                evidence_html += f'<div class="ev-item">{html_escape(ev)}</div>'
        if verified_at:
            evidence_html += f'<div class="ev-ts">All data verified: {html_escape(verified_at)}</div>'
    else:
        evidence_html = '<p class="empty">No evidence data available.</p>'

    # --- Section: AI Prompt (copyable) ---
    # Build Markdown-formatted summary for AI agents
    sub_lines = ""
    for key in ["competition_density", "market_maturity", "community_buzz", "ecosystem_depth"]:
        val = merged_sub.get(key)
        if val is not None:
            sub_lines += f"- {_SUB_LABELS[key]}: {val}/100 — {_SUB_EXPLAIN[key]}\n"

    angles_md = ""
    if search_angles:
        for i, a in enumerate(search_angles, 1):
            angles_md += f'{i}. "{a}"\n'

    comp_table = "| # | Project | Stars | Language | Activity | Found Via |\n"
    comp_table += "|---|---------|-------|----------|----------|----------|\n"
    for i, c in enumerate(competitors[:15], 1):
        c_name = c.get("name", "")
        c_stars = f'{c.get("stars", 0):,}'
        c_lang = c.get("language", "")
        c_act = c.get("activity", {}).get("label", "")
        c_days = c.get("activity", {}).get("days_since_update")
        c_act_str = f"{c_act} ({c_days}d)" if c_days is not None else c_act
        c_via = ", ".join(c.get("found_via_angles", []))
        comp_table += f"| {i} | {c_name} | {c_stars} | {c_lang} | {c_act_str} | {c_via} |\n"

    crowd_md = crowd.get("message", "No similar queries found.")
    analysis_md = strategic if strategic else "Not available."

    ai_prompt_text = (
        f"## Verified Market Intelligence Report\n"
        f"> Generated by Mnemox Idea Reality · {verified_at} · All data verified from live APIs\n\n"
        f"### Idea: {idea_text}\n\n"
        f"### Overall Score: {score}/100 — {dup} duplicate likelihood\n\n"
        f"### Sub-Dimension Scores\n{sub_lines}\n"
        f"### Search Angles Used\n{angles_md}\n"
        f"### Top Competitors\n{comp_table}\n"
        f"### Crowd Intelligence\n{crowd_md}\n\n"
        f"### Strategic Analysis\n{analysis_md}\n\n"
        f"---\n"
        f"Based on this verified market data, help me create a product positioning plan "
        f"that addresses the gaps in the competitive landscape."
    )

    timestamp_display = verified_at[:10] if verified_at and len(verified_at) >= 10 else record.get("created_at", "")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Idea Reality Report — {html_escape(idea_text[:60])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&family=JetBrains+Mono&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{
  font-family:'Outfit',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  background:#04060b;color:#e0e0e8;line-height:1.7;
  max-width:800px;margin:0 auto;padding:48px 32px;
}}
a{{color:#00b4ff;text-decoration:none}}
a:hover{{text-decoration:underline}}
.brand{{text-align:center;margin-bottom:40px}}
.brand h1{{font-size:24px;font-weight:700;color:#fff;letter-spacing:2px}}
.brand h1 span{{color:#00b4ff}}
.brand .rid{{color:#6a6a80;font-size:12px;margin-top:4px}}
.idea-card{{
  background:#0b1120;border:1px solid #1a1a28;border-radius:8px;
  padding:16px 20px;margin:24px 0;
}}
.idea-label{{font-size:11px;color:#6a6a80;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}}
.idea-text{{font-size:15px;color:#ccc}}
.score-section{{text-align:center;margin:32px 0}}
.score-circle{{
  width:120px;height:120px;border-radius:50%;
  border:4px solid {score_color};
  display:inline-flex;align-items:center;justify-content:center;
  flex-direction:column;
}}
.score-num{{font-size:40px;font-weight:800;color:{score_color};line-height:1}}
.score-sub{{font-size:12px;color:#6a6a80}}
.dup-badge{{
  display:inline-block;margin-top:12px;padding:4px 14px;
  border-radius:20px;font-size:12px;font-weight:600;
  background:{dup_color}22;color:{dup_color};border:1px solid {dup_color}44;
}}
h2{{
  font-size:16px;font-weight:700;color:#00b4ff;
  margin:36px 0 16px;padding-bottom:8px;
  border-bottom:1px solid #1a1a28;text-transform:uppercase;letter-spacing:1px;
}}
.section{{background:#0b1120;border:1px solid #1a1a28;border-radius:8px;padding:20px;margin-bottom:20px}}
.sub-row{{display:flex;align-items:center;gap:10px;margin:10px 0}}
.sub-label{{width:160px;font-size:13px;color:#ccc}}
.sub-track{{flex:1;height:12px;background:#1a1a28;border-radius:6px;overflow:hidden}}
.sub-fill{{height:100%;border-radius:6px;background:#00b4ff}}
.sub-val{{width:30px;font-size:13px;font-weight:700;color:#fff;text-align:right}}
.sub-explain{{font-size:11px;color:#6a6a80;min-width:120px}}
.angles-list{{margin:0;padding-left:24px;font-size:14px;color:#ccc}}
.angles-list li{{margin:4px 0}}
.comp{{background:#080e1a;border:1px solid #1a1a28;border-radius:8px;padding:14px 16px;margin:10px 0}}
.comp-header{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.badge{{font-size:16px}}
.comp-name{{font-weight:600;color:#00b4ff;font-size:14px}}
.comp-stars{{font-size:12px;color:#6a6a80}}
.lang-tag{{font-size:11px;color:#aaa;background:#1a1a28;padding:2px 8px;border-radius:10px}}
.comp-desc{{font-size:13px;color:#999;margin:6px 0 4px;line-height:1.5}}
.comp-via{{font-size:11px;color:#555;margin:4px 0}}
.angle-tag{{
  display:inline-block;background:#00b4ff15;color:#00b4ff;
  padding:1px 8px;border-radius:10px;font-size:10px;margin:0 3px;
  border:1px solid #00b4ff33;
}}
.comp-meta{{font-size:11px;color:#6a6a80}}
.strat p{{margin-bottom:16px;font-size:14px;color:#ccc}}
.crowd-msg{{font-size:14px;color:#ccc}}
.ev-item{{font-size:13px;color:#999;margin:6px 0;font-family:'JetBrains Mono',monospace}}
.ev-src{{color:#00b4ff;font-weight:600}}
.ev-ts{{margin-top:12px;font-size:12px;color:#6a6a80;font-style:italic}}
.empty{{color:#6a6a80;font-style:italic}}
.ai-section{{background:#080e1a;border:1px solid #1a1a28;border-radius:8px;padding:20px;margin-bottom:20px}}
.ai-explain{{font-size:13px;color:#999;margin-bottom:12px;line-height:1.6}}
.ai-prompt{{
  background:#0b1120;border:1px solid #1a1a28;border-radius:6px;
  padding:16px;font-size:12px;color:#ccc;
  white-space:pre-wrap;word-wrap:break-word;
  max-height:400px;overflow-y:auto;line-height:1.5;
}}
.copy-btn{{
  display:inline-block;margin-top:12px;padding:8px 20px;
  background:#00b4ff;color:#04060b;border:none;border-radius:6px;
  font-size:13px;font-weight:600;cursor:pointer;
}}
.copy-btn:hover{{background:#0099dd}}
.footer{{
  margin-top:48px;padding-top:20px;border-top:1px solid #1a1a28;
  text-align:center;color:#6a6a80;font-size:11px;
}}
.footer a{{color:#00b4ff}}
</style>
</head>
<body>

<div class="brand">
  <h1><span>MNEMOX</span> IDEA REALITY</h1>
  <div class="rid">Full Intelligence Report &middot; ID: {html_escape(report_id[:8])} &middot; {html_escape(timestamp_display)}</div>
</div>

<div class="idea-card">
  <div class="idea-label">Idea</div>
  <div class="idea-text">{html_escape(idea_text)}</div>
</div>

<div class="score-section">
  <div class="score-circle">
    <span class="score-num">{score}</span>
    <span class="score-sub">/ 100</span>
  </div>
  <div><span class="dup-badge">Duplicate likelihood: {html_escape(dup)}</span></div>
</div>

<h2>Sub-Dimension Scores</h2>
<div class="section">
  {sub_bars_html}
</div>

{"<h2>Search Angles</h2><div class='section'>" + angles_html + "</div>" if angles_html else ""}

<h2>Crowd Intelligence</h2>
<div class="section">
  <p class="crowd-msg">{crowd_msg}</p>
</div>

<h2>Real Competitors ({len(competitors[:15])})</h2>
<div class="section">
  {comp_html}
</div>

<h2>Strategic Analysis</h2>
<div class="section strat">
  {strat_html}
</div>

<h2>Source Evidence</h2>
<div class="section">
  {evidence_html}
</div>

<h2>How to Use This Report with AI</h2>
<div class="ai-section">
  <p class="ai-explain">
    Copy the text below and paste it to your AI coding agent (Claude, ChatGPT, Cursor, etc.)
    to generate an action plan for your product.
  </p>
  <pre class="ai-prompt" id="ai-prompt">{html_escape(ai_prompt_text)}</pre>
  <button class="copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('ai-prompt').textContent).then(function(){{var b=event.target;b.textContent='Copied!';setTimeout(function(){{b.textContent='Copy to Clipboard'}},2000)}})">Copy to Clipboard</button>
</div>

<div class="footer">
  <a href="https://idea-reality-mcp.onrender.com">Mnemox Idea Reality</a>
  &middot; Report {html_escape(report_id[:8])}
  &middot; {html_escape(timestamp_display)}
</div>

</body>
</html>"""


@app.get("/report/{report_id}/pdf")
async def report_pdf(report_id: str):
    """Download report as self-contained HTML file."""
    record = score_db.get_report(report_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Report not found")

    html_content = _build_report_html(record, report_id)

    return HTMLResponse(
        content=html_content,
        headers={
            "Content-Disposition": f'attachment; filename="idea-reality-report-{report_id[:8]}.html"',
        },
    )


@app.get("/report/{report_id}/json")
async def report_json(report_id: str):
    """Download report as machine-readable JSON."""
    record = score_db.get_report(report_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Report not found")

    report_data = record.get("report_data", {})
    if isinstance(report_data, str):
        try:
            report_data = json.loads(report_data)
        except (json.JSONDecodeError, TypeError):
            report_data = {}

    report = report_data.get("report", report_data)

    return JSONResponse(
        content={
            "report_id": report_id,
            "idea_text": record.get("idea_text", ""),
            "score": record.get("score", 0),
            "sub_scores": report.get("sub_scores", {}),
            "search_angles": report.get("search_angles", []),
            "score_breakdown": report.get("score_breakdown", {}),
            "crowd_intelligence": report.get("crowd_intelligence", {}),
            "competitors": report.get("competitors", []),
            "strategic_analysis": report.get("strategic_analysis", ""),
            "verified_at": report.get("verified_at", record.get("created_at", "")),
            "created_at": record.get("created_at", ""),
        },
        headers={
            "Content-Disposition": f'attachment; filename="idea-reality-{report_id[:8]}.json"',
        },
    )


@app.post("/report/{report_id}/translate")
async def translate_report(report_id: str, lang: str = "en"):
    """Re-generate strategic analysis in a different language.

    NOTE: Language switching is deprioritized for V1.0. This endpoint is
    kept as a stub but returns 501 until the feature is implemented.
    """
    raise HTTPException(status_code=501, detail="Language switching not yet available")


@app.get("/report/{report_id}")
async def get_report(report_id: str):
    """Retrieve a saved report by ID.

    Returns the full report JSON, or 404 if not found.
    """
    record = score_db.get_report(report_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Report not found")
    # Parse report_data back to dict if stored as JSON string
    if isinstance(record.get("report_data"), str):
        try:
            record["report_data"] = json.loads(record["report_data"])
        except (json.JSONDecodeError, TypeError):
            pass
    return record


class ReportPreviewRequest(BaseModel):
    idea_text: str
    depth: Literal["quick", "deep"] = "quick"


@app.post("/api/report/preview")
async def report_preview(req: ReportPreviewRequest, request: Request):
    """Run compute_signal but return blurred preview — section titles + first 50 chars only.

    Body: { "idea_text": "...", "depth": "quick" | "deep" }
    """
    if not req.idea_text or not req.idea_text.strip():
        raise HTTPException(status_code=422, detail="idea_text cannot be empty")

    idea_text = req.idea_text.strip()
    keywords = extract_keywords(idea_text)

    try:
        if req.depth == "deep":
            github_results, hn_results, npm_results, pypi_results, ph_results = (
                await asyncio.gather(
                    search_github_repos(keywords),
                    search_hn(keywords),
                    search_npm(keywords),
                    search_pypi(keywords),
                    search_producthunt(keywords),
                )
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
        raise HTTPException(status_code=500, detail="An internal error occurred. Please try again.") from exc

    # Build blurred preview: reality_signal is visible, sections show title + first 50 chars
    preview: dict = {
        "reality_signal": result["reality_signal"],
        "duplicate_likelihood": result.get("duplicate_likelihood"),
        "idea_hash": score_db.idea_hash(idea_text),
        "preview": True,
    }

    # Blur evidence — show type/source + truncated detail
    if result.get("evidence"):
        preview["evidence"] = [
            {
                "type": e.get("type", ""),
                "source": e.get("source", ""),
                "detail": (e.get("detail", "") or "")[:50] + "...",
            }
            for e in result["evidence"]
        ]

    # Blur top_similars — show name only, truncate description
    if result.get("top_similars"):
        preview["top_similars"] = [
            {
                "name": s.get("name", ""),
                "description": (s.get("description", "") or "")[:50] + "...",
            }
            for s in result["top_similars"]
        ]

    # Blur pivot_hints — first 50 chars each
    if result.get("pivot_hints"):
        preview["pivot_hints"] = [
            hint[:50] + "..." for hint in result["pivot_hints"]
        ]

    return preview


# ---------------------------------------------------------------------------
# LemonSqueezy payment endpoints
# ---------------------------------------------------------------------------

@app.post("/api/create-checkout")
async def create_checkout(req: CheckoutRequest):
    """Create a LemonSqueezy checkout for a paid report.

    Body: { "idea_text": "...", "idea_hash": "...", "language": "en",
            "success_url": "https://..." }
    Returns: { "checkout_url": "https://mnemox-ai.lemonsqueezy.com/checkout/..." }
    """
    if not lemon_utils._get_api_key():
        raise HTTPException(status_code=503, detail="LemonSqueezy is not configured")

    if not req.idea_text or not req.idea_text.strip():
        raise HTTPException(status_code=422, detail="idea_text cannot be empty")

    try:
        url = await lemon_utils.create_checkout(
            idea_text=req.idea_text.strip(),
            idea_hash=req.idea_hash,
            language=req.language,
            success_url=req.success_url,
            depth=req.depth,
            tier=req.tier,
        )
    except Exception as exc:
        logger.exception("LemonSqueezy checkout creation failed")
        raise HTTPException(status_code=502, detail="Payment service unavailable. Please try again.") from exc

    return {"checkout_url": url}


@app.post("/api/lemon-webhook")
async def lemon_webhook(request: Request):
    """Handle LemonSqueezy webhook events.

    On order_created:
      1. Extract idea_text from custom data
      2. Run compute_signal + generate_report
      3. Save report to DB with buyer_email
    """
    if not lemon_utils._get_webhook_secret():
        raise HTTPException(status_code=503, detail="LemonSqueezy webhook is not configured")

    payload = await request.body()
    signature = request.headers.get("x-signature", "")

    try:
        event = lemon_utils.verify_webhook(payload, signature)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid request.")

    event_name = event.get("meta", {}).get("event_name", "")

    if event_name == "order_created":
        attrs = event.get("data", {}).get("attributes", {})
        custom_data = event.get("meta", {}).get("custom_data", {})
        idea_text = custom_data.get("idea_text", "")
        idea_hash_val = custom_data.get("idea_hash", "")
        language = custom_data.get("language", "en")
        depth = custom_data.get("depth", "quick")
        tier = custom_data.get("tier", "single")
        buyer_email = attrs.get("user_email", "")
        order_id = str(event.get("data", {}).get("id", ""))

        # Idempotency check — skip if this order was already processed
        existing = score_db.get_report_by_stripe_session(order_id)
        if existing:
            logger.info("[WEBHOOK] Duplicate webhook for order %s, skipping", order_id)
            return {"status": "already_processed"}

        if idea_text:
            try:
                keywords = await _extract_keywords_via_haiku(idea_text)
                keyword_source = "llm"
                if keywords is None:
                    keywords = extract_keywords(idea_text)
                    keyword_source = "dictionary"
                if depth == "deep":
                    github_results, hn_results, npm_results, pypi_results, ph_results = (
                        await asyncio.gather(
                            search_github_repos(keywords),
                            search_hn(keywords),
                            search_npm(keywords),
                            search_pypi(keywords),
                            search_producthunt(keywords),
                        )
                    )
                    signal_result = compute_signal(
                        idea_text=idea_text,
                        keywords=keywords,
                        github_results=github_results,
                        hn_results=hn_results,
                        depth="deep",
                        npm_results=npm_results,
                        pypi_results=pypi_results,
                        ph_results=ph_results,
                    )
                else:
                    github_results, hn_results = await asyncio.gather(
                        search_github_repos(keywords),
                        search_hn(keywords),
                    )
                    signal_result = compute_signal(
                        idea_text=idea_text,
                        keywords=keywords,
                        github_results=github_results,
                        hn_results=hn_results,
                        depth="quick",
                    )

                full_report = await report_mod.generate_report(
                    idea_text=idea_text,
                    signal_result=signal_result,
                    language=language,
                    tier=tier,
                )

                report_data = {**signal_result, "report": full_report, "keyword_source": keyword_source}

                report_id = str(uuid.uuid4())
                score_db.save_report(
                    report_id=report_id,
                    idea_text=idea_text,
                    idea_hash=idea_hash_val or score_db.idea_hash(idea_text),
                    score=signal_result["reality_signal"],
                    report_data=json.dumps(report_data),
                    language=language,
                    stripe_session_id=order_id,  # reuse column for LemonSqueezy order ID
                    buyer_email=buyer_email,
                )
                logger.info(
                    "[LEMON] Report saved: report_id=%s, email=%s, score=%d, keywords=%s",
                    report_id, buyer_email, signal_result["reality_signal"], keyword_source,
                )
            except Exception:
                logger.exception("[LEMON] Failed to generate/save report for order %s", order_id)

    return {"received": True}


async def _generate_report_on_the_fly(
    idea_text: str,
    idea_hash_val: str,
    language: str = "en",
    order_id: str = "",
    buyer_email: str = "",
    depth: str = "quick",
    tier: str = "single",
) -> dict:
    """Generate a paid report from scratch and save to DB.

    Args:
        tier: "single" or "pro" — controls multi-angle scanning

    Returns {"payment_status": "paid", "status": "complete", "report_id": ...}.
    Raises on failure.
    """
    keywords = await _extract_keywords_via_haiku(idea_text)
    keyword_source = "llm"
    if keywords is None:
        keywords = extract_keywords(idea_text)
        keyword_source = "dictionary"
    if depth == "deep":
        github_results, hn_results, npm_results, pypi_results, ph_results = (
            await asyncio.gather(
                search_github_repos(keywords),
                search_hn(keywords),
                search_npm(keywords),
                search_pypi(keywords),
                search_producthunt(keywords),
            )
        )
        signal_result = compute_signal(
            idea_text=idea_text,
            keywords=keywords,
            github_results=github_results,
            hn_results=hn_results,
            depth="deep",
            npm_results=npm_results,
            pypi_results=pypi_results,
            ph_results=ph_results,
        )
    else:
        github_results, hn_results = await asyncio.gather(
            search_github_repos(keywords),
            search_hn(keywords),
        )
        signal_result = compute_signal(
            idea_text=idea_text,
            keywords=keywords,
            github_results=github_results,
            hn_results=hn_results,
            depth="quick",
        )
    full_report = await report_mod.generate_report(
        idea_text=idea_text,
        signal_result=signal_result,
        language=language,
        tier=tier,
    )
    report_data = {**signal_result, "report": full_report, "keyword_source": keyword_source}
    report_id = str(uuid.uuid4())
    score_db.save_report(
        report_id=report_id,
        idea_text=idea_text,
        idea_hash=idea_hash_val or score_db.idea_hash(idea_text),
        score=signal_result["reality_signal"],
        report_data=json.dumps(report_data),
        language=language,
        stripe_session_id=order_id or None,
        buyer_email=buyer_email or None,
    )
    logger.info("[CHECKOUT] Report generated on-the-fly: report_id=%s, tier=%s", report_id, tier)
    return {
        "payment_status": "paid",
        "status": "complete",
        "report_id": report_id,
    }


async def _checkout_status_logic(
    order_id: str = "",
    session_id: str = "",
    idea_hash: str = "",
    idea_text: str = "",
    depth: str = "",
    tier: str = "single",
) -> dict:
    """Shared logic for GET and POST checkout-status.

    Lookup order:
      1. Find report by order_id → return if found
      2. Find report by idea_hash → return if found
      3. If idea_text provided and idea_hash matches → generate on-the-fly
      4. Try LemonSqueezy API (if order_id) → generate from custom_data
      5. Return pending
    """
    lookup_id = order_id or session_id
    if not lookup_id and not idea_hash:
        raise HTTPException(status_code=422, detail="order_id, session_id, or idea_hash required")

    # 1. Look up in DB by order ID
    report = None
    if lookup_id:
        report = score_db.get_report_by_stripe_session(lookup_id)
    # 2. Look up by idea_hash
    if not report and idea_hash:
        report = score_db.get_report_by_idea_hash(idea_hash)
    if report:
        return {
            "payment_status": "paid",
            "status": "complete",
            "report_id": report["report_id"],
        }

    # 3. Self-healing: regenerate only when a checkout reference exists
    #    (order_id/session_id proves a real checkout happened but webhook was missed).
    #    Without lookup_id, returning a report would bypass payment entirely.
    if idea_text and idea_text.strip() and idea_hash and lookup_id:
        computed_hash = score_db.idea_hash(idea_text.strip())
        if computed_hash == idea_hash:
            try:
                return await _generate_report_on_the_fly(
                    idea_text=idea_text.strip(),
                    idea_hash_val=idea_hash,
                    depth=depth or "quick",
                    tier=tier,
                )
            except Exception:
                logger.exception("[CHECKOUT] On-the-fly generation failed for idea_hash=%s", idea_hash[:16])

    # 4. Not in DB — try LemonSqueezy API to verify + regenerate
    if order_id and lemon_utils._get_api_key():
        try:
            order_attrs = await lemon_utils.get_order(order_id)
            if order_attrs.get("status") == "paid":
                custom = order_attrs.get("first_order_item", {}).get("custom_data", {})
                if not custom:
                    custom = {}
                lemon_idea_text = custom.get("idea_text", "")
                language = custom.get("language", "en")
                idea_hash_val = custom.get("idea_hash", "")
                lemon_depth = custom.get("depth", "quick")
                lemon_tier = custom.get("tier", "single")

                if lemon_idea_text:
                    try:
                        return await _generate_report_on_the_fly(
                            idea_text=lemon_idea_text,
                            idea_hash_val=idea_hash_val,
                            language=language,
                            order_id=order_id,
                            buyer_email=order_attrs.get("user_email", ""),
                            depth=lemon_depth,
                            tier=lemon_tier,
                        )
                    except Exception:
                        logger.exception("[LEMON] Report generation failed for order %s", order_id)
        except Exception:
            logger.exception("[LEMON] Failed to verify/regenerate order %s", order_id)

    # 5. Nothing worked
    return {"payment_status": "unpaid", "status": "pending"}


@app.get("/api/checkout-status")
async def checkout_status_get(order_id: str = "", session_id: str = "", idea_hash: str = ""):
    """Check payment status and return report_id (GET — backward compat).

    Accepts order_id (LemonSqueezy), session_id (legacy), or idea_hash.
    """
    return await _checkout_status_logic(
        order_id=order_id,
        session_id=session_id,
        idea_hash=idea_hash,
    )


class CheckoutStatusRequest(BaseModel):
    order_id: str = ""
    session_id: str = ""
    idea_hash: str = ""
    idea_text: str = ""
    depth: str = ""
    tier: str = "single"


@app.post("/api/checkout-status")
async def checkout_status_post(req: CheckoutStatusRequest):
    """Check payment status and return report_id (POST — with self-healing).

    If no report exists but idea_text is provided, generates the report
    on-the-fly so the user always gets their paid report even if the
    webhook was delayed or never fired.
    """
    return await _checkout_status_logic(
        order_id=req.order_id,
        session_id=req.session_id,
        idea_hash=req.idea_hash,
        idea_text=req.idea_text,
        depth=req.depth,
        tier=req.tier,
    )


# ---------------------------------------------------------------------------
# GET / — redirect to report page
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return RedirectResponse("/static/report.html")


@app.get("/report.html")
async def report_redirect():
    return RedirectResponse("/static/report.html")


# ---------------------------------------------------------------------------
# Mount static files at /static (before MCP catch-all)
# ---------------------------------------------------------------------------

app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")),
    name="static",
)

# ---------------------------------------------------------------------------
# Mount MCP Streamable HTTP at /mcp
# Enables Smithery and MCP HTTP clients to connect via:
#   https://idea-reality-mcp.onrender.com/mcp
# ---------------------------------------------------------------------------

app.mount("/", mcp_http)
