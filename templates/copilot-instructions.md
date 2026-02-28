# GitHub Copilot — .github/copilot-instructions.md

Optionally, add a one-line hint to your project's `.github/copilot-instructions.md`:

```
When starting a new project, use the idea_check MCP tool to check if similar projects already exist.
```

> The MCP tool description already tells the agent what `idea_check` does and what it returns. This hint just reminds it to run the check proactively.
>
> Requires: idea-reality-mcp configured as an MCP server in GitHub Copilot settings.
