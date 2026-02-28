# Reddit r/ClaudeAI Draft

## Title options (pick one):

**Option A:** I added 4 lines to my CLAUDE.md and now Claude Code checks if my idea already exists before writing any code

**Option B:** Built an MCP server that lets Claude check GitHub, HN, npm and PyPI before it starts coding — saved me from building 3 things that already existed

**Option C:** My CLAUDE.md now has a "reality check" step — Claude refuses to build anything without scanning the market first

---

## Flair: Self-Promotion (or "Built with Claude" if available)

---

## Post body:

I kept running into the same problem: I'd ask Claude to build something, spend 2 hours in a coding session, then discover three existing tools that do the same thing.

So I built an MCP server called idea-reality-mcp that scans GitHub repos, Hacker News discussions, npm packages, and PyPI before Claude writes a single line of code. It returns a "reality signal" from 0-100 — the higher the number, the more competition already exists.

The key part: I added this to my CLAUDE.md:

```
## Pre-build Reality Check

Before creating any new project, feature, or tool, run `idea_check` with a one-line description.
- If reality_signal > 80: STOP. Warn me about high competition before proceeding.
- If reality_signal > 60: Proceed with caution. Suggest how to differentiate.
- If reality_signal < 40: Green light. Proceed normally.
```

Now every time I say "build me a ___", Claude automatically checks the market first. Example output:

```
Reality Signal: 87/100

Top competitors found:
- existing-tool-1 (2.3k stars)
- existing-tool-2 (890 stars)

Recommendation: High competition. Consider focusing on [specific gap].
```

**What it actually searches (not LLM guessing):**
- GitHub Search API (repo count + star distribution)
- HN Algolia API (discussion volume)
- npm registry (quick mode skips this)
- PyPI (deep mode)
- Product Hunt (optional, needs token)

The difference from just asking ChatGPT "does this exist?" — this actually searches real APIs and gives you numbers. LLMs guess. This searches.

It's open source, runs as a standard MCP server (stdio or HTTP):

GitHub: https://github.com/mnemox-ai/idea-reality-mcp

Works with Claude Code, Cursor, Windsurf, and any MCP-compatible client. There are ready-made instruction templates for each.

Happy to answer questions about the MCP implementation or the scoring formula.

---

## Notes for Sean:

### Why this should work:
1. **Personal story opening** — "I kept running into the same problem"
2. **CLAUDE.md angle** — r/ClaudeAI loves config sharing (a config repo got 1,100 stars from one post)
3. **Shows actual output** — not just marketing, technical substance
4. **"We search. They guess."** embedded naturally
5. **Ends with invitation to discuss** — not a CTA to download
6. **One GitHub link only** — not spammy
7. **No emoji, no hype words** — reads like a developer talking to developers

### What NOT to do:
- Don't mention download numbers or stars (looks like bragging)
- Don't say "v0.3.4" or version numbers (nobody cares)
- Don't link PyPI, Smithery, MCP Registry (one link is enough)
- Don't mention it's your startup product
- Don't cross-post to multiple subreddits at once (Reddit flags this)

### Timing:
- Post during US working hours (9-11am PST / 12-2pm EST)
- Weekdays get more developer eyeballs than weekends
- Tuesday-Thursday is optimal

### If it gets removed:
- Check if account age / karma is too low
- Message the mods with a polite note: "Hey, I shared a tool I built as an MCP server for Claude Code. Was this removed for a specific reason? Happy to adjust the post."
- Don't repost immediately — wait 24h
