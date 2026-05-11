"""Typer CLI: `tagent run|status|report|catalog|doctor`."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from runtime.api.deps import Kernel
from runtime.api.parsers import parse_path, parse_text, parse_url
from runtime.config.settings import get_settings

app = typer.Typer(add_completion=False, help="Test-Agent Runtime CLI")
console = Console()
_kernel = Kernel()


@app.command()
def run(
    target: str = typer.Argument(..., help="path / url / free-form text"),
    note: str = typer.Option("", "--note", help="extra hint to the router"),
    no_persist: bool = typer.Option(False, "--no-persist", help="skip DB write"),
    json_only: bool = typer.Option(False, "--json", help="print full result JSON only"),
    mode: str = typer.Option("exec", "--mode", help="exec | learn | silent (charter §23)"),
    lang: str = typer.Option("zh", "--lang", help="zh | en | zh-en"),
):
    """Plan + execute a test run."""
    from runtime.tutor.i18n import set_lang
    from runtime.tutor.verbosity import set_mode

    set_mode(mode)
    set_lang(lang)
    art = _build_artifact(target, note)
    run_id, decision = _kernel.submit(art, persist=not no_persist)
    if not json_only:
        console.print(f"[bold green]run_id[/]: {run_id}")
        console.print(f"target_type: {decision.detected_target_type}  confidence={decision.confidence:.2f}")
        console.print("rationale:", decision.rationale)
        _print_dag(decision)
    summary = _kernel.execute_sync(run_id, decision)
    if json_only:
        typer.echo(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        console.print(
            f"[bold]done[/]: {summary['succeeded']}/{summary['total']} ok, {summary['failed']} failed"
        )


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


@app.command()
def plan(
    target: str = typer.Argument(...),
    note: str = typer.Option("", "--note"),
    out: Path | None = typer.Option(None, "--out", help="write decision JSON to file"),
):
    """Plan only (no execution)."""
    art = _build_artifact(target, note)
    decision = _kernel.decide(art)
    payload = decision.model_dump()
    if out:
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"decision written -> {out}")
    else:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@app.command()
def doctor():
    """Sanity check: settings + catalog + optional DB/MinIO ping."""
    s = get_settings()
    console.print("[bold]Settings:[/]")
    console.print(f"  project_root      = {s.project_root}")
    console.print(f"  llm_provider      = {s.llm_provider} (fallback {s.llm_provider_fallback})")
    console.print(f"  db_url            = {s.db_url}")
    console.print(f"  minio_endpoint    = {s.minio_endpoint}")
    console.print(f"  otel_enabled      = {s.otel_enabled}")
    cat = _kernel.catalog()
    console.print(f"\n[bold]Catalog:[/] {cat['counts']['experts']} experts, {cat['counts']['skills']} skills")
    _ping_db()
    _ping_minio()


def _build_artifact(target: str, note: str):
    p = Path(target)
    if target.startswith(("http://", "https://")):
        art = parse_url(target)
    elif p.exists():
        art = parse_path(p)
    else:
        art = parse_text(target)
    if note:
        art.text = (art.text or "") + "\n\n# Note:\n" + note
    return art


def _print_dag(decision):
    from runtime.tutor.explainer import explain_node
    from runtime.tutor.verbosity import Mode, get_mode

    t = Table(title="Routing DAG")
    t.add_column("id")
    t.add_column("kind")
    t.add_column("name")
    t.add_column("depends_on")
    for n in decision.dag:
        t.add_row(n.id, n.kind, n.name, ",".join(n.depends_on) or "-")
    console.print(t)

    # Charter §23 教学层渲染
    if get_mode() is not Mode.SILENT:
        for i, n in enumerate(decision.dag):
            console.print(f"\n[bold]🎯 Step {i+1}/{len(decision.dag)}[/] {n.name}")
            exp = explain_node(
                target=n.name,
                one_liner_zh=getattr(n, "one_liner_zh", "") or "(router 未填 one_liner)",
                one_liner_en=getattr(n, "one_liner_en", ""),
                why=getattr(n, "why", ""),
                theory_refs=list(getattr(n, "theory_refs", []) or []),
                alternatives=list(getattr(n, "alternatives", []) or []),
            )
            rendered = exp.render()
            if rendered:
                console.print(rendered)


def _ping_db():
    try:
        from sqlalchemy import text

        from runtime.storage.db import get_engine

        with get_engine().connect() as c:
            c.execute(text("SELECT 1"))
        console.print("[green]DB    OK[/]")
    except Exception as e:  # noqa: BLE001
        console.print(f"[yellow]DB    skip ({e})[/]")


def _ping_minio():
    try:
        from runtime.storage.objects import ObjectStore

        ObjectStore()._conn()  # noqa: SLF001
        console.print("[green]MinIO OK[/]")
    except Exception as e:  # noqa: BLE001
        console.print(f"[yellow]MinIO skip ({e})[/]")


if __name__ == "__main__":
    app()
