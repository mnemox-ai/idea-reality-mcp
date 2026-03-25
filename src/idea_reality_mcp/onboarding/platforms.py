"""Platform detection and MCP config templates for idea-reality-mcp."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

def _green(text: str) -> str:
    return f"\033[32m{text}\033[0m"


def _yellow(text: str) -> str:
    return f"\033[33m{text}\033[0m"


# ---------------------------------------------------------------------------
# MCP server command
# ---------------------------------------------------------------------------

MCP_COMMAND = "uvx"
MCP_ARGS = ["idea-reality-mcp"]
MCP_FALLBACK_COMMAND = "python"
MCP_FALLBACK_ARGS = ["-m", "idea_reality_mcp"]

# ---------------------------------------------------------------------------
# Platform definitions
# ---------------------------------------------------------------------------

def _claude_desktop_config_path() -> Path | None:
    """Return Claude Desktop config path for the current OS."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
        return None
    else:  # Linux
        xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        return Path(xdg) / "Claude" / "claude_desktop_config.json"


def _mcp_json_block() -> dict[str, Any]:
    """Standard MCP server JSON config block."""
    return {
        "command": MCP_COMMAND,
        "args": MCP_ARGS,
    }


PLATFORMS: dict[str, dict[str, Any]] = {
    "claude_desktop": {
        "name": "Claude Desktop",
        "detect": lambda: _claude_desktop_config_path() is not None
        and _claude_desktop_config_path().parent.exists(),
        "config_path": _claude_desktop_config_path,
        "instruction": lambda: (
            f"Add to {_claude_desktop_config_path()}:\n"
            + json.dumps(
                {"mcpServers": {"idea-reality-mcp": _mcp_json_block()}},
                indent=2,
            )
        ),
    },
    "claude_code": {
        "name": "Claude Code",
        "detect": lambda: _which("claude") is not None,
        "config_path": lambda: None,
        "instruction": lambda: (
            "Run:\n  claude mcp add idea-reality -- uvx idea-reality-mcp"
        ),
    },
    "cursor": {
        "name": "Cursor",
        "detect": lambda: (Path.cwd() / ".cursor").is_dir()
        or Path(os.environ.get("APPDATA", "") or Path.home()).joinpath(
            ".cursor"
        ).is_dir(),
        "config_path": lambda: Path.cwd() / ".cursor" / "mcp.json",
        "instruction": lambda: (
            "Add to .cursor/mcp.json:\n"
            + json.dumps(
                {"mcpServers": {"idea-reality-mcp": _mcp_json_block()}},
                indent=2,
            )
        ),
    },
    "windsurf": {
        "name": "Windsurf",
        "detect": lambda: _windsurf_config_path().parent.exists(),
        "config_path": lambda: _windsurf_config_path(),
        "instruction": lambda: (
            f"Add to {_windsurf_config_path()}:\n"
            + json.dumps(
                {"mcpServers": {"idea-reality-mcp": _mcp_json_block()}},
                indent=2,
            )
        ),
    },
    "cline": {
        "name": "Cline",
        "detect": lambda: (Path.cwd() / ".cline").is_dir(),
        "config_path": lambda: Path.cwd() / ".cline" / "mcp.json",
        "instruction": lambda: (
            "Add to .cline/mcp.json:\n"
            + json.dumps(
                {"mcpServers": {"idea-reality-mcp": _mcp_json_block()}},
                indent=2,
            )
        ),
    },
    "smithery": {
        "name": "Smithery",
        "detect": lambda: _which("npx") is not None,
        "config_path": lambda: None,
        "instruction": lambda: (
            "Run:\n  npx -y @smithery/cli install idea-reality-mcp"
        ),
    },
    "docker": {
        "name": "Docker",
        "detect": lambda: _which("docker") is not None,
        "config_path": lambda: None,
        "instruction": lambda: (
            "Run:\n  docker run --rm -i mnemox/idea-reality-mcp"
        ),
    },
    "raw_json": {
        "name": "Raw JSON (manual)",
        "detect": lambda: True,  # always available as fallback
        "config_path": lambda: None,
        "instruction": lambda: (
            "MCP server config:\n"
            + json.dumps(
                {"idea-reality-mcp": _mcp_json_block()},
                indent=2,
            )
        ),
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _which(cmd: str) -> str | None:
    """Minimal shutil.which without importing shutil at module level."""
    import shutil
    return shutil.which(cmd)


def _windsurf_config_path() -> Path:
    """Return Windsurf config path."""
    if sys.platform == "win32":
        home = Path.home()
    else:
        home = Path.home()
    return home / ".codeium" / "windsurf" / "mcp_config.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_platforms() -> list[dict[str, Any]]:
    """Detect which MCP platforms are available on this system.

    Returns a list of dicts with keys: id, name, instruction.
    """
    detected: list[dict[str, Any]] = []
    for platform_id, cfg in PLATFORMS.items():
        if platform_id == "raw_json":
            continue  # always included separately
        try:
            if cfg["detect"]():
                detected.append(
                    {
                        "id": platform_id,
                        "name": cfg["name"],
                        "instruction": cfg["instruction"](),
                    }
                )
        except Exception:
            pass  # skip platforms that fail detection
    return detected


def get_platform_instruction(platform_id: str) -> str | None:
    """Get config instruction for a specific platform."""
    cfg = PLATFORMS.get(platform_id)
    if cfg is None:
        return None
    try:
        return cfg["instruction"]()
    except Exception:
        return None
