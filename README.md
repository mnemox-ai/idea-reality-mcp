# idea-reality-mcp

Pre-build reality check for AI coding agents. Stop building what already exists.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)

## What it does

`idea-reality-mcp` is an MCP server that provides the `idea_check` tool. When an AI coding agent is about to build something, it can call this tool to check whether similar projects already exist on GitHub and Hacker News.

The tool returns:

- **reality_signal** (0–100): How much existing work overlaps with your idea
- **duplicate_likelihood**: low / medium / high
- **evidence**: Raw search data from GitHub and HN
- **top_similars**: Top 5 similar GitHub repos with stars, URLs, descriptions
- **pivot_hints**: 3 actionable suggestions based on the competitive landscape

## Quickstart

```bash
# Install and run
uvx idea-reality-mcp

# Or clone and run locally
git clone https://github.com/mnemox-ai/idea-reality-mcp.git
cd idea-reality-mcp
uv run idea-reality-mcp
```

### Optional: Set GitHub token for higher rate limits

```bash
export GITHUB_TOKEN=ghp_your_token_here
```

## Claude Desktop config

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "idea-reality": {
      "command": "uvx",
      "args": ["idea-reality-mcp"]
    }
  }
}
```

## Cursor config

Add to `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "idea-reality": {
      "command": "uvx",
      "args": ["idea-reality-mcp"]
    }
  }
}
```

## Tool schema

### `idea_check`

**Input:**

| Parameter   | Type                      | Required | Description                          |
|-------------|---------------------------|----------|--------------------------------------|
| `idea_text` | string                    | yes      | Natural-language description of idea |
| `depth`     | `"quick"` \| `"deep"`     | no       | `"quick"` = GitHub + HN (default). `"deep"` = reserved for v0.2 |

**Output:**

```json
{
  "reality_signal": 72,
  "duplicate_likelihood": "high",
  "evidence": [
    {"source": "github", "type": "repo_count", "query": "...", "count": 342, "detail": "..."},
    {"source": "github", "type": "max_stars", "query": "...", "count": 15000, "detail": "..."},
    {"source": "hackernews", "type": "mention_count", "query": "...", "count": 18, "detail": "..."}
  ],
  "top_similars": [
    {"name": "user/repo", "url": "https://github.com/user/repo", "stars": 15000, "updated": "2025-12-01T...", "description": "..."}
  ],
  "pivot_hints": [
    "High existing competition detected. Consider a niche differentiator...",
    "The leading project (user/repo, 15000 stars) may have gaps...",
    "Consider building an integration or plugin..."
  ],
  "meta": {
    "checked_at": "2025-12-15T10:30:00+00:00",
    "sources_used": ["github", "hackernews"],
    "depth": "quick",
    "version": "0.1.0"
  }
}
```

## Sample prompts

```
Before building, check if this already exists: a CLI tool that converts
Figma designs to React components automatically

idea_check: AI-powered code review bot for GitHub PRs that suggests fixes

Check market reality: real-time collaborative markdown editor with AI
autocomplete
```

## Roadmap

- **v0.1** — GitHub + HN search, basic scoring (current)
- **v0.2** — `depth: "deep"` with Product Hunt, npm/PyPI registry search
- **v0.3** — LLM-powered keyword extraction and semantic similarity
- **v0.4** — Trend detection and timing analysis

## License

MIT — see [LICENSE](LICENSE)
