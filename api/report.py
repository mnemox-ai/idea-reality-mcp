"""Paid report generation engine — V2.0.

5 sections, data-driven, no generic advice:
1. Score Breakdown — per-source signal bars
2. Crowd Intelligence — N similar queries, avg score (facts only)
3. Multi-Angle Search — Haiku generates 3-5 search perspectives
4. Real Competitors — top 15 from multi-angle scan, activity badges
5. Strategic Analysis — Sonnet LLM, one cohesive analysis
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone

import httpx

sys.path.insert(0, os.path.dirname(__file__))
import db as score_db  # noqa: E402

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Section 1: Score Breakdown — per-source signal bars
# ---------------------------------------------------------------------------


def _build_score_breakdown(signal_result: dict) -> dict:
    """Build per-source breakdown showing where signals came from."""
    score = signal_result.get("reality_signal", 0)
    evidence = signal_result.get("evidence", [])
    dup = signal_result.get("duplicate_likelihood", "unknown")

    # Aggregate signals by source
    sources: dict[str, int] = {}
    for ev in evidence:
        src = ev.get("source", "unknown")
        count = ev.get("count", 0)
        sources[src] = sources.get(src, 0) + count

    total_signals = sum(sources.values()) or 1
    ranked = sorted(sources.items(), key=lambda x: x[1], reverse=True)

    bars = []
    for src, count in ranked:
        pct = round(count / total_signals * 100)
        bars.append({
            "source": src,
            "signals": count,
            "percentage": pct,
        })

    # Score interpretation — factual, no opinion
    explanations = {
        "very_low": "Your idea has very little existing competition — this is rare and promising.",
        "low": "Few direct matches found. The market has room for new entrants.",
        "moderate": "Some existing projects, but meaningful differentiation is possible.",
        "high": "Active projects across multiple sources. Strong differentiation needed.",
        "very_high": "Multiple established projects. Consider a very specific niche or unique angle.",
    }

    if score >= 80:
        level = "very_high"
        summary = f"Very high competition ({score}/100). Multiple established projects exist."
    elif score >= 60:
        level = "high"
        summary = f"High competition ({score}/100). Active projects found across multiple sources."
    elif score >= 40:
        level = "moderate"
        summary = f"Moderate competition ({score}/100). Some existing projects, but room for differentiation."
    elif score >= 20:
        level = "low"
        summary = f"Low competition ({score}/100). Few direct matches found."
    else:
        level = "very_low"
        summary = f"Very low competition ({score}/100). Minimal existing solutions detected."

    return {
        "score": score,
        "level": level,
        "summary": summary,
        "explanation": explanations[level],
        "duplicate_likelihood": dup,
        "source_bars": bars,
        "total_signals": total_signals,
    }


# ---------------------------------------------------------------------------
# Section 2: Crowd Intelligence — facts only, no causal reasoning
# ---------------------------------------------------------------------------


def _build_crowd_intelligence(idea_text: str, idea_hash: str, score: int) -> dict:
    """Query score_history for similar ideas. Report FACTS only.

    Does NOT say 'lower score = entry angles' or any causal claims.
    Just: N queries matched, avg score, depth breakdown.
    """
    # Extract meaningful words for LIKE search
    words = [w.lower() for w in idea_text.split() if len(w) >= 4]
    if not words:
        words = [w.lower() for w in idea_text.split() if len(w) >= 3]

    similar = score_db.search_similar_ideas(
        keywords=words[:5],
        exclude_hash=idea_hash,
        limit=50,
    )

    # Total database size for context
    total_checks = score_db.get_total_checks()

    if not similar:
        return {
            "similar_count": 0,
            "total_database_queries": total_checks,
            "message": (
                f"Your idea is unique among {total_checks} queries in our database. "
                f"No one has searched for anything similar yet."
            ),
        }

    scores = [s["score"] for s in similar]
    avg_score = round(sum(scores) / len(scores), 1)

    # Depth breakdown
    depth_counts = {}
    for s in similar:
        d = s.get("depth", "quick")
        depth_counts[d] = depth_counts.get(d, 0) + 1

    # Score comparison
    if score > avg_score + 10:
        score_comparison = "higher than"
    elif score < avg_score - 10:
        score_comparison = "lower than"
    else:
        score_comparison = "similar to"

    return {
        "similar_count": len(similar),
        "avg_score": avg_score,
        "your_score": score,
        "score_comparison": score_comparison,
        "total_database_queries": total_checks,
        "depth_breakdown": depth_counts,
        "message": (
            f"{len(similar)} people searched for similar ideas. "
            f"Average competition score: {avg_score}/100. "
            f"Your score is {score_comparison} the average."
        ),
    }


# ---------------------------------------------------------------------------
# Section 3: Multi-Angle Search — Haiku generates search perspectives
# ---------------------------------------------------------------------------

_ANGLE_PROMPT = """Given a product idea, generate 3-5 distinct search angles.
Each angle should search for the same concept from a DIFFERENT perspective.

