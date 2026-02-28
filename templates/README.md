# Agent Instruction Templates

Optional one-line hints to remind your AI agent to run `idea_check` before building.

> **Note:** The MCP tool description already tells agents what `idea_check` does. These hints just make the check proactive — the agent runs it automatically when you start a new project.

## How to Use

1. Install idea-reality-mcp as an MCP server (this is the important part)
2. Optionally, copy the one-line hint into your agent's instruction file
3. Done — your agent will check ideas before coding

## Templates

- [Claude Code](./CLAUDE.md) → `CLAUDE.md` or `.claude/instructions.md`
- [Cursor](./cursorrules.md) → `.cursorrules`
- [Windsurf](./windsurf-rules.md) → `.windsurfrules`
- [GitHub Copilot](./copilot-instructions.md) → `.github/copilot-instructions.md`

## More Examples

See [examples/agent-instructions.md](../examples/agent-instructions.md) for GitHub Actions integration.
