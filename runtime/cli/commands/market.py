"""market: search + list + install + uninstall + verify commands."""

from __future__ import annotations

import hashlib
from pathlib import Path

import typer
from rich.table import Table

from runtime.cli._shared import console


def register(app: typer.Typer) -> None:
    @app.command()
    def search(
        keyword: str = typer.Argument(...),
        lane: str = typer.Option(None, "--lane", help="skills | agents | mcp | hooks"),
    ):
        """Search marketplace registry."""
        from runtime.marketplace.catalog import search as catalog_search
        results = catalog_search(keyword, lane=lane)
        if not results:
            console.print("[yellow]no match[/]")
            return
        t = Table(title=f"Marketplace search: {keyword}")
        for col in ("name", "lane", "version", "source_tier", "confidence", "score"):
            t.add_column(col)
        for e in results:
            t.add_row(e.name, e.lane, e.version, e.source_tier, e.confidence, str(e.safety_score))
        console.print(t)

    @app.command(name="list")
    def list_cmd(lane: str = typer.Option(None, "--lane")):
        """List installed marketplace entries."""
        from runtime.marketplace.catalog import load_local
        entries = load_local()
        if lane:
            entries = [e for e in entries if e.lane == lane]
        if not entries:
            console.print("[yellow]nothing installed[/]")
            return
        t = Table(title="Installed marketplace entries")
        for col in ("name", "lane", "version", "tier", "installed_at"):
            t.add_column(col)
        for e in entries:
            t.add_row(e.name, e.lane, e.version, e.source_tier, e.installed_at or "—")
        console.print(t)

    @app.command()
    def install(
        name: str = typer.Argument(...),
        lane: str = typer.Argument(...),
        source: str = typer.Option(..., "--source", help="path to skill .md / agent .md / mcp config / hook"),
        tier: str = typer.Option("low", "--tier"),
        version: str = typer.Option("1.32.4", "--version"),
    ):
        """Install marketplace entry through 4 safety gates."""
        from runtime.marketplace.catalog import Entry
        from runtime.marketplace.installer import install as do_install

        p = Path(source)
        if not p.exists():
            console.print(f"[red]source not found:[/] {source}")
            raise typer.Exit(2)
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        entry = Entry(name=name, version=version, lane=lane, source_url=str(p.resolve()),
                      sha256=sha, license="MIT", source_tier=tier)
        res = do_install(entry, p)
        if res["ok"]:
            console.print(f"[green]installed[/] {name} → {res['path']}")
        else:
            console.print(f"[red]blocked[/] {res.get('blocked_by')}")
            for r in res.get("reasons", []):
                console.print(f"  - {r}")
            raise typer.Exit(1)

    @app.command()
    def uninstall(name: str = typer.Argument(...)):
        """Uninstall (archive only, irreversible)."""
        from runtime.marketplace.installer import uninstall as do_uninstall
        res = do_uninstall(name)
        if res["ok"]:
            console.print(f"[yellow]archived[/] {name} → {res['archived_to']}")
        else:
            console.print(f"[red]failed[/] {res.get('error')}")
            raise typer.Exit(1)

    @app.command()
    def verify(
        source: str = typer.Argument(...),
        skip_sandbox: bool = typer.Option(False, "--skip-sandbox"),
        skip_darwin: bool = typer.Option(False, "--skip-darwin"),
    ):
        """Run 4 safety gates without install."""
        from runtime.marketplace.verifier import run_all_gates
        p = Path(source)
        if not p.exists():
            console.print(f"[red]not found:[/] {source}")
            raise typer.Exit(2)
        results = run_all_gates(p, skip_sandbox=skip_sandbox, skip_darwin=skip_darwin)
        t = Table(title=f"Verify: {p.name}")
        for col in ("gate", "passed", "score", "reason"):
            t.add_column(col)
        for g in results:
            t.add_row(g.gate, "✓" if g.passed else "✗", str(g.score or "—"), g.reason or "—")
        console.print(t)
