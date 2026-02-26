English | [繁體中文](SECURITY.zh-TW.md)

# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.2.x   | :white_check_mark: |
| 0.1.x   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in idea-reality-mcp, please report it responsibly:

1. **Do not** open a public GitHub issue.
2. Email **security@mnemox.ai** with:
   - A description of the vulnerability
   - Steps to reproduce
   - Potential impact
3. You will receive a response within 48 hours acknowledging receipt.
4. We will work with you to understand and address the issue before any public disclosure.

## Scope

This project makes outbound HTTP requests to:

- `api.github.com` — GitHub Search API
- `hn.algolia.com` — Hacker News Algolia API
- `registry.npmjs.org` — npm Registry API (deep mode)
- `pypi.org` — PyPI Registry (deep mode)
- `api.producthunt.com` — Product Hunt GraphQL API (deep mode, optional — only when `PRODUCTHUNT_TOKEN` is set)

No user data is stored or transmitted to any other service. The optional `GITHUB_TOKEN` and `PRODUCTHUNT_TOKEN` environment variables are used solely for API authentication and are never logged or persisted.
