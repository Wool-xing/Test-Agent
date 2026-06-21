"""tagent migrate — V1.x → V2.0.0 migration helper (§补-1)."""

from __future__ import annotations

from pathlib import Path

import typer

from runtime.infra.migration import MigrationManager

app = typer.Typer(name="migrate", help="Migrate from V1.x to V2.0.0")


@app.command("v2")
def migrate_v2(
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview changes without applying"),
    project_root: str = typer.Option(".", "--root", help="Project root directory"),
) -> None:
    """Migrate V1.x configuration and data to V2.0.0 format."""
    root = Path(project_root).resolve()
    mgr = MigrationManager(root)

    if not mgr.check_needed():
        print("No V1.x configuration found — migration not needed.")
        return

    if dry_run:
        report = mgr.dry_run()
        print("Dry-run — the following steps would be executed:")
        for step in report.steps:
            print(f"  {'[reversible]' if step.reversible else '[irreversible]'} {step.name}: {step.description}")
    else:
        report = mgr.migrate()
        ok = sum(1 for s in report.steps if s.applied)
        total = len(report.steps)
        print(f"Migration complete: {ok}/{total} steps applied.")
        if report.errors:
            for err in report.errors:
                print(f"  ERROR: {err}")
        if report.warnings:
            for warn in report.warnings:
                print(f"  WARNING: {warn}")
