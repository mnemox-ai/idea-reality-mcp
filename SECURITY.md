English | [繁體中文](docs/zh/SECURITY.zh-TW.md)

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
- `api.stackexchange.com` — Stack Overflow API (deep mode)

No user data is stored or transmitted to any other service. The optional `GITHUB_TOKEN`
environment variable is used solely for API authentication and is never logged or persisted.
`PRODUCTHUNT_TOKEN` is ignored — the Product Hunt source is disabled and makes no network
calls, so `api.producthunt.com` is never contacted.
