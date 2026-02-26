English | [繁體中文](sample_prompts.zh-TW.md)

# Sample prompts for idea_check

## Basic usage

```
Before I build this, check if it already exists:
A CLI tool that converts Figma designs into React components automatically.
```

```
idea_check: AI-powered code review bot for GitHub PRs that automatically suggests fixes
```

```
Check market reality for: a real-time collaborative markdown editor with AI autocomplete
```

## Using with depth

```
Do a quick reality check on: Kubernetes cost optimization dashboard with AI recommendations
```

## Interpreting results

- **reality_signal 0–29**: Greenfield — little existing competition. Validate demand.
- **reality_signal 30–60**: Moderate competition — differentiate or find a niche.
- **reality_signal 61–100**: Crowded space — pivot, specialize, or integrate.

Check `top_similars` to see what already exists and `pivot_hints` for actionable next steps.
