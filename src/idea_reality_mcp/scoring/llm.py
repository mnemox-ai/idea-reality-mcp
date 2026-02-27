"""LLM-powered keyword extraction — MCP client side.

Calls the Render API ``/api/extract-keywords`` which invokes Claude Haiku 4.5
to generate optimised search queries.  Falls back to *None* on **any** failure
(timeout, rate-limit, server error, bad JSON) so the caller can switch to the
dictionary-based ``extract_keywords()`` pipeline.
"""

from __future__ import annotations

import json
import os

import httpx

_DEFAULT_API_URL = "https://idea-reality-mcp.onrender.com"
_TIMEOUT_SECONDS = 8.0


async def extract_keywords_llm(idea_text: str) -> list[str] | None:
    """Ask the Render API to generate search keywords via Claude Haiku 4.5.

    Returns:
        A list of 3-8 keyword query strings, or *None* if the request fails
        for any reason (timeout, 429, 5xx, invalid response, etc.).
    """
    api_url = os.environ.get("IDEA_REALITY_API_URL", _DEFAULT_API_URL)
    url = f"{api_url}/api/extract-keywords"

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json={"idea_text": idea_text})

        if resp.status_code != 200:
            return None

        data = resp.json()
        keywords = data.get("keywords")

        if not isinstance(keywords, list) or len(keywords) < 2:
            return None

        # Ensure every element is a non-empty string
        cleaned = [str(k).strip() for k in keywords if str(k).strip()]
        if len(cleaned) < 2:
            return None

        return cleaned[:8]

    except (httpx.HTTPError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
