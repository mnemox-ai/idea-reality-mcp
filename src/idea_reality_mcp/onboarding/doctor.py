"""Health check (doctor) for idea-reality-mcp installation."""

from __future__ import annotations

import os
import sys


# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

def _green(text: str) -> str:
    return f"\033[32m{text}\033[0m"


def _red(text: str) -> str:
    return f"\033[31m{text}\033[0m"


def _yellow(text: str) -> str:
    return f"\033[33m{text}\033[0m"


def _pass(label: str, detail: str = "") -> None:
    msg = f"  {_green('[PASS]')} {label}"
    if detail:
        msg += f" -- {detail}"
    print(msg)


def _fail(label: str, detail: str = "") -> None:
    msg = f"  {_red('[FAIL]')} {label}"
    if detail:
        msg += f" -- {detail}"
    print(msg)


def _warn(label: str, detail: str = "") -> None:
    msg = f"  {_yellow('[WARN]')} {label}"
    if detail:
        msg += f" -- {detail}"
    print(msg)


# ---------------------------------------------------------------------------
# Core checks
# ---------------------------------------------------------------------------

def _check_python_version() -> bool:
    """Python >= 3.11."""
    ok = sys.version_info >= (3, 11)
    v = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if ok:
        _pass("Python version", v)
    else:
        _fail("Python version", f"{v} (need >= 3.11)")
    return ok


def _check_import_server() -> bool:
    """Can import idea_reality_mcp.server."""
    try:
        import idea_reality_mcp.server  # noqa: F401
        _pass("MCP server import")
        return True
    except Exception as e:
        _fail("MCP server import", str(e))
        return False


def _check_tools_load() -> bool:
    """idea_check tool exists on the MCP server."""
    try:
        from idea_reality_mcp.server import mcp  # noqa: F811
        # FastMCP stores tools; check the tool registry
        tools = mcp._tool_manager._tools if hasattr(mcp, "_tool_manager") else {}
        if not tools:
            # Fallback: try older FastMCP API
            tools = getattr(mcp, "_tools", {})
        if "idea_check" in tools:
            _pass("MCP tool: idea_check")
            return True
        else:
            _warn("MCP tool: idea_check", "tool not found in registry (may need different FastMCP API)")
            return True  # non-fatal
    except Exception as e:
        _fail("MCP tool load", str(e))
        return False


def _check_scoring_engine() -> bool:
    """compute_signal runs with dummy data."""
    try:
        from idea_reality_mcp.scoring.engine import compute_signal
        from idea_reality_mcp.sources.github import GitHubResults
        from idea_reality_mcp.sources.hn import HNResults

        dummy_gh = GitHubResults(
            total_repo_count=0, top_repos=[], max_stars=0,
        )
        dummy_hn = HNResults(total_mentions=0, evidence=[])
        result = compute_signal(
            idea_text="test idea",
            keywords=["test"],
            github_results=dummy_gh,
            hn_results=dummy_hn,
            depth="quick",
        )
        if isinstance(result, dict) and "reality_signal" in result:
            _pass("Scoring engine", f"reality_signal={result['reality_signal']}")
            return True
        else:
            _fail("Scoring engine", "unexpected return format")
            return False
    except Exception as e:
        _fail("Scoring engine", str(e))
        return False


# ---------------------------------------------------------------------------
# Full checks (external connectivity)
# ---------------------------------------------------------------------------

def _check_github_token() -> bool:
    """GITHUB_TOKEN is set and valid."""
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        _warn("GITHUB_TOKEN", "not set (unauthenticated GitHub API: 10 req/hr)")
        return False
    try:
        import httpx
        resp = httpx.get(
            "https://api.github.com/rate_limit",
            headers={"Authorization": f"token {token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            remaining = data.get("rate", {}).get("remaining", "?")
            _pass("GITHUB_TOKEN", f"valid ({remaining} requests remaining)")
            return True
        else:
            _fail("GITHUB_TOKEN", f"HTTP {resp.status_code}")
            return False
    except Exception as e:
        _fail("GITHUB_TOKEN", str(e))
        return False


def _check_source_reachable(name: str, url: str) -> bool:
    """HEAD request to a source URL."""
    try:
        import httpx
        resp = httpx.head(url, timeout=10, follow_redirects=True)
        if resp.status_code < 400:
            _pass(f"Source: {name}", f"HTTP {resp.status_code}")
            return True
        else:
            _fail(f"Source: {name}", f"HTTP {resp.status_code}")
            return False
    except Exception as e:
        _fail(f"Source: {name}", str(e))
        return False


def _check_anthropic_key() -> bool:
    """ANTHROPIC_API_KEY is set."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        _pass("ANTHROPIC_API_KEY", "set")
        return True
    else:
        _warn("ANTHROPIC_API_KEY", "not set (LLM keyword extraction disabled)")
        return False


def _check_rest_api() -> bool:
    """REST API reachable."""
    try:
        import httpx
        resp = httpx.get(
            "https://idea-reality-mcp.onrender.com/health",
            timeout=15,
        )
        if resp.status_code == 200:
            _pass("REST API", "reachable")
            return True
        else:
            _fail("REST API", f"HTTP {resp.status_code}")
            return False
    except Exception as e:
        _warn("REST API", f"unreachable ({e})")
        return False


# ---------------------------------------------------------------------------
# Source URLs
# ---------------------------------------------------------------------------

SOURCE_URLS = {
    "GitHub": "https://api.github.com",
    "Hacker News": "https://hn.algolia.com",
    "npm": "https://registry.npmjs.org",
    "PyPI": "https://pypi.org",
    "Product Hunt": "https://www.producthunt.com",
    "Stack Overflow": "https://api.stackexchange.com",
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_doctor(full: bool = False) -> bool:
    """Run health checks. Returns True if all core checks pass."""
    print("\n  idea-reality-mcp doctor\n")

    print("  Core checks:")
    results = [
        _check_python_version(),
        _check_import_server(),
        _check_tools_load(),
        _check_scoring_engine(),
    ]
    core_ok = all(results)

    if full:
        print("\n  Connectivity checks:")
        _check_github_token()
        for name, url in SOURCE_URLS.items():
            _check_source_reachable(name, url)
        _check_anthropic_key()
        _check_rest_api()

    print()
    if core_ok:
        print(f"  {_green('All core checks passed.')}")
    else:
        print(f"  {_red('Some core checks failed.')}")
    print()
    return core_ok
