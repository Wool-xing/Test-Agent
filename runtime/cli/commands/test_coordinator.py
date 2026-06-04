"""CLI entry point: `tagent test <target>`."""

from __future__ import annotations

import typer

from runtime.cli._shared import console


def test_command(target: str = typer.Argument(..., help="Path/URL/free-text target")):
    """Execute the full 11-step test pipeline."""
    from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline

    pipeline = TestCoordinatorPipeline()
    result = pipeline.run(target)

    if not result.ok:
        console.print(f"\n[red]Pipeline aborted at: {result.aborted_at}[/]")
        raise typer.Exit(1)

    console.print("\n[green]Pipeline complete.[/]")


def register(app: typer.Typer) -> None:
    app.command(name="test")(test_command)
