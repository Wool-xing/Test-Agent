"""report: display last test run results in Rich format."""

from __future__ import annotations

from pathlib import Path

import typer

from runtime.cli._shared import console
from runtime.config.settings import get_settings


def register(app: typer.Typer) -> None:
    @app.command()
    def report(
        run_id: str = typer.Argument(None, help="Specific run ID to display"),
        history: bool = typer.Option(False, "--history", "-H", help="Show recent run history"),
        limit: int = typer.Option(10, "--limit", "-n", help="Number of history entries"),
    ):
        """Display test run results with Rich formatting."""
        settings = get_settings()
        gateway_dir = settings.gateway_dir

        if history:
            _show_history(gateway_dir, limit)
        elif run_id:
            _show_run(gateway_dir, run_id)
        else:
            _show_latest(gateway_dir)


def _show_latest(gateway_dir: Path) -> None:
    """Show the most recent run result."""
    import json

    session_file = gateway_dir / "active_session.json"
    if not session_file.exists():
        console.print("[yellow]No test runs found. Run `tagent run <target>` first.[/]")
        return

    data = json.loads(session_file.read_text(encoding="utf-8"))
    console.print("[bold cyan]Latest Run[/]")
    console.print(f"  Started: {data.get('started_at', 'unknown')}")
    console.print(f"  Provider: {data.get('provider', 'unknown')}")
    console.print(f"  Model: {data.get('model', 'unknown')}")

    # Check workspace for run results
    workspace = gateway_dir.parent / "workspace"
    _show_workspace_results(workspace)


def _show_run(gateway_dir: Path, run_id: str) -> None:
    """Show a specific run by ID."""
    console.print(f"[bold cyan]Run: {run_id}[/]")
    console.print("[yellow]Run detail lookup not yet implemented.[/]")


def _show_history(gateway_dir: Path, limit: int) -> None:
    """Show recent run history by scanning workspace."""
    console.print(f"[bold cyan]Recent Test Runs (last {limit})[/]")
    workspace = gateway_dir.parent / "workspace"
    if not workspace.exists():
        console.print("[dim]No workspace found. Run `tagent run <target>` first.[/]")
        return

    # Scan for result artifacts sorted by modification time
    artifacts = sorted(
        [f for f in workspace.glob("**/*") if f.is_file()],
        key=lambda p: p.stat().st_mtime, reverse=True,
    )[:limit * 3]

    if not artifacts:
        console.print("[dim]No test result artifacts found.[/]")
        return

    # Group by parent directory
    shown_dirs = set()
    count = 0
    for f in artifacts:
        parent = f.parent.name
        if parent not in shown_dirs:
            console.print(f"\n  [bold]{parent}[/]")
            shown_dirs.add(parent)
        if count < limit:
            age = _fmt_age(f.stat().st_mtime)
            console.print(f"    · {f.name}  [dim]({_fmt_size(f.stat().st_size)}, {age})[/]")
            count += 1


def _show_workspace_results(workspace: Path) -> None:
    """Scan workspace for test output artifacts (locale-independent)."""
    if not workspace.exists():
        console.print("[dim]No workspace found. Run `tagent run <target>` first.[/]")
        return

    # Scan ALL subdirectories for output files
    all_dirs = sorted(
        [d for d in workspace.iterdir() if d.is_dir() and not d.name.startswith(".")],
        key=lambda d: d.stat().st_mtime, reverse=True,
    )

    found = False
    for d in all_dirs[:5]:
        files = sorted(d.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)[:8]
        if files:
            found = True
            console.print(f"\n[bold]{d.name}[/]")
            for f in files:
                if f.is_file():
                    console.print(f"  · {f.name} ({_fmt_size(f.stat().st_size)})")
    if not found:
        console.print("[dim]No output artifacts found in workspace.[/]")


def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f}KB"
    return f"{size / (1024 * 1024):.1f}MB"


def _fmt_age(mtime: float) -> str:
    import time
    delta = time.time() - mtime
    if delta < 60:
        return "just now"
    elif delta < 3600:
        return f"{int(delta / 60)}m ago"
    elif delta < 86400:
        return f"{int(delta / 3600)}h ago"
    return f"{int(delta / 86400)}d ago"