Example — idea: "AI code review tool"
→ ["AI code review tool", "automated pull request review", "LLM code analysis", "developer code quality automation"]

Rules:
- Each angle is 3-6 words, suitable for GitHub/npm search
- Angles should find DIFFERENT competitors (not the same ones with different words)
- Output ONLY a JSON array of strings. No explanation."""


async def _generate_search_angles(idea_text: str) -> list[str]:
    """Use Haiku to generate 3-5 distinct search angles from one idea.

    Fallback: extract query strings from signal_result evidence.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return [idea_text]

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=api_key, timeout=30.0)
        message = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=300,
            system=_ANGLE_PROMPT,
            messages=[{"role": "user", "content": idea_text}],
        )

        raw = message.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [ln for ln in lines if not ln.strip().startswith("```")]
            raw = "\n".join(lines).strip()

        angles = json.loads(raw)

        if not isinstance(angles, list) or len(angles) < 2:
            return [idea_text]

        cleaned = [str(a).strip() for a in angles if str(a).strip()]
        return cleaned[:5] if len(cleaned) >= 2 else [idea_text]

    except Exception:
        logger.exception("[REPORT] Haiku angle generation failed")
        return [idea_text]


def _fallback_angles_from_evidence(signal_result: dict) -> list[str]:
    """Extract query strings from signal_result evidence as fallback angles."""
    angles: list[str] = []
    for ev in signal_result.get("evidence", []):
        q = ev.get("query", "")
        if q and q not in angles:
            angles.append(q)
    return angles[:5] if angles else []


# ---------------------------------------------------------------------------
# Section 4: Real Competitors — activity badges
# ---------------------------------------------------------------------------


def _activity_badge(updated_at: str) -> dict:
    """Compute activity badge from GitHub updated_at timestamp.

    🔥 Active: updated < 30 days ago
    🆕 New: (can't determine from updated_at alone, skip)
    💤 Inactive: updated > 180 days ago
    ⚡ Recent: updated 30-180 days ago
    """
    if not updated_at:
        return {"badge": "❓", "label": "unknown", "days_since_update": None}

    try:
        # Parse ISO timestamp (GitHub format: "2026-03-01T12:00:00Z")
        updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days = (now - updated).days

        if days < 30:
            return {"badge": "🔥", "label": "active", "days_since_update": days}
        elif days < 180:
            return {"badge": "⚡", "label": "recent", "days_since_update": days}
        else:
            return {"badge": "💤", "label": "inactive", "days_since_update": days}
    except Exception:
        return {"badge": "❓", "label": "unknown", "days_since_update": None}


