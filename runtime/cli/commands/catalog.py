"""catalog: list experts + skills."""

from __future__ import annotations

import typer
from rich.table import Table

from runtime.cli._shared import _kernel, console


def register(app: typer.Typer) -> None:
    @app.command()
    def catalog():
        """List experts + skills loaded from markdown."""
        data = _kernel.catalog()
        t = Table(title=f"Catalog: {data['counts']['experts']} experts + {data['counts']['skills']} skills")
        t.add_column("kind")
        t.add_column("name")
        t.add_column("description")
        for e in data["experts"]:
            t.add_row(e["kind"], e["name"], e["description"][:80])
        for s in data["skills"]:
            t.add_row(s["kind"], s["name"], s["description"][:80])
        console.print(t)
