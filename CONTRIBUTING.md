English | [繁體中文](CONTRIBUTING.zh-TW.md)

# Contributing to idea-reality-mcp

Thanks for your interest in contributing.

## Getting started

```bash
git clone https://github.com/mnemox-ai/idea-reality-mcp.git
cd idea-reality-mcp
uv sync --dev
```

## Running tests

```bash
uv run pytest
```

## Development workflow

1. Fork the repo and create a branch from `main`.
2. Make your changes.
3. Add or update tests as needed.
4. Run `uv run pytest` and ensure all tests pass.
5. Open a pull request with a clear description.

## Code style

- Follow existing patterns in the codebase.
- Use type hints.
- Keep functions focused and small.

## Adding a new data source

1. Create a new file in `src/idea_reality_mcp/sources/`.
2. Implement an async function that returns a dataclass with results.
3. Integrate it into `scoring/engine.py`.
4. Add tests in `tests/`.

## Reporting bugs

Open an issue on GitHub with:
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
