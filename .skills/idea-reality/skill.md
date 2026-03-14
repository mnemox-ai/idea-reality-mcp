---
name: idea-reality
version: 1.0.0
description: Pre-build reality check — scan GitHub, HN, npm, PyPI, Product Hunt for existing prior art before you build.
metadata:
  openclaw:
    emoji: "\U0001F50D"
    requires:
      bins:
        - python3
    install: pip install idea-reality-mcp
---

# Idea Reality Check

Scans existing projects across GitHub, Hacker News, npm, PyPI, and Product Hunt. Returns a `reality_signal` score (0-100) indicating how much prior art already exists for a given idea.

## When to Use

- Before starting a new project — check if it already exists
- User asks "has anyone built X?" or "does X exist?"
- Validating competition or market saturation for an idea
- Comparing existing solutions before deciding to build
- Works with English and Traditional Chinese input

## How It Works

1. Extracts keywords from the idea description (dictionary-based, no LLM dependency)
2. Queries sources in parallel based on depth mode
3. Computes a weighted `reality_signal` score using log-curve continuous scoring
4. Returns evidence, similar projects, and actionable pivot hints

### Depth Modes

| Mode | Sources | Weights |
|------|---------|---------|
| `quick` | GitHub + HN | repos 60%, stars 20%, HN 20% |
| `deep` | GitHub + HN + npm + PyPI + Product Hunt | repos 25%, stars 10%, HN 15%, npm 20%, PyPI 15%, PH 15% |

## Usage

### Quick mode (default)

```python
idea_check(idea_text="CLI tool for managing Docker containers", depth="quick")
```

### Deep mode

```python
idea_check(idea_text="MCP server for stock trading memory", depth="deep")
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `idea_text` | `str` | Yes | — | Natural-language description of the idea |
| `depth` | `"quick" \| "deep"` | No | `"quick"` | Source coverage level |

## Output Format

```json
{
  "reality_signal": 42,
  "duplicate_likelihood": "medium",
  "sub_scores": {
    "competition_density": 55,
    "market_maturity": 30,
    "community_buzz": 20,
    "ecosystem_depth_npm": 45,
    "ecosystem_depth_pypi": 38,
    "product_launches": 12,
    "market_momentum": 65
  },
  "trend": "stable",
  "evidence": [
    {
      "source": "github",
      "type": "repo_count",
      "query": "docker cli",
      "count": 120,
      "detail": "120 repos found across queries",
      "queried_at": "2026-03-14T10:00:00+00:00"
    }
  ],
  "top_similars": [
    {
      "name": "lazydocker",
      "url": "https://github.com/jesseduffield/lazydocker",
      "stars": 35000,
      "updated": "2026-03-10",
      "description": "The lazier way to manage everything docker"
    }
  ],
  "pivot_hints": [
    "Moderate competition exists. Focus on a specific use case..."
  ],
  "meta": {
    "checked_at": "2026-03-14T10:00:00+00:00",
    "sources_used": ["github", "hackernews", "npm", "pypi", "producthunt"],
    "depth": "deep",
    "version": "0.5.0",
    "keyword_source": "dictionary"
  }
}
```

### Key Fields

| Field | Description |
|-------|-------------|
| `reality_signal` | 0-100. Higher = more existing competition |
| `duplicate_likelihood` | `low` (<30), `medium` (30-60), `high` (>60) |
| `sub_scores` | Per-source breakdown. `npm`/`pypi`/`product_launches` are `null` in quick mode |
| `trend` | `accelerating`, `stable`, or `declining` based on recent activity ratios |
| `top_similars` | Existing projects found, filtered for relevance. Prefixed with `npm:`, `pypi:`, `ph:` for non-GitHub sources |
| `pivot_hints` | 3 actionable suggestions based on competition level |

## Built by Mnemox AI

- GitHub: [mnemox-ai/idea-reality-mcp](https://github.com/mnemox-ai/idea-reality-mcp)
- PyPI: [idea-reality-mcp](https://pypi.org/project/idea-reality-mcp/)