async def _build_competitor_analysis(signal_result: dict) -> list[dict]:
    """Fetch extended competitors from GitHub with activity badges.

    Does NOT touch keyword extraction (out of scope).
    """
    from idea_reality_mcp.sources.github import (
        GITHUB_API,
        _headers,
        _is_noise_repo,
    )

    # Extract query strings from evidence
    keywords: list[str] = []
    for ev in signal_result.get("evidence", []):
        q = ev.get("query", "")
        if q and q not in keywords:
            keywords.append(q)

    if not keywords:
        # Fallback: use top_similars from signal_result
        return [
            {**s, "activity": _activity_badge(s.get("updated", ""))}
            for s in signal_result.get("top_similars", [])[:10]
        ]

    all_repos: list[dict] = []
    repo_hits: dict[str, int] = {}

    async with httpx.AsyncClient(timeout=15.0) as client:
        for query in keywords[:3]:
            try:
                resp = await client.get(
                    GITHUB_API,
                    params={
                        "q": query,
                        "sort": "stars",
                        "order": "desc",
                        "per_page": 10,
                    },
                    headers=_headers(),
                )
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("items", []):
                    name = item.get("full_name", "")
                    if not name:
                        continue
                    repo_hits[name] = repo_hits.get(name, 0) + 1
                    all_repos.append({
                        "name": name,
                        "url": item.get("html_url", ""),
                        "stars": item.get("stargazers_count", 0),
                        "description": (item.get("description") or "")[:300],
                        "updated": item.get("updated_at", ""),
                        "created": item.get("created_at", ""),
                        "language": item.get("language", ""),
                    })
            except Exception:
                continue

    # Build relevance keywords from query strings
    relevance_kws: list[str] = []
    kw_set: set[str] = set()
    for q in keywords[:3]:
        for w in q.lower().split():
            if len(w) >= 4:
                kw_set.add(w)
    relevance_kws = list(kw_set) or None

    all_repos = [r for r in all_repos if not _is_noise_repo(r, query_keywords=relevance_kws)]

    # Dedupe and sort by (hit_count, stars)
    seen: set[str] = set()
    unique: list[dict] = []
    for repo in sorted(
        all_repos,
        key=lambda r: (repo_hits.get(r["name"], 0), r["stars"]),
        reverse=True,
    ):
        if repo["name"] not in seen:
            seen.add(repo["name"])
            repo["activity"] = _activity_badge(repo.get("updated", ""))
            unique.append(repo)

    return unique[:10]


async def _build_multi_angle_competitors(
    angles: list[str],
    signal_result: dict,
) -> list[dict]:
    """For each angle, run 1 GitHub search. Merge, dedupe, tag found_via_angles."""
    from idea_reality_mcp.sources.github import (
        GITHUB_API,
        _headers,
        _is_noise_repo,
    )

    all_repos: list[dict] = []
    # Track which angles found each repo
    repo_angles: dict[str, list[str]] = {}

    async with httpx.AsyncClient(timeout=15.0) as client:
        for angle in angles:
            try:
                resp = await client.get(
                    GITHUB_API,
                    params={
                        "q": angle,
                        "sort": "stars",
                        "order": "desc",
                        "per_page": 10,
                    },
                    headers=_headers(),
                )
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("items", []):
                    name = item.get("full_name", "")
                    if not name:
                        continue
                    if name not in repo_angles:
                        repo_angles[name] = []
                    repo_angles[name].append(angle)
                    all_repos.append({
                        "name": name,
                        "url": item.get("html_url", ""),
                        "stars": item.get("stargazers_count", 0),
                        "description": (item.get("description") or "")[:300],
                        "updated": item.get("updated_at", ""),
                        "created": item.get("created_at", ""),
                        "language": item.get("language", ""),
                    })
            except Exception:
                continue

    # Build relevance keywords from all angles
    kw_set: set[str] = set()
    for angle in angles:
        for w in angle.lower().split():
            if len(w) >= 4:
                kw_set.add(w)
    relevance_kws = list(kw_set) or None

    all_repos = [r for r in all_repos if not _is_noise_repo(r, query_keywords=relevance_kws)]

    # Dedupe: merge found_via_angles, sort by angle count desc then stars desc
    seen: set[str] = set()
    unique: list[dict] = []
    for repo in sorted(
        all_repos,
        key=lambda r: (len(repo_angles.get(r["name"], [])), r["stars"]),
        reverse=True,
    ):
        if repo["name"] not in seen:
            seen.add(repo["name"])
            repo["found_via_angles"] = repo_angles.get(repo["name"], [])
            repo["activity"] = _activity_badge(repo.get("updated", ""))
            unique.append(repo)

    return unique[:15]


