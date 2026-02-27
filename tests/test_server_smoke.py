"""Smoke tests for the MCP server."""

from idea_reality_mcp.server import mcp


def test_server_has_name():
    assert mcp.name == "idea-reality-mcp"


def test_idea_check_tool_registered():
    """Verify the idea_check tool is registered on the server."""
    # FastMCP registers tools internally; we can verify by checking
    # that importing tools module doesn't error and the tool function exists
    from idea_reality_mcp.tools import idea_check

    assert callable(idea_check)


def test_server_importable():
    """Verify the package is importable and has version."""
    import idea_reality_mcp

    assert idea_reality_mcp.__version__ == "0.3.2"
