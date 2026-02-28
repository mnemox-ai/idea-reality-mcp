# idea-reality-mcp — Cursor Plugin

Pre-build reality check for your AI agent. Scans 5 real databases before you write code.

## What's included

| Component | Description |
|-----------|-------------|
| **MCP Server** | `idea_check` tool — scans GitHub, HN, npm, PyPI, Product Hunt |
| **Skill** | `idea-check` — guides the agent through reality check workflow |
| **Rule** | Auto-trigger hint — reminds agent to check before building |

## Quick start

1. Install from Cursor Marketplace
2. Ask your agent: "Check if there's already a tool that does X"
3. Get a 0-100 reality signal with real competitor data

## Configuration

Optional environment variables:

```bash
GITHUB_TOKEN=ghp_...        # Higher GitHub API rate limits
PRODUCTHUNT_TOKEN=your_...  # Enable Product Hunt (deep mode)
```

## Links

- [GitHub](https://github.com/mnemox-ai/idea-reality-mcp)
- [Web demo](https://mnemox.ai/check)
- [PyPI](https://pypi.org/project/idea-reality-mcp/)

## License

MIT
