"""FastMCP server definition."""

import sys
from pathlib import Path

# First-run hint (stderr only, does not affect MCP protocol)
if not (Path.home() / ".idea-reality" / ".setup_done").exists():
    print("First time? Run: idea-reality setup", file=sys.stderr)

from fastmcp import FastMCP

mcp = FastMCP(
    "idea-reality-mcp",
    instructions="Pre-build reality check for AI coding agents. Stop building what already exists.",
)

# Register tools by importing the module (tools use @mcp.tool decorator)
from . import tools  # noqa: F401, E402
