# Agent Instruction Templates

Copy-paste snippets to make your AI coding agent run `idea_check` before building anything new.

## How to Use

1. Pick the template for your AI tool
2. Copy the snippet into your project's instruction file
3. Done — your agent will now check ideas before coding

## Threshold Guide

| Signal | Action | Meaning |
|--------|--------|---------|
| > 80 | STOP | High competition. Warn the user before proceeding. |
| > 60 | CAUTION | Moderate competition. Suggest differentiation. |
| < 40 | GREEN LIGHT | Low competition. Proceed normally. |

## Templates

- [Claude Code](./CLAUDE.md) → `.claude/instructions.md` or `CLAUDE.md`
- [Cursor](./cursorrules.md) → `.cursorrules`
- [Windsurf](./windsurf-rules.md) → `.windsurfrules`
- [GitHub Copilot](./copilot-instructions.md) → `.github/copilot-instructions.md`

## More Examples

See [examples/agent-instructions.md](../examples/agent-instructions.md) for GitHub Actions integration and advanced setups.