# ---------------------------------------------------------------------------
# Section 5: Strategic Analysis — Sonnet (paid) / Haiku (free fallback)
# ---------------------------------------------------------------------------

_STRATEGIC_PROMPT = """You are a competitive intelligence analyst writing a paid report section.

Given:
- An idea description
- Competition score and source breakdown
- Real competitor data with activity status
- Crowd intelligence (how many people searched similar ideas)

Write ONE cohesive strategic analysis (400-600 words). Structure:

1. **Competitive Landscape** (2-3 sentences): What does the data tell us? Reference specific competitors by name, their star counts, and activity status.

2. **Market Gaps** (2-3 sentences): Based on the competitors found, what's missing? What do users likely still struggle with? (Infer from the types of projects found, NOT from generic startup advice.)

3. **Positioning Opportunity** (2-3 sentences): Given the crowd data (N people searched similar ideas) and competitor activity, where should this idea position itself?

4. **Key Risk** (1-2 sentences): The single biggest risk based on the actual data, not generic "market risk" statements.

RULES:
- Reference ACTUAL competitor names, star counts, and activity badges from the data provided
- Every claim must tie back to a specific data point
- NO generic startup advice (no "build an MVP", "focus on user feedback", "consider content marketing")
- If data is thin, say so honestly instead of making things up
- Write in the language specified in the Language field
- No markdown headers — use natural paragraph transitions
- No code fences"""

_FALLBACK_ANALYSIS = (
    "Strategic analysis could not be generated at this time. "
    "The data above (competitors, activity badges, and crowd signals) "
    "provides the raw intelligence for your own analysis."
)


