# Agent Instructions — Optional One-Line Hints

Once idea-reality-mcp is installed as an MCP server, the tool description tells your agent everything it needs. These optional hints just make the check **proactive** — the agent runs it automatically when you start a new project.

## Claude Code — `CLAUDE.md`

```
When starting a new project, use the idea_check MCP tool to check if similar projects already exist.
```

## Cursor — `.cursorrules`

```
When starting a new project, use the idea_check MCP tool to check if similar projects already exist.
```

## Windsurf — `.windsurfrules`

```
When starting a new project, use the idea_check MCP tool to check if similar projects already exist.
```

## GitHub Copilot — `.github/copilot-instructions.md`

```
When starting a new project, use the idea_check MCP tool to check if similar projects already exist.
```

## GitHub Actions — Auto-check proposals

Use [idea-check-action](https://github.com/mnemox-ai/idea-check-action) to validate new feature proposals in CI:

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

## Why add this?

Without the hint, your agent only runs `idea_check` when you explicitly ask. With it, the agent checks proactively before building — preventing wasted effort on ideas that already have 5,000-star implementations on GitHub.
