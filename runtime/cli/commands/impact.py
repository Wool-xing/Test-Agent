"""`tagent impact` — KG‑driven blast radius and test selection."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from runtime.cli._shared import console
from runtime.intelligence.impact_engine import ImpactEngine

_app = typer.Typer()

_DEFAULT_GRAPH = "graphify-out/graph.json"


def _resolve_graph(graph: str) -> Path | None:
    """Resolve --graph argument. Default '' means use built‑in default."""
    if graph == _DEFAULT_GRAPH:
        return None  # use ImpactEngine default
    return Path(graph)


def register(app: typer.Typer) -> None:
    app.add_typer(_app, name="impact")


@_app.command()
def analyze(
    file: str = typer.Option(..., "--file", "-f", help="File path to analyze impact for"),
    graph: str = typer.Option(_DEFAULT_GRAPH, "--graph", help="Path to graph.json"),
):
    """Analyze impact of changing a file — shows blast radius and risk."""
    engine = ImpactEngine(graph_path=_resolve_graph(graph))
    result = engine.analyze([file])

    # Risk colour
    if result.risk_score >= 0.7:
        risk_colour = "red"
    elif result.risk_score >= 0.4:
        risk_colour = "yellow"
    else:
        risk_colour = "green"

    console.print(Panel.fit(
        f"[bold]Changed:[/] {result.changed_file}\n"
        f"[bold]Risk Score:[/] [{risk_colour}]{result.risk_score:.3f}[/{risk_colour}]\n"
        f"[bold]Recommendation:[/] {result.test_recommendation}",
        title="Impact Analysis",
        border_style=risk_colour,
    ))

    if result.affected_functions:
        console.print(f"\n[bold]Directly affected ({len(result.affected_functions)}):[/]")
        for fn in result.affected_functions[:10]:
            console.print(f"  - {fn}")
        if len(result.affected_functions) > 10:
            console.print(f"  ... and {len(result.affected_functions) - 10} more")

    if result.blast_radius:
        console.print(f"\n[bold]Blast radius ({len(result.blast_radius)} dependents):[/]")
        for dep in result.blast_radius[:15]:
            console.print(f"  - {dep}")
        if len(result.blast_radius) > 15:
            console.print(f"  ... and {len(result.blast_radius) - 15} more")

    if result.impacted_tests:
        console.print(f"\n[bold]Impacted tests ({len(result.impacted_tests)}):[/]")
        for t in result.impacted_tests[:20]:
            console.print(f"  - {t}")
        if len(result.impacted_tests) > 20:
            console.print(f"  ... and {len(result.impacted_tests) - 20} more")
    elif result.risk_score > 0:
        console.print(f"\n[yellow]No direct test associations found — recommendation is '{result.test_recommendation}'[/]")


@_app.command()
def recommend(
    files: list[str] = typer.Argument(..., help="Changed file paths"),
    graph: str = typer.Option(_DEFAULT_GRAPH, "--graph", help="Path to graph.json"),
):
    """Recommend which tests to run for a set of changed files."""
    engine = ImpactEngine(graph_path=_resolve_graph(graph))
    tests = engine.recommend_tests(files)

    if not tests:
        console.print("[red]High risk — run ALL tests[/]")
        raise typer.Exit(0)

    console.print(f"[green]Run {len(tests)} impacted tests:[/]")
    for t in tests:
        console.print(f"  - {t}")


@_app.command()
def blast_radius(
    function: str = typer.Argument(..., help="Function name to check"),
    graph: str = typer.Option(_DEFAULT_GRAPH, "--graph", help="Path to graph.json"),
):
    """Show what depends on a given function — transitive blast radius."""
    engine = ImpactEngine(graph_path=_resolve_graph(graph))
    broken = engine.what_breaks(function)

    if not broken:
        console.print(f"[dim]No dependents found for '{function}'[/]")
        raise typer.Exit(0)

    table = Table(title=f"Blast Radius: {function}")
    table.add_column("#", style="dim", width=4)
    table.add_column("File", style="cyan")
    table.add_column("Symbol", style="green")

    for i, entry in enumerate(broken[:50], 1):
        if "::" in entry:
            file_part, sym_part = entry.split("::", 1)
        else:
            file_part, sym_part = entry, ""
        table.add_row(str(i), file_part, sym_part)

    console.print(table)
    if len(broken) > 50:
        console.print(f"[dim]... and {len(broken) - 50} more[/]")
    console.print(f"\n[yellow]{len(broken)} total dependents[/]")
