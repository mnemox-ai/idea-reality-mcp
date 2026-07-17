<!-- mcp-name: io.github.mnemox-ai/idea-reality-mcp -->
English | [繁體中文](docs/zh/README.zh-TW.md)

# idea-reality-mcp

**How to check if someone already built your app idea — automatically.**

idea-reality-mcp is an MCP server that scans GitHub, npm, PyPI, Hacker News, and Stack Overflow to check if your startup idea already exists. It returns a 0–100 reality score with evidence, trend detection, and pivot suggestions — so your AI agent can decide whether to build, pivot, or kill the idea before writing any code.

**When to use this:** You're about to start a new project and want to know if similar tools already exist, how competitive the space is, and whether the market is growing or declining.

> **Not just checking — building it?** After a reality check, open your idea as a public project on **[AngelRun](https://angelrun.vercel.app/new?utm_source=idea-reality&utm_medium=readme&utm_campaign=demand-cta)** — ship updates, climb the season, and get seen by angels.

[![PyPI](https://img.shields.io/pypi/v/idea-reality-mcp.svg)](https://pypi.org/project/idea-reality-mcp/)
[![Smithery](https://smithery.ai/badge/idea-reality-mcp)](https://smithery.ai/server/idea-reality-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-277%20passing-brightgreen.svg)]()
[![GitHub stars](https://img.shields.io/github/stars/mnemox-ai/idea-reality-mcp)](https://github.com/mnemox-ai/idea-reality-mcp)
[![Downloads](https://static.pepy.tech/badge/idea-reality-mcp)](https://pepy.tech/project/idea-reality-mcp)

<p align="center">
  <a href="cursor://anysphere.cursor-deeplink/mcp/install?name=idea-reality&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22idea-reality-mcp%22%5D%7D">
    <img src="https://cursor.com/deeplink/mcp-install-dark.svg" alt="Install in Cursor" height="32">
  </a>
</p>

## How it works

1. **Describe your idea** in plain English — e.g. "a CLI tool that converts Figma designs to React components"
2. **idea_check scans 5 databases** in parallel (GitHub repos + stars, Hacker News discussions, npm/PyPI packages, Stack Overflow questions)
3. **Get a 0–100 reality score** with trend direction (accelerating/stable/declining), top competitors, and AI-generated pivot suggestions

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

```bash
# 1. Install
uvx idea-reality-mcp

# 2. Add to your agent
claude mcp add idea-reality -- uvx idea-reality-mcp   # Claude Code
```

**3. Ask your agent:** *"Before I start building, check if this already exists: a CLI tool that converts Figma designs to React components"*

That's it. The agent calls `idea_check` and returns: reality_signal, top competitors, and pivot suggestions.

<details>
<summary>Other MCP clients</summary>

**Claude Desktop / Cursor** — add to config JSON:

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

Config location: **macOS** `~/Library/Application Support/Claude/claude_desktop_config.json` · **Windows** `%APPDATA%\Claude\claude_desktop_config.json` · **Cursor** `.cursor/mcp.json`

**Smithery** (remote, no local install):

```bash
npx -y @smithery/cli install idea-reality-mcp --client claude
```

</details>

## Setup & Configuration

First-time guided setup:

```bash
idea-reality setup
```

This walks you through:
1. **Terms acceptance** — data collection policy and disclaimer
2. **Platform detection** — auto-detects Claude Desktop, Claude Code, Cursor, Windsurf, Cline
3. **Config generation** — prints the exact JSON snippet for your platform
4. **Health check** — verifies MCP server, tools, and scoring engine

### Platform Configs

```bash
idea-reality config              # interactive menu
idea-reality config claude_code  # auto-installs via CLI
idea-reality config cursor       # prints Cursor config
idea-reality config raw_json     # generic MCP JSON
```

Supported: Claude Desktop · Claude Code · Cursor · Windsurf · Cline · Smithery · Docker

### Health Check

```bash
idea-reality doctor        # core checks (~2s)
idea-reality doctor --full # + GitHub API, all 6 sources, Anthropic API
```

## Usage

**MCP tool call** (any MCP-compatible agent):

```json
{
  "tool": "idea_check",
  "arguments": {
    "idea_text": "a CLI tool that converts Figma designs to React components",
    "depth": "deep"
  }
}
```

**REST API** (no MCP required):

```bash
curl -X POST https://idea-reality-mcp.onrender.com/api/check \
  -H "Content-Type: application/json" \
  -d '{"idea_text": "AI code review tool", "depth": "quick"}'
```

**Python**:

```python
import httpx

resp = httpx.post("https://idea-reality-mcp.onrender.com/api/check", json={
    "idea_text": "AI code review tool",
    "depth": "deep"
})
print(resp.json()["reality_signal"])  # 0-100
```

Free. No API key required.

## Why not just Google it?

**Your AI agent never Googles anything before it starts building.** `idea_check` runs *inside* your agent — it triggers automatically whether you remember or not.

| | Google | ChatGPT | idea-reality-mcp |
|---|---|---|---|
| **Who runs it** | You, manually | You, manually | Your agent, automatically |
| **Output** | 10 blue links | "Sounds promising!" | Score 0-100 + evidence |
| **Sources** | Web pages | None (LLM) | GitHub + HN + npm + PyPI + PH + SO |
| **Price** | Free | Paywall | Free & open-source (MIT) |

## Modes

| Mode | Sources | Use case |
|------|---------|----------|
| **quick** (default) | GitHub + HN | Fast sanity check, < 3 seconds |
| **deep** | GitHub + HN + npm + PyPI + Stack Overflow | Full competitive scan |

<details>
<summary>Scoring weights</summary>

| Source | Quick | Deep |
|--------|-------|------|
| GitHub repos | 60% | 22% |
| GitHub stars | 20% | 9% |
| Hacker News | 20% | 14% |
| npm | — | 18% |
| PyPI | — | 13% |
| Stack Overflow | — | 10% |

If a source is unavailable, its weight is redistributed automatically — so the deep-mode
weights above are renormalised over the sources that actually answered.

> **Product Hunt was removed on 2026-07-17.** It had carried 14% of the deep-mode weight
> since launch and had never returned a single result: the adapter asked for
> `posts(search: $query)`, and Product Hunt's API has no text search on posts at all
> (`Field 'posts' doesn't accept argument 'search'`). Its weight is now redistributed to
> sources that answer. If you need it back, it needs a real search surface — not a token.

</details>

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
```

`PRODUCTHUNT_TOKEN` no longer does anything — the source is disabled and ignores it.
Setting it used to be worse than useless: it un-skipped a source whose query the API
rejects, so it reported "0 competitors on Product Hunt" into 14% of the deep score.

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
- [x] **v0.6** — Onboarding CLI (`idea-reality setup`, `config`, `doctor`)
- [ ] **v1.0** — Idea Memory Dataset (opt-in anonymous logging)

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=mnemox-ai/idea-reality-mcp&type=Date)](https://star-history.com/#mnemox-ai/idea-reality-mcp&Date)

## Found a blind spot?

If the tool missed obvious competitors or returned irrelevant results:

1. [Open an issue](https://github.com/mnemox-ai/idea-reality-mcp/issues/new?template=inaccurate-result.yml) with your idea text and the output
2. We'll improve the keyword extraction for your domain

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) ([繁體中文](docs/zh/CONTRIBUTING.zh-TW.md)).

## License

MIT — see [LICENSE](LICENSE)

Built by [Mnemox AI](https://mnemox.ai) · [dev@mnemox.ai](mailto:dev@mnemox.ai)
