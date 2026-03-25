"""Interactive setup wizard for idea-reality-mcp."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from .terms import IDEA_REALITY_DISCLAIMER, IDEA_REALITY_ACCEPT_PROMPT


# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------

def _green(text: str) -> str:
    return f"\033[32m{text}\033[0m"


def _yellow(text: str) -> str:
    return f"\033[33m{text}\033[0m"


def _bold(text: str) -> str:
    return f"\033[1m{text}\033[0m"


def _cyan(text: str) -> str:
    return f"\033[36m{text}\033[0m"


# ---------------------------------------------------------------------------
# Marker file
# ---------------------------------------------------------------------------

MARKER_DIR = Path.home() / ".idea-reality"
MARKER_FILE = MARKER_DIR / ".setup_done"


def is_setup_done() -> bool:
    """Check if setup has been completed previously."""
    return MARKER_FILE.exists()


def _write_marker() -> None:
    """Write the setup-done marker file."""
    MARKER_DIR.mkdir(parents=True, exist_ok=True)
    MARKER_FILE.write_text("setup completed\n")


# ---------------------------------------------------------------------------
# Wizard steps
# ---------------------------------------------------------------------------

def _step_disclaimer() -> bool:
    """Show disclaimer and ask for acceptance."""
    print(_bold("\n  Step 1: Terms & Disclaimer\n"))
    print(IDEA_REALITY_DISCLAIMER)
    try:
        answer = input(f"  {IDEA_REALITY_ACCEPT_PROMPT}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n  Setup cancelled.")
        return False
    if answer not in ("y", "yes"):
        print("  You must accept the terms to continue. Setup cancelled.")
        return False
    print(f"  {_green('[OK]')} Terms accepted.\n")
    return True


def _step_detect_platforms() -> None:
    """Detect and show available platforms."""
    print(_bold("  Step 2: Platform Detection\n"))
    # Lazy import to avoid circular deps
    from .platforms import detect_platforms, get_platform_instruction

    detected = detect_platforms()
    if not detected:
        print(f"  {_yellow('[WARN]')} No MCP platforms detected.\n")
        print("  Raw JSON config:")
        raw = get_platform_instruction("raw_json")
        if raw:
            print(f"  {raw}\n")
        return

    for p in detected:
        print(f"  {_green('[FOUND]')} {p['name']}")

    print()
    # Show config for the first detected platform
    first = detected[0]
    print(f"  Config for {_bold(first['name'])}:\n")
    print(f"  {first['instruction']}\n")

    if len(detected) > 1:
        print(f"  (Also detected: {', '.join(p['name'] for p in detected[1:])})")
        print(f"  Run {_cyan('idea-reality config <platform>')} for other configs.\n")


def _step_github_token() -> None:
    """Optionally configure GITHUB_TOKEN."""
    print(_bold("  Step 3: GitHub Token (optional)\n"))
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        print(f"  {_green('[OK]')} GITHUB_TOKEN already set.\n")
        return

    print("  Without GITHUB_TOKEN: 10 GitHub API requests/hour (unauthenticated).")
    print("  With GITHUB_TOKEN: 5,000 requests/hour.")
    print("  Create one at: https://github.com/settings/tokens\n")
    print("  To set it, add to your shell profile:")
    print("    export GITHUB_TOKEN=ghp_xxxxxxxxxxxx\n")


def _step_health_check() -> bool:
    """Run core health check."""
    print(_bold("  Step 4: Health Check\n"))
    from .doctor import run_doctor
    return run_doctor(full=False)


def _step_done() -> None:
    """Show completion message."""
    _write_marker()
    print(_bold("  Setup complete!\n"))
    print('  Tell your agent: "Check if there\'s already a tool for converting Figma to React"\n')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_setup(force: bool = False) -> bool:
    """Run the interactive setup wizard.

    Args:
        force: Re-run even if setup was already done.

    Returns:
        True if setup completed successfully.
    """
    if is_setup_done() and not force:
        print(f"\n  Setup already completed. Use {_cyan('--force')} to re-run.\n")
        return True

    print(_bold("\n  idea-reality-mcp Setup Wizard\n"))
    print("  " + "=" * 40)

    # Step 1: Disclaimer
    if not _step_disclaimer():
        return False

    # Step 2: Detect platforms
    _step_detect_platforms()

    # Step 3: GitHub token
    _step_github_token()

    # Step 4: Health check
    _step_health_check()

    # Done
    _step_done()
    return True
