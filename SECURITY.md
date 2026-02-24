# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | :white_check_mark: |

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

No user data is stored or transmitted to any other service. The optional `GITHUB_TOKEN` environment variable is used solely for GitHub API authentication and is never logged or persisted.
