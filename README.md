<!-- mcp-name: io.github.mnemox-ai/idea-reality-mcp -->
English | [繁體中文](README.zh-TW.md)

# idea-reality-mcp

**Stop building what already exists.**

You spend 3 weeks coding a tool. Ship it. Then find out someone already built it — with 5,000 stars.

`idea_check` scans GitHub, Hacker News, npm, PyPI, Product Hunt, and Stack Overflow *before* your agent writes a single line of code. One call. Six databases. A score instead of a guess.

[![PyPI](https://img.shields.io/pypi/v/idea-reality-mcp.svg)](https://pypi.org/project/idea-reality-mcp/)
[![Smithery](https://smithery.ai/badge/idea-reality-mcp)](https://smithery.ai/server/idea-reality-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-275%20passing-brightgreen.svg)]()
[![GitHub stars](https://img.shields.io/github/stars/mnemox-ai/idea-reality-mcp)](https://github.com/mnemox-ai/idea-reality-mcp)
[![Downloads](https://static.pepy.tech/badge/idea-reality-mcp)](https://pepy.tech/project/idea-reality-mcp)

<p align="center">
  <a href="cursor://anysphere.cursor-deeplink/mcp/install?name=idea-reality&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22idea-reality-mcp%22%5D%7D">
    <img src="https://cursor.com/deeplink/mcp-install-dark.svg" alt="Install in Cursor" height="32">
  </a>
</p>

## What you get

```
You: "AI code review tool"

idea_check →
├── reality_signal: 92/100
├── trend: accelerating ↗
├── market_momentum: 73/100
├── GitHub repos: 847 (45% created in last 6 months)
├── Top competitor: reviewdog (9,094 ⭐)
├── npm packages: 56
├── HN discussions: 254 (trending up)
└── Verdict: HIGH — market is accelerating, find a niche fast
```

One score. Six sources. Trend detection. Your agent decides what to do next.

<p align="center">
  <a href="https://mnemox.ai/check"><strong>Try it in your browser — no install</strong></a>
</p>

## Quick Start

**1. Install and run**

```bash
uvx idea-reality-mcp
```

**2. Add to your MCP client**

<details>
<summary>Claude Desktop — <code>claude_desktop_config.json</code></summary>

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

Config location: **macOS** `~/Library/Application Support/Claude/claude_desktop_config.json` · **Windows** `%APPDATA%\Claude\claude_desktop_config.json`

</details>

<details>
<summary>Claude Code</summary>

```bash
claude mcp add idea-reality -- uvx idea-reality-mcp
```

</details>

<details>
<summary>Cursor — <code>.cursor/mcp.json</code></summary>

Or click the button above for one-click install.

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

</details>

<details>
<summary>Smithery (remote, no local install)</summary>

```bash
npx -y @smithery/cli install idea-reality-mcp --client claude
```

</details>

**3. Use it**

Tell your agent:

```
Before I start building, check if this already exists:
a CLI tool that converts Figma designs to React components
```

That's it. The agent calls `idea_check` and returns: reality_signal, top competitors, and pivot suggestions.

## Why not just Google it?

**Google works — if you remember to use it.** The problem isn't search quality. It's that your AI agent never Googles anything before it starts building.

`idea_check` runs **inside** your agent. It triggers automatically. The search happens whether you remember or not.

| | Google | ChatGPT / SaaS validators | idea-reality-mcp |
|---|---|---|---|
| **Who runs it** | You, manually | You, manually | Your agent, automatically |
| **Output** | 10 blue links | "Sounds promising!" | Score 0-100 + evidence + competitors |
| **Sources** | Web pages | None (LLM generation) | GitHub + HN + npm + PyPI + PH + SO |
| **Workflow** | Copy-paste between tabs | Separate app | MCP / CLI / API / CI |
| **Price** | Free | Free trial → paywall | Free & open-source (MIT) |

## Modes

| Mode | Sources | Use case |
|------|---------|----------|
| **quick** (default) | GitHub + HN | Fast sanity check, < 3 seconds |
| **deep** | GitHub + HN + npm + PyPI + Product Hunt + Stack Overflow | Full competitive scan |

### Scoring weights

| Source | Quick | Deep |
|--------|-------|------|
| GitHub repos | 60% | 22% |
| GitHub stars | 20% | 9% |
| Hacker News | 20% | 14% |
| npm | — | 18% |
| PyPI | — | 13% |
| Product Hunt | — | 14% |
| Stack Overflow | — | 10% |

If Product Hunt or Stack Overflow is unavailable, their weight is redistributed automatically.

## Tool schema

### `idea_check`

| Parameter   | Type                      | Required | Description                          |
|-------------|---------------------------|----------|--------------------------------------|
| `idea_text` | string                    | yes      | Natural-language description of idea |
| `depth`     | `"quick"` \| `"deep"`     | no       | `"quick"` = GitHub + HN (default). `"deep"` = all 6 sources |

<details>
<summary>Full output example</summary>

```json
{
  "reality_signal": 72,
  "duplicate_likelihood": "high",
  "trend": "accelerating",
  "sub_scores": { "market_momentum": 73 },
  "evidence": [
    {"source": "github", "type": "repo_count", "query": "...", "count": 342},
    {"source": "github", "type": "max_stars", "query": "...", "count": 15000},
    {"source": "hackernews", "type": "mention_count", "query": "...", "count": 18},
    {"source": "npm", "type": "package_count", "query": "...", "count": 56},
    {"source": "pypi", "type": "package_count", "query": "...", "count": 23},
    {"source": "producthunt", "type": "product_count", "query": "...", "count": 8},
    {"source": "stackoverflow", "type": "question_count", "query": "...", "count": 120}
  ],
  "top_similars": [
    {"name": "user/repo", "url": "https://github.com/...", "stars": 15000, "description": "..."}
  ],
  "pivot_hints": [
    "High competition. Consider a niche differentiator...",
    "The leading project may have gaps in..."
  ]
}
```

</details>

## REST API

Not using MCP? Call it directly:

```bash
curl -X POST https://idea-reality-mcp.onrender.com/api/check \
  -H "Content-Type: application/json" \
  -d '{"idea_text": "AI code review tool", "depth": "quick"}'
```

Free. No API key required.

## CI: Auto-check on Pull Requests

Use [idea-check-action](https://github.com/mnemox-ai/idea-check-action) to validate feature proposals:

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

## Optional config

```bash
export GITHUB_TOKEN=ghp_...        # Higher GitHub API rate limits
export PRODUCTHUNT_TOKEN=your_...  # Enable Product Hunt (deep mode)
```

**Auto-trigger:** Add one line to your `CLAUDE.md`, `.cursorrules`, or `.github/copilot-instructions.md`:

```
When starting a new project, use the idea_check MCP tool to check if similar projects already exist.
```

## Roadmap

- [x] **v0.1** — GitHub + HN search, basic scoring
- [x] **v0.2** — Deep mode (npm, PyPI, Product Hunt), keyword extraction
- [x] **v0.3** — 3-stage keyword pipeline, Chinese term mappings, LLM-powered search
- [x] **v0.4** — Score History, Agent Templates, GitHub Action
- [x] **v0.5** — Temporal signals, trend detection, market momentum
- [ ] **v1.0** — Idea Memory Dataset (opt-in anonymous logging)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=mnemox-ai/idea-reality-mcp&type=Date)](https://star-history.com/#mnemox-ai/idea-reality-mcp&Date)

## Found a blind spot?

If the tool missed obvious competitors or returned irrelevant results:

1. [Open an issue](https://github.com/mnemox-ai/idea-reality-mcp/issues/new?template=inaccurate-result.yml) with your idea text and the output
2. We'll improve the keyword extraction for your domain

## License

MIT — see [LICENSE](LICENSE)

Built by [Mnemox AI](https://mnemox.ai) · [dev@mnemox.ai](mailto:dev@mnemox.ai)
