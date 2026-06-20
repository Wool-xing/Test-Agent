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
    """Show recent run history."""
    console.print(f"[bold cyan]Recent Runs (last {limit})[/]")
    console.print("[yellow]Run history not yet implemented.[/]")


def _show_workspace_results(workspace: Path) -> None:
    """Scan workspace for test output artifacts."""

    dirs_to_check = ["测试报告", "测试用例", "测试结果"]
    found = False
    for dirname in dirs_to_check:
        d = workspace / dirname
        if d.exists():
            if not found:
                found = True
            files = sorted(d.glob("**/*"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]
            if files:
                console.print(f"\n[bold]{dirname}[/]")
                for f in files:
                    if f.is_file():
                        size = f.stat().st_size
                        console.print(f"  · {f.name} ({_fmt_size(size)})")
    if not found:
        console.print("[dim]No output artifacts found.[/]")


def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size}B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f}KB"
    return f"{size / (1024 * 1024):.1f}MB"
