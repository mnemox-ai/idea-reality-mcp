English | [繁體中文](README.zh-TW.md)

# idea-reality-mcp

Pre-build reality check for AI coding agents. Stop building what already exists.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)
[![PyPI](https://img.shields.io/pypi/v/idea-reality-mcp.svg)](https://pypi.org/project/idea-reality-mcp/)
[![Smithery](https://smithery.ai/badge/idea-reality-mcp)](https://idea-reality-mcp--mnemox-ai.run.tools)

<p align="center">
  <img src="assets/demo_flow.gif" alt="idea-reality-mcp demo" width="600" />
</p>

## 30 seconds: Try it now

```bash
uvx idea-reality-mcp
```

Or [try it in your browser](https://mnemox.ai/check) — no install required.

## What this is (and isn't)

`idea-reality-mcp` is an MCP tool that scans **existing supply** — GitHub repos, Hacker News discussions, npm/PyPI packages, and Product Hunt — before you write a single line of code.

It returns a **reality signal** (0-100), top similar projects, and pivot suggestions.

**This is NOT:**
- A business plan generator
- A generic "market research" prompt wrapper
- An AI that tells you if your idea is "good"

**This IS:**
- A supply-side scanner that checks what already exists before you build
- A tooling layer for AI coding agents (MCP protocol)
- Runs in seconds, not hours

## 5 minutes: Three ways to use it

### Scenario 1: "I have a side project idea — should I build it?"

Tell your AI agent:
```
Before I start building, check if this already exists:
a CLI tool that converts Figma designs to React components
```

The agent calls `idea_check` and returns: reality_signal, top competitors, and 3 pivot suggestions.

### Scenario 2: "I need to find competitors and alternatives"

```
idea_check("open source feature flag service", depth="deep")
```

Deep mode scans all 5 sources in parallel (GitHub + HN + npm + PyPI + Product Hunt) and returns ranked similar projects with star counts, package downloads, and HN discussion links.

### Scenario 3: "Build-or-buy sanity check before a sprint"

```
We're about to spend 2 weeks building an internal error tracking tool.
Run a reality check first.
```

If the signal comes back at 85+ with mature open-source alternatives, you just saved your team 2 weeks.

## 1 hour: Integrate into your workflow

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

Restart Claude Desktop. Then ask: *"Check if someone already built a markdown-to-slide-deck converter."*

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

Open Command Palette → "MCP: List Tools" → you should see `idea_check`.

### Claude Code (CLI)

Add to your project's `CLAUDE.md`:

```
When users discuss new project ideas or ask about competition,
use the idea_check tool from idea-reality-mcp.
```

Then just chat naturally — the agent will call the tool when relevant.

### CI: Auto-check on Pull Requests

Add `.github/workflows/idea-check.yml` to run a reality check when PRs touch certain files:

```yaml
name: Idea Reality Check
on:
  pull_request:
    paths: ['docs/proposals/**', 'RFC/**']

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install idea-reality-mcp httpx
      - name: Run idea check
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python -c "
          import asyncio, json
          from idea_reality_mcp.sources.github import search_github_repos
          from idea_reality_mcp.sources.hn import search_hn
          from idea_reality_mcp.scoring.engine import compute_signal, extract_keywords

          async def main():
              idea = open('docs/proposals/latest.md').read()[:500]
              kw = extract_keywords(idea)
              gh = await search_github_repos(kw)
              hn = await search_hn(kw)
              report = compute_signal(gh, hn)
              print(json.dumps(report, indent=2))

          asyncio.run(main())
          "
      - name: Comment on PR
        if: always()
        uses: actions/github-script@v7
        with:
          script: |
            // Parse output and post as PR comment
            github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: '## Idea Reality Check\nSee workflow run for full report.'
            })
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
    "depth": "deep",
    "version": "0.3.1"
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

## Roadmap

- [x] **v0.1** — GitHub + HN search, basic scoring
- [x] **v0.2** — Deep mode (npm, PyPI, Product Hunt), improved keyword extraction
- [x] **v0.3** — 3-stage keyword pipeline, 150+ Chinese term mappings, synonym expansion
- [x] **v0.3.1** — Non-tech domain precision fix, relevance-weighted ranking
- [ ] **v0.4** — LLM-powered keyword extraction and semantic similarity
- [ ] **v0.5** — Trend detection and timing analysis
- [ ] **v1.0** — Idea Memory Dataset (opt-in anonymous logging)

## Found a blind spot?

If the tool missed obvious competitors or returned irrelevant results:

1. [Open an issue](https://github.com/mnemox-ai/idea-reality-mcp/issues/new?template=inaccurate-result.yml) with your idea text and the output
2. We'll improve the keyword extraction for your domain

Zero-friction feedback makes this tool better for everyone.

## License

MIT — see [LICENSE](LICENSE)

## Contact

Built by [Mnemox AI](https://mnemox.ai) · [dev@mnemox.ai](mailto:dev@mnemox.ai)
