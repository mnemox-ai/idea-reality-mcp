"""FastAPI REST wrapper for idea-reality-mcp.

Exposes:
  GET  /health       — liveness probe
  POST /api/check    — idea reality check
  ANY  /mcp          — MCP Streamable HTTP transport (for Smithery / MCP clients)
"""

from __future__ import annotations

import asyncio
from typing import Literal

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
    version="0.3.1",
    lifespan=mcp_http.lifespan,
)

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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Liveness probe — called by /check page on load."""
    return {"status": "ok"}


@app.post("/api/check")
async def check(req: CheckRequest):
    """Run an idea reality check.

    Body: { "idea_text": "...", "depth": "quick" | "deep" }
    Returns the full reality check report dict.
    """
    if not req.idea_text or not req.idea_text.strip():
        raise HTTPException(status_code=422, detail="idea_text cannot be empty")

    idea_text = req.idea_text.strip()
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

    return result


# ---------------------------------------------------------------------------
# Mount MCP Streamable HTTP at /mcp
# Enables Smithery and MCP HTTP clients to connect via:
#   https://idea-reality-mcp.onrender.com/mcp
# ---------------------------------------------------------------------------

app.mount("/", mcp_http)
