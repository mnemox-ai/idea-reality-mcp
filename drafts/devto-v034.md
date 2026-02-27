---
title: "I asked ChatGPT if my idea was original. GitHub said 847 repos already exist."
published: false
description: Why AI opinions are dangerous for developers, and how real-time data search beats LLM cheerleading
tags: ai, mcp, opensource, webdev
cover_image: https://raw.githubusercontent.com/mnemox-ai/idea-reality-mcp/main/assets/devto-cover.png
---

Last month I mass-deleted 6 hours of code.

Claude had spent the entire time enthusiastically helping me build something that already had 12 competitors on GitHub. The top one had over 1,000 stars.

Here's the pattern every developer hits:

1. Developer has an idea
2. Asks ChatGPT: "Is this original?"
3. ChatGPT says: "That's a great idea! Here's how to build it..."
4. Developer spends 2 weeks building
5. Searches GitHub → finds 847 repos doing the same thing
6. The top one has 9,000 stars and a funded team behind it

**The AI didn't lie. It just didn't search.**

## Why "just Google it" doesn't work

You might think: just search before you build. But manual searching has problems:

- **You search GitHub** → find repos, but miss npm packages and HN discussions
- **You search one query** → miss synonyms ("LLM monitoring" vs "AI observability" vs "model telemetry")
- **You check star counts** → but don't check PyPI/npm for existing packages
- **You spend 30 minutes** → and still aren't sure if you missed something

The real issue: there's no standardized way to do a comprehensive market scan across all developer platforms at once.

## What if your AI agent searched before coding?

I built [idea-reality-mcp](https://github.com/mnemox-ai/idea-reality-mcp) — an MCP server that searches real data before you build.

One command. Five sources. Quantified signal.

```
"AI code review tool"
→ reality_signal: 90/100
→ 847 GitHub repos (top: reviewdog, 9,094 ⭐)
→ 254 Hacker News mentions
→ Verdict: "Extremely high existing coverage"
```

It searches GitHub, Hacker News, npm, PyPI, and Product Hunt in parallel, then returns a 0-100 reality signal based on actual API data — not LLM opinions.

## We search. They guess.

| | ChatGPT / Copilot | idea-reality-mcp |
|---|---|---|
| **Method** | Generates opinion from training data | Searches live APIs in real-time |
| **Sources** | None (hallucination-prone) | GitHub, HN, npm, PyPI, Product Hunt |
| **Output** | "Great idea!" (usually) | reality_signal: 73, 2,341 repos found |
| **Verifiable** | No | Yes — every number links to a real API |
| **Speed** | Instant | ~3 seconds (parallel async) |

## How it works (30 seconds)

```bash
# Install
uvx idea-reality-mcp

# Or add to Claude Desktop / Cursor config:
{
  "mcpServers": {
    "idea-reality": {
      "command": "uvx",
      "args": ["idea-reality-mcp"]
    }
  }
}
```

Then ask your AI agent: *"Check if anyone has built a CLI tool for DNS propagation monitoring"*

The agent calls `idea_check` automatically and gets back:
- **reality_signal**: 0-100 score
- **Top similar projects** with star counts
- **HN discussion** evidence
- **Pivot suggestions** if the space is crowded

No API key needed. No account. No storage. It's a protocol, not a SaaS.

## The scoring is intentionally simple

```
Quick mode: GitHub repos (60%) + stars (20%) + HN mentions (20%)
Deep mode:  GitHub (25%) + stars (10%) + HN (15%) + npm (20%) + PyPI (15%) + PH (15%)
```

Every weight is documented. Every number comes from a real API call you can verify. No ML black box.

I chose explainability over sophistication because when you're deciding whether to invest weeks into a project, you need to trust the data — not a magic number.

## Make your AI check automatically

The most powerful pattern: add one line to your AI agent's instructions.

**For Claude Code** (`.claude/instructions.md`):
```
Before starting any new project, run idea_check to verify the idea hasn't been built already.
```

**For Cursor** (`.cursorrules`):
```
When the user describes a new project idea, always run idea_check first.
```

Now your agent will search before coding — every time, automatically.

## What it found that surprised me

Some results from real checks on the [web demo](https://mnemox.ai/check):

![idea-reality-mcp demo result](https://raw.githubusercontent.com/mnemox-ai/idea-reality-mcp/main/assets/demo-result.png)

- **"MCP server for monitoring LLM calls"** → Signal 68. Turns out there are several observability tools, but none MCP-native. Worth building with differentiation.
- **"AI-powered code review"** → Signal 90. Massively crowded. reviewdog alone has 9K stars. Don't.
- **"Pet acupuncture booking app"** → Signal 12. Almost nothing exists. Niche, but the market might also be tiny.

The signal doesn't tell you whether to build — it tells you what you're walking into, backed by data.

## Open source, zero storage

- **120 tests**, all passing
- **MIT license**
- **Zero storage** — nothing is logged or saved
- **Zero accounts** — no signup, no API key needed
- **Works offline** (dictionary-based keyword extraction for MCP mode)
- Published on **PyPI**, **MCP Registry**, **Smithery**, and 10+ directories

The web demo at [mnemox.ai/check](https://mnemox.ai/check) uses Claude Haiku for smarter keyword extraction, but the MCP tool itself needs zero external dependencies.

## Try it

- **GitHub**: [mnemox-ai/idea-reality-mcp](https://github.com/mnemox-ai/idea-reality-mcp)
- **Web demo**: [mnemox.ai/check](https://mnemox.ai/check)
- **Install**: `uvx idea-reality-mcp`
- **MCP Registry**: `io.github.mnemox-ai/idea-reality-mcp`

If you use Claude Code or Cursor daily, add it to your agent instructions. It takes 30 seconds and saves hours.

What's the worst "I should have searched first" moment you've had? Drop your idea in the comments — I'll run it through the tool and reply with the real numbers. 🔍

---

*Built by [Sean](https://github.com/mnemox-ai) at Mnemox.*
