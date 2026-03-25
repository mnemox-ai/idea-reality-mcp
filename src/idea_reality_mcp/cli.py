"""CLI for idea-reality-mcp (setup, doctor, config)."""

from __future__ import annotations

import click


@click.group()
@click.version_option(package_name="idea-reality-mcp")
def cli() -> None:
    """idea-reality-mcp -- pre-build reality check for AI coding agents."""
    pass


@cli.command()
@click.option("--force", is_flag=True, help="Re-run even if setup was already completed.")
def setup(force: bool) -> None:
    """Interactive setup wizard."""
    from .onboarding.setup_wizard import run_setup

    success = run_setup(force=force)
    raise SystemExit(0 if success else 1)


@cli.command()
@click.option("--full", is_flag=True, help="Run full checks including external connectivity.")
def doctor(full: bool) -> None:
    """Health check for idea-reality-mcp installation."""
    from .onboarding.doctor import run_doctor

    ok = run_doctor(full=full)
    raise SystemExit(0 if ok else 1)


@cli.command()
@click.argument("platform", required=False, default=None)
def config(platform: str | None) -> None:
    """Show MCP config for a platform.

    Without PLATFORM, lists detected platforms.
    With PLATFORM, shows the config snippet.

    Platforms: claude_desktop, claude_code, cursor, windsurf, cline, smithery, docker, raw_json
    """
    from .onboarding.platforms import detect_platforms, get_platform_instruction, PLATFORMS

    if platform is None:
        detected = detect_platforms()
        if detected:
            click.echo("\nDetected platforms:\n")
            for p in detected:
                click.echo(f"  - {p['name']} ({p['id']})")
            click.echo(f"\nRun: idea-reality config <platform_id>\n")
        else:
            click.echo("\nNo platforms detected. Available platform IDs:\n")
            for pid, cfg in PLATFORMS.items():
                click.echo(f"  - {pid} ({cfg['name']})")
            click.echo()
        return

    instruction = get_platform_instruction(platform)
    if instruction is None:
        click.echo(f"\nUnknown platform: {platform}")
        click.echo(f"Available: {', '.join(PLATFORMS.keys())}\n")
        raise SystemExit(1)

    click.echo(f"\n{instruction}\n")
