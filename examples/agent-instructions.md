# Recommended: Add idea-reality-mcp to your AI agent instructions

Copy-paste one of these snippets into your project to make your AI agent automatically validate ideas before building.

## Claude Code — `CLAUDE.md`

Add to your project's `CLAUDE.md`:

```markdown
## Before building anything new

Before starting any new tool, feature, library, or project, always run `idea_check` first
to verify the idea hasn't already been built. If reality_signal > 80, discuss alternatives
with the user before proceeding.
```

## Claude Desktop / Cursor — System prompt

Add to your Claude Desktop system prompt or `.cursor/rules`:

```
When the user describes a new project idea or asks you to build something from scratch:
1. Run idea_check(idea_text=<summarize the idea>, depth="deep") first
2. If reality_signal > 80: warn the user and show top competitors
3. If reality_signal > 60: mention similar projects but proceed if user confirms
4. If reality_signal < 40: proceed — the space is relatively open
```

## GitHub Actions — Auto-check proposals

Add `.github/workflows/idea-check.yml` to automatically validate new feature proposals:

```yaml
name: Idea Reality Check
on:
  pull_request:
    paths: ['docs/proposals/**', 'RFC/**']
  issues:
    types: [opened]

jobs:
  check:
    if: contains(github.event.issue.labels.*.name, 'proposal') || github.event_name == 'pull_request'
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
```

## Why add this?

Without this instruction, your AI agent will happily spend hours building something that already exists with 5,000 stars on GitHub. Adding a single line to your instructions file prevents this — automatically, every time.
