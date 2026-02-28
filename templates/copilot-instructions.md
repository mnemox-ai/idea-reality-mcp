# GitHub Copilot — .github/copilot-instructions.md

Add this to your project's `.github/copilot-instructions.md`:

---

## Pre-build Reality Check

Before creating any new project, feature, or tool, use the idea_check MCP tool with a one-line description.
- If reality_signal > 80: STOP. Warn the user about high competition before proceeding.
- If reality_signal > 60: Proceed with caution. Suggest how to differentiate.
- If reality_signal < 40: Green light. Proceed normally.

---

> Requires: idea-reality-mcp configured as an MCP server in GitHub Copilot settings.
