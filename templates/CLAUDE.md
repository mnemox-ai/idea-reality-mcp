# Claude Code — CLAUDE.md / .claude/instructions.md

Add this to your project's `CLAUDE.md` or `.claude/instructions.md`:

---

## Pre-build Reality Check

Before creating any new project, feature, or tool, run `idea_check` with a one-line description.
- If reality_signal > 80: STOP. Warn me about high competition before proceeding.
- If reality_signal > 60: Proceed with caution. Suggest how to differentiate.
- If reality_signal < 40: Green light. Proceed normally.

---

> Requires: [idea-reality-mcp](https://github.com/mnemox-ai/idea-reality-mcp) configured as an MCP server.
