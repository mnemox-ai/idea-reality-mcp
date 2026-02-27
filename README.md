English | [繁體中文](README.zh-TW.md)

# idea-reality-mcp

Pre-build reality check for AI coding agents. Stop building what already exists.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)
[![PyPI](https://img.shields.io/pypi/v/idea-reality-mcp.svg)](https://pypi.org/project/idea-reality-mcp/)
[![Smithery](https://smithery.ai/badge/idea-reality-mcp)](https://smithery.ai/server/idea-reality-mcp)

> **v0.3 is here** — 3-stage keyword extraction pipeline, 150+ Chinese term mappings, 90+ intent anchors, 80+ synonym expansions. Supports Chinese and mixed-language input out of the box.

## What it does

`idea-reality-mcp` is an MCP server that provides the `idea_check` tool. When an AI coding agent is about to build something, it can call this tool to check whether similar projects already exist across multiple sources.

**Quick mode** (default): GitHub + Hacker News
**Deep mode**: GitHub + HN + npm + PyPI + Product Hunt (all sources in parallel)

The tool returns:

- **reality_signal** (0-100): How much existing work overlaps with your idea
- **duplicate_likelihood**: low / medium / high
- **evidence**: Raw search data from all queried sources
- **top_similars**: Top similar projects from GitHub, npm, PyPI, and Product Hunt
- **pivot_hints**: 3 actionable suggestions based on the competitive landscape

## Quickstart

```bash
# Install and run
uvx idea-reality-mcp

# Or install via Smithery
npx -y @smithery/cli install idea-reality-mcp --client claude

# Or clone and run locally
git clone https://github.com/mnemox-ai/idea-reality-mcp.git
cd idea-reality-mcp
uv run idea-reality-mcp
```

### Optional: Environment variables

```bash
# Higher GitHub API rate limits
export GITHUB_TOKEN=ghp_your_token_here

# Enable Product Hunt search (deep mode)
export PRODUCTHUNT_TOKEN=your_ph_token_here
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

## Recommended: Add to your CLAUDE.md

To ensure your AI agent automatically uses `idea_check` when you discuss new ideas, add this line to your project's `CLAUDE.md` (or equivalent instructions file):

```
When users discuss new project ideas or ask about competition, use the idea_check tool from idea-reality-mcp.
```

This helps the agent recognize when to call the tool without you having to explicitly name it.

## Tool schema

### `idea_check`

**Input:**

| Parameter   | Type                      | Required | Description                          |
|-------------|---------------------------|----------|--------------------------------------|
| `idea_text` | string                    | yes      | Natural-language description of idea |
| `depth`     | `"quick"` \| `"deep"`     | no       | `"quick"` = GitHub + HN (default). `"deep"` = all 5 sources in parallel |

**Output:**

```json
{
  "reality_signal": 72,
  "duplicate_likelihood": "high",
  "evidence": [
    {"source": "github", "type": "repo_count", "query": "...", "count": 342, "detail": "..."},
    {"source": "github", "type": "max_stars", "query": "...", "count": 15000, "detail": "..."},
    {"source": "hackernews", "type": "mention_count", "query": "...", "count": 18, "detail": "..."},
    {"source": "npm", "type": "package_count", "query": "...", "count": 56, "detail": "..."},
    {"source": "pypi", "type": "package_count", "query": "...", "count": 23, "detail": "..."},
    {"source": "producthunt", "type": "product_count", "query": "...", "count": 8, "detail": "..."}
  ],
  "top_similars": [
    {"name": "user/repo", "url": "https://github.com/...", "stars": 15000, "updated": "...", "description": "..."},
    {"name": "npm:cool-pkg", "url": "https://npmjs.com/...", "stars": 0, "updated": "", "description": "..."},
    {"name": "pypi:cool-pkg", "url": "https://pypi.org/...", "stars": 0, "updated": "", "description": "..."}
  ],
  "pivot_hints": [
    "High existing competition detected. Consider a niche differentiator...",
    "The leading project (user/repo, 15000 stars) may have gaps...",
    "Consider building an integration or plugin..."
  ],
  "meta": {
    "checked_at": "2026-02-25T10:30:00+00:00",
    "sources_used": ["github", "hackernews", "npm", "pypi", "producthunt"],
    "depth": "deep",
    "version": "0.3.0"
  }
}
```

### Scoring weights

**Quick mode:** GitHub repos 60% + GitHub stars 20% + HN mentions 20%

**Deep mode:** GitHub repos 25% + GitHub stars 10% + HN mentions 15% + npm 20% + PyPI 15% + Product Hunt 15%

If Product Hunt is unavailable (no token), its weight is automatically redistributed to the other sources.

## Sample prompts

```
Before building, check if this already exists: a CLI tool that converts
Figma designs to React components automatically

idea_check("AI-powered code review bot for GitHub PRs", depth="deep")

Check market reality: real-time collaborative markdown editor with AI
autocomplete
```

## Roadmap

- [x] **v0.1** — GitHub + HN search, basic scoring
- [x] **v0.2** — `depth: "deep"` with npm, PyPI, Product Hunt; improved keyword extraction
- [x] **v0.3** — 3-stage keyword pipeline (Stage A/B/C), 150+ Chinese term mappings, synonym expansion
- [x] **v0.3.1** — Non-tech domain search precision fix, relevance-weighted result ranking (current)
- [ ] **v0.4** — LLM-powered keyword extraction and semantic similarity
- [ ] **v0.5** — Trend detection and timing analysis
- [ ] **v1.0** — Idea Memory Dataset (opt-in anonymous logging of checks)

## License

MIT — see [LICENSE](LICENSE)

## Try it live

Visit [mnemox.ai/check](https://mnemox.ai/check) to try the idea reality check in your browser — no install required.

## Contact

Built by [Mnemox AI](https://mnemox.ai) · [dev@mnemox.ai](mailto:dev@mnemox.ai)
