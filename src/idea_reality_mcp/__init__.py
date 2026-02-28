"""idea-reality-mcp: Pre-build reality check for AI coding agents."""

__version__ = "0.4.0"


def main() -> None:
    """CLI entry point."""
    from .server import mcp

    mcp.run()
