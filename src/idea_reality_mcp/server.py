"""FastMCP server definition."""

from fastmcp import FastMCP

mcp = FastMCP(
    "idea-reality-mcp",
    instructions="Pre-build reality check for AI coding agents. Stop building what already exists.",
)

# Register tools by importing the module (tools use @mcp.tool decorator)
from . import tools  # noqa: F401, E402
