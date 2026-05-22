"""export: TestCaseTree multi-format export (xmind/markmap/opml)."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from runtime.cli._shared import console


def register(app: typer.Typer) -> None:
    @app.command()
    def export(
        plan: str = typer.Argument(..., help="TestCaseTree JSON path"),
        format: str = typer.Option("xmind", "--format", help="xmind | markmap | opml | all"),
        out: str = typer.Option("", "--out", help="output file (single format only)"),
        out_dir: str = typer.Option("workspace/testcases", "--out-dir", help="output dir when --format all"),
    ):
        """Export TestCaseTree to xmind / markmap / opml / all."""
        from runtime.exporters import markmap as _m  # noqa: F401
        from runtime.exporters import opml as _o  # noqa: F401
        from runtime.exporters import xmind as _x  # noqa: F401
        from runtime.exporters.base import REGISTRY, get_exporter

        plan_path = Path(plan)
        if not plan_path.is_file():
            console.print(f"[red]plan not found:[/] {plan}")
            raise typer.Exit(2)
        raw = json.loads(plan_path.read_text(encoding="utf-8"))
        tree = _tree_from_dict(raw)

        formats = sorted(REGISTRY) if format == "all" else [format]
        written: list[Path] = []
        for fmt in formats:
            if fmt not in REGISTRY:
                console.print(f"[red]unknown format:[/] {fmt}; available={sorted(REGISTRY)}")
                raise typer.Exit(2)
            exp = get_exporter(fmt)
            target = Path(out_dir) / f"{tree.project_name}{exp.extension}" if format == "all" or not out else Path(out)
            target.parent.mkdir(parents=True, exist_ok=True)
            final = exp.export(tree, target)
            written.append(final)
            console.print(f"[green]{fmt}[/] → {final}")
        if format == "all":
            console.print(f"[bold]done[/]: {len(written)} files written under {out_dir}")


def _tree_from_dict(d: dict):
    from runtime.exporters.base import TestCaseNode, TestCaseTree

    def _node(n: dict):
        return TestCaseNode(
            title=n.get("title", "(untitled)"), kind=n.get("kind", "feature"),
            priority=n.get("priority"), preconditions=list(n.get("preconditions", [])),
            expected=list(n.get("expected", [])), notes=n.get("notes", ""),
            tags=list(n.get("tags", [])), id=n.get("id", ""),
            children=[_node(c) for c in n.get("children", [])],
        )

    return TestCaseTree(
        project_name=d.get("project_name", "untitled"),
        root=_node(d.get("root", {"title": "root"})),
        version=d.get("version", "1.0"),
        author=d.get("author", "Test-Agent"),
    )
