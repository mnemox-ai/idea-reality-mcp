<!-- mcp-name: io.github.mnemox-ai/idea-reality-mcp -->
English | [繁體中文](README.zh-TW.md)

# idea-reality-mcp

**We search. They guess.**

The only idea validator that searches real data. 5 sources. Quantified signal. Zero hallucination.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)
[![PyPI](https://img.shields.io/pypi/v/idea-reality-mcp.svg)](https://pypi.org/project/idea-reality-mcp/)
[![Smithery](https://smithery.ai/badge/idea-reality-mcp)](https://idea-reality-mcp--mnemox-ai.run.tools)
[![GitHub stars](https://img.shields.io/github/stars/mnemox-ai/idea-reality-mcp)](https://github.com/mnemox-ai/idea-reality-mcp)

<p align="center">
  <img src="assets/demo_flow.gif" alt="idea-reality-mcp demo" width="600" />
</p>

## The problem

Every developer has wasted days building something that already exists with 5,000 stars on GitHub.

You ask ChatGPT: *"Is there already a tool that does X?"*

ChatGPT says: *"That's a great idea! There are some similar tools, but you can definitely build something better!"*

**That's not validation. That's cheerleading.**

## What we do instead

```
You: "AI code review tool"

idea-reality-mcp:
├── reality_signal: 90/100
├── GitHub repos: 847
├── Top competitor: reviewdog (9,094 ⭐)
├── npm packages: 56
├── HN discussions: 254
└── Verdict: HIGH — consider pivoting to a niche
```

One gives you encouragement. The other gives you facts.

**Which one do you trust your next 3 months on?**

## Try it now (30 seconds)

```bash
uvx idea-reality-mcp
```

Or [try it in your browser](https://mnemox.ai/check) — no install required.

## Why not just ask ChatGPT?

| | idea-reality-mcp | ChatGPT / ValidatorAI / IdeaProof |
|---|---|---|
| **Data source** | GitHub + HN + npm + PyPI + Product Hunt (real-time) | LLM generation (no real source searched) |
| **Output** | Score 0-100 + real projects with star counts | Text opinion ("Sounds promising!") |
| **Verifiable** | Every number has a source | Not verifiable |
| **Integration** | MCP / CLI / API / Web | Web-only |
| **Price** | Free, open-source, forever | Free trial → paywall |
| **Audience** | Developers (before writing code) | Non-technical founders (before writing pitch decks) |

**TL;DR — We search 5 real databases. They generate opinions.**

## New: AI-powered search intelligence

**Claude Haiku 4.5** now generates optimal search queries from your idea description — in any language — with automatic fallback to our battle-tested dictionary pipeline.

| | Before | Now |
|---|---|---|
| English ideas | ✅ Good | ✅ Good |
| Chinese / non-English ideas | ⚠️ Dictionary lookup (150+ terms) | ✅ Native understanding |
| Ambiguous descriptions | ⚠️ Keyword matching | ✅ Semantic extraction |
| Reliability | 100% (no external API) | 100% (graceful fallback to dictionary) |

The LLM understands your idea. The dictionary is your safety net. **You always get results.**

## Install (5 minutes)

### Claude Desktop

Paste into `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

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

### Cursor

Paste into `.cursor/mcp.json` in your project root:

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

### Claude Code (CLI)

```bash
claude mcp add idea-reality -- uvx idea-reality-mcp
```

### Smithery (Remote)

```bash
npx -y @smithery/cli install idea-reality-mcp --client claude
```

### Optional: Environment variables

```bash
export GITHUB_TOKEN=ghp_...        # Higher GitHub API rate limits
export PRODUCTHUNT_TOKEN=your_...  # Enable Product Hunt (deep mode)
```

### Optional: Agent auto-trigger

The MCP tool description already tells your agent what `idea_check` does. To make it run **proactively** (before every new project), add a one-line hint:

```
When starting a new project, use the idea_check MCP tool to check if similar projects already exist.
```

> Add to your `CLAUDE.md`, `.cursorrules`, `.windsurfrules`, or `.github/copilot-instructions.md`. See [templates/](templates/) for all platforms.

## Usage

### "I have a side project idea — should I build it?"

Tell your AI agent:

```
Before I start building, check if this already exists:
a CLI tool that converts Figma designs to React components
```

The agent calls `idea_check` and returns: reality_signal, top competitors, and pivot suggestions.

### "Find competitors and alternatives"

```
idea_check("open source feature flag service", depth="deep")
```

Deep mode scans all 5 sources in parallel — GitHub repos, HN discussions, npm packages, PyPI packages, and Product Hunt — and returns ranked results.

### "Build-or-buy sanity check before a sprint"

```
We're about to spend 2 weeks building an internal error tracking tool.
Run a reality check first.
```

If the signal comes back at 85+ with mature open-source alternatives, you just saved your team 2 weeks.

## Tool schema

### `idea_check`

| Parameter   | Type                      | Required | Description                          |
|-------------|---------------------------|----------|--------------------------------------|
| `idea_text` | string                    | yes      | Natural-language description of idea |
| `depth`     | `"quick"` \| `"deep"`     | no       | `"quick"` = GitHub + HN (default). `"deep"` = all 5 sources in parallel |

**Output:** `reality_signal` (0-100), `duplicate_likelihood`, `evidence[]`, `top_similars[]`, `pivot_hints[]`, `meta{}`

<details>
<summary>Full output example</summary>

```json
{
  "reality_signal": 72,
  "duplicate_likelihood": "high",
  "evidence": [
    {"source": "github", "type": "repo_count", "query": "...", "count": 342},
    {"source": "github", "type": "max_stars", "query": "...", "count": 15000},
    {"source": "hackernews", "type": "mention_count", "query": "...", "count": 18},
    {"source": "npm", "type": "package_count", "query": "...", "count": 56},
    {"source": "pypi", "type": "package_count", "query": "...", "count": 23},
    {"source": "producthunt", "type": "product_count", "query": "...", "count": 8}
  ],
  "top_similars": [
    {"name": "user/repo", "url": "https://github.com/...", "stars": 15000, "description": "..."}
  ],
  "pivot_hints": [
    "High competition. Consider a niche differentiator...",
    "The leading project may have gaps in...",
    "Consider building an integration or plugin..."
  ],
  "meta": {
    "sources_used": ["github", "hackernews", "npm", "pypi", "producthunt"],
    "keyword_source": "llm",
    "depth": "deep",
    "version": "0.4.0"
  }
}
```

</details>

### Scoring weights

| Mode | GitHub repos | GitHub stars | HN | npm | PyPI | Product Hunt |
|------|-------------|-------------|-----|-----|------|-------------|
| Quick | 60% | 20% | 20% | — | — | — |
| Deep | 25% | 10% | 15% | 20% | 15% | 15% |

If Product Hunt is unavailable (no token), its weight is redistributed automatically.

## CI: Auto-check on Pull Requests

Use [idea-check-action](https://github.com/mnemox-ai/idea-check-action) to validate new feature proposals:

```yaml
name: Idea Reality Check
on:
  issues:
    types: [opened]

jobs:
  check:
    if: contains(github.event.issue.labels.*.name, 'proposal')
    runs-on: ubuntu-latest
    steps:
      - uses: mnemox-ai/idea-check-action@v1
        with:
          idea: ${{ github.event.issue.title }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
```

## Roadmap

- [x] **v0.1** — GitHub + HN search, basic scoring
- [x] **v0.2** — Deep mode (npm, PyPI, Product Hunt), improved keyword extraction
- [x] **v0.3** — 3-stage keyword pipeline, 150+ Chinese term mappings, synonym expansion, LLM-powered search (Render API)
- [x] **v0.4** — Email gate, Score History, Agent Templates, GitHub Action
- [ ] **v0.5** — Temporal signals (trend detection and timing analysis)
- [ ] **v1.0** — Idea Memory Dataset (opt-in anonymous logging)

## Found a blind spot?

If the tool missed obvious competitors or returned irrelevant results:

1. [Open an issue](https://github.com/mnemox-ai/idea-reality-mcp/issues/new?template=inaccurate-result.yml) with your idea text and the output
2. We'll improve the keyword extraction for your domain

## License

MIT — see [LICENSE](LICENSE)

## Contact

Built by [Mnemox AI](https://mnemox.ai) · [dev@mnemox.ai](mailto:dev@mnemox.ai)