async def _generate_strategic_analysis(
    idea_text: str,
    signal_result: dict,
    competitors: list[dict],
    crowd: dict,
    language: str,
    *,
    angles: list[str] | None = None,
) -> str:
    """Call Sonnet for paid report strategic analysis. Falls back to template."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.info("[REPORT] skipped LLM — no ANTHROPIC_API_KEY")
        return _FALLBACK_ANALYSIS

    # Build competitor summary
    comp_lines = []
    for c in competitors[:15]:
        activity = c.get("activity", {})
        badge = activity.get("badge", "")
        days = activity.get("days_since_update")
        days_str = f", last updated {days}d ago" if days is not None else ""
        desc = f" — {c['description'][:100]}" if c.get("description") else ""
        found_via = c.get("found_via_angles", [])
        via_str = f" [found via: {', '.join(found_via)}]" if found_via else ""
        comp_lines.append(
            f"- {badge} {c['name']} ({c.get('stars', 0)}★{days_str}){desc}{via_str}"
        )
    competitors_text = "\n".join(comp_lines) if comp_lines else "(no competitors found)"

    # Build source breakdown
    breakdown = signal_result.get("evidence", [])
    ev_lines = []
    for ev in breakdown[:8]:
        ev_lines.append(f"- [{ev.get('source', '?')}] {ev.get('detail', '')}")
    evidence_text = "\n".join(ev_lines) if ev_lines else "(no evidence)"

    # Crowd summary
    sim_count = crowd.get("similar_count", 0)
    avg_score = crowd.get("avg_score", 0)
    total_db = crowd.get("total_database_queries", 0)
    crowd_text = (
        f"Database: {total_db} total queries. "
        f"{sim_count} similar queries found, avg score {avg_score}/100."
        if sim_count > 0
        else f"Database: {total_db} total queries. No similar queries found."
    )

    # Search angles context
    angles_text = ""
    if angles and len(angles) > 1:
        angles_text = f"\nSearch Angles Used:\n" + "\n".join(f"- {a}" for a in angles) + "\n"

    user_prompt = (
        f"Idea: {idea_text}\n"
        f"Reality Signal: {signal_result.get('reality_signal', 0)}/100\n"
        f"Duplicate Likelihood: {signal_result.get('duplicate_likelihood', 'unknown')}\n"
        f"Language: {language}\n"
        f"{angles_text}\n"
        f"Source Evidence:\n{evidence_text}\n\n"
        f"Competitors:\n{competitors_text}\n\n"
        f"Crowd Intelligence:\n{crowd_text}"
    )

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=api_key, timeout=30.0)
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=_STRATEGIC_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return message.content[0].text.strip()

    except Exception:
        logger.exception("[REPORT] Sonnet analysis failed")
        return _FALLBACK_ANALYSIS


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _build_single_competitors(signal_result: dict) -> list[dict]:
    """Build competitor list from existing signal_result data (zero extra API calls).

    Uses top_similars already computed by engine.py.
    """
    similars = signal_result.get("top_similars", [])
    competitors = []
    for s in similars:
        name = s.get("name", "")
        # Skip npm:/pypi:/ph: prefixed entries — they're packages, not direct competitors
        if ":" in name and name.split(":")[0] in ("npm", "pypi", "ph"):
            continue
        comp = {
            "name": name,
            "url": s.get("url", ""),
            "stars": s.get("stars", 0),
            "description": (s.get("description") or "")[:300],
            "updated": s.get("updated", ""),
            "language": s.get("language", ""),
            "activity": _activity_badge(s.get("updated", "")),
            "found_via_angles": [],  # single tier: no multi-angle
        }
        competitors.append(comp)
    return competitors[:8]


async def generate_report(
    idea_text: str,
    signal_result: dict,
    language: str = "en",
    tier: str = "single",
) -> dict:
    """Generate a paid report from compute_signal() output.

    Args:
        tier: "single" (no extra API calls) or "pro" (multi-angle scan)

    Returns dict with keys:
    - search_angles: list of search perspectives used
    - sub_scores: per-source sub-dimension scores
    - score_breakdown: per-source signal bars
    - crowd_intelligence: similar queries data
    - competitors: verified competitors with activity badges
    - strategic_analysis: Sonnet-generated cohesive analysis (string)
    - verified_at: ISO timestamp of report generation
    """
    idea_h = score_db.idea_hash(idea_text)
    score = signal_result.get("reality_signal", 0)

    if tier == "pro":
        # Pro tier: multi-angle scan (3-5 perspectives, 15 competitors)
        angles = await _generate_search_angles(idea_text)
        if len(angles) <= 1:
            fallback = _fallback_angles_from_evidence(signal_result)
            if fallback:
                angles = fallback
        competitors = await _build_multi_angle_competitors(angles, signal_result)
    else:
        # Single tier: use existing scan data (zero extra API calls)
        angles = [idea_text]
        competitors = _build_single_competitors(signal_result)

    score_breakdown = _build_score_breakdown(signal_result)
    crowd = _build_crowd_intelligence(idea_text, idea_h, score)
    sub_scores = signal_result.get("sub_scores", {})

    analysis = await _generate_strategic_analysis(
        idea_text, signal_result, competitors, crowd, language,
        angles=angles,
    )

    return {
        "search_angles": angles,
        "sub_scores": sub_scores,
        "score_breakdown": score_breakdown,
        "crowd_intelligence": crowd,
        "competitors": competitors,
        "strategic_analysis": analysis,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }
