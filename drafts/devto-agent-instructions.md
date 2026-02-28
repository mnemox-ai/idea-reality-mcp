---
title: "Add a pre-build reality check to your AI agent — one line, every project"
published: false
tags: ai, mcp, opensource, productivity
---

Your AI coding agent just spent 3 hours building a DNS propagation checker. You were impressed. The code was clean, tests passed, CLI looked great. Then you searched GitHub: 47 repos doing exactly the same thing. One of them has 2,000+ stars and a published npm package.

The agent never checked. You never asked it to. Nobody does.

This is the most common failure mode of AI-assisted development. Not bad code. Not wrong architecture. Just building something that already exists, because the agent was never told to look first.

## The blind spot

Claude Code, Cursor, Windsurf, GitHub Copilot -- they are all excellent at writing code. Give them a spec and they will produce working software. But they have zero awareness of what already exists in the ecosystem.

They don't search GitHub before scaffolding a new project. They don't check if there's already a popular npm package for what you described. They don't scan Hacker News to see if someone shipped the same idea last week.

The result: you invest hours (or days) into something that already has mature alternatives. Or you ship a clone without knowing, then find out when someone drops a link in your comments section.

## One tool, five sources, real data

[idea-reality-mcp](https://github.com/mnemox-ai/idea-reality-mcp) is an MCP server that searches five real-time sources -- GitHub, Hacker News, npm, PyPI, and Product Hunt -- and returns a `reality_signal` score from 0 to 100.

It uses live API data, not LLM opinions. Every number in the result traces back to an actual search query you can verify. The scoring formula is documented and intentionally simple: no ML, no black box.

Add one line to your agent's instructions file and it checks automatically before writing any new code. Here is what that looks like in practice.

## What the results look like

**Example 1: "CLI tool for DNS propagation monitoring"**

```
reality_signal: 75
top_competitor: dns-propagation-checker (1,847 stars)
github_repos: 47
npm_packages: 12
hn_mentions: 23
verdict: High competition. Multiple mature tools exist.
```

Your agent sees signal 75 and warns you: "There are 47 existing repos in this space, including one with nearly 2K stars. Want me to find a differentiation angle instead?"

**Example 2: "MCP server for pre-build idea validation"**

```
reality_signal: 15
top_competitor: none with significant traction
github_repos: 3
npm_packages: 0
hn_mentions: 2
verdict: Low competition. Greenfield opportunity.
```

Signal 15. The agent proceeds with confidence. The space is open.

**Example 3: "React component library for dashboards"**

```
reality_signal: 85
top_competitor: tremor (4,200 stars)
github_repos: 312
npm_packages: 89
hn_mentions: 67
verdict: Very crowded. Strong incumbents with active development.
```

Signal 85. The agent stops and says: "This space has 312 repos and multiple well-funded projects. I'd recommend either targeting a specific niche or contributing to an existing library."

## Setup: one snippet per platform

The most effective pattern is adding a pre-build check directly to your agent's instruction file. The agent reads these instructions at the start of every session and follows them automatically.

### Claude Code -- `CLAUDE.md`

```markdown
## Pre-build Reality Check
Before creating any new project, feature, or tool, run idea_check.
- reality_signal > 80: STOP. Warn the user about existing competition.
- reality_signal > 60: Caution. Show competitors and suggest differentiation.
- reality_signal < 40: Green light. Proceed with implementation.
```

### Cursor -- `.cursorrules`

```markdown
## Pre-build Reality Check
Before creating any new project, feature, or tool, run idea_check.
- reality_signal > 80: STOP. Warn the user about existing competition.
- reality_signal > 60: Caution. Show competitors and suggest differentiation.
- reality_signal < 40: Green light. Proceed with implementation.
```

### Windsurf -- `.windsurfrules`

```markdown
## Pre-build Reality Check
Before creating any new project, feature, or tool, run idea_check.
- reality_signal > 80: STOP. Warn the user about existing competition.
- reality_signal > 60: Caution. Show competitors and suggest differentiation.
- reality_signal < 40: Green light. Proceed with implementation.
```

### GitHub Copilot -- `.github/copilot-instructions.md`

```markdown
## Pre-build Reality Check
Before creating any new project, feature, or tool, run idea_check.
- reality_signal > 80: STOP. Warn the user about existing competition.
- reality_signal > 60: Caution. Show competitors and suggest differentiation.
- reality_signal < 40: Green light. Proceed with implementation.
```

The snippet is identical across platforms. Drop it into the right file and your agent gains market awareness permanently.

## How it works under the hood

The tool connects via MCP (Model Context Protocol), so any MCP-compatible agent can call it natively. When triggered:

1. Your idea text goes through a 3-stage keyword extraction pipeline (90+ intent anchors, 80+ synonym expansions).
2. Five sources are queried in parallel using async HTTP.
3. Results are scored with a weighted formula: GitHub repo count, star concentration, npm/PyPI package density, HN discussion volume, and Product Hunt presence.
4. The agent receives a structured response with the signal, evidence list, top competitors, and pivot suggestions.

Total latency: roughly 3 seconds for a deep scan across all five sources.

## Install

```bash
# pip
pip install idea-reality-mcp

# uv (recommended)
uvx idea-reality-mcp
```

No API key required. No account. No data storage. Works entirely through live, public API queries.

Set `GITHUB_TOKEN` for higher rate limits (optional). Set `PRODUCTHUNT_TOKEN` to include Product Hunt data (optional).

## Try it now

- **GitHub**: [mnemox-ai/idea-reality-mcp](https://github.com/mnemox-ai/idea-reality-mcp)
- **Web demo**: [mnemox.ai/check](https://mnemox.ai/check) -- test any idea without installing anything
- **Agent instruction templates**: [examples/agent-instructions.md](https://github.com/mnemox-ai/idea-reality-mcp/blob/master/examples/agent-instructions.md)
- **MCP Registry**: `io.github.mnemox-ai/idea-reality-mcp`

Your agent does not need to guess. Make it search.

---

*Built by [Sean](https://github.com/mnemox-ai) at Mnemox. 120 tests passing. MIT licensed.*
