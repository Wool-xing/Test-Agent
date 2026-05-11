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
    version: str = typer.Option("1.0.0", "--version"),
):
    """Install marketplace entry through 4 safety gates."""
    import hashlib

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
    """Uninstall (archive only, §22 不可逆禁止)."""
    from runtime.marketplace.installer import uninstall as do_uninstall

    res = do_uninstall(name)
    if res["ok"]:
        console.print(f"[yellow]archived[/] {name} → {res['archived_to']}")
    else:
        console.print(f"[red]failed[/] {res.get('error')}")
        raise typer.Exit(1)


@app.command()
def export(
    plan: str = typer.Argument(..., help="TestCaseTree JSON path (testcase-designer output)"),
    format: str = typer.Option("xmind", "--format", help="xmind | markmap | opml | all"),
    out: str = typer.Option("", "--out", help="output file (single format only)"),
    out_dir: str = typer.Option("workspace/测试用例", "--out-dir", help="dir when --format all"),
):
    """Export TestCaseTree to xmind / markmap / opml / all (charter §5 多格式 I/O)."""
    from runtime.exporters import xmind as _x  # noqa: F401 ensure registration
    from runtime.exporters import markmap as _m  # noqa: F401
    from runtime.exporters import opml as _o  # noqa: F401
    from runtime.exporters.base import REGISTRY, TestCaseNode, TestCaseTree, get_exporter

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
        if format == "all" or not out:
            target = Path(out_dir) / f"{tree.project_name}{exp.extension}"
        else:
            target = Path(out)
        target.parent.mkdir(parents=True, exist_ok=True)
        final = exp.export(tree, target)
        written.append(final)
        console.print(f"[green]{fmt}[/] → {final}")
    if format == "all":
        console.print(f"[bold]done[/]: {len(written)} files written under {out_dir}")


def _tree_from_dict(d: dict) -> "TestCaseTree":
    from runtime.exporters.base import TestCaseNode, TestCaseTree

    def _node(n: dict) -> TestCaseNode:
        return TestCaseNode(
            title=n.get("title", "(untitled)"),
            kind=n.get("kind", "feature"),
            priority=n.get("priority"),
            preconditions=list(n.get("preconditions", [])),
            expected=list(n.get("expected", [])),
            notes=n.get("notes", ""),
            tags=list(n.get("tags", [])),
            id=n.get("id", ""),
            children=[_node(c) for c in n.get("children", [])],
        )

    return TestCaseTree(
        project_name=d.get("project_name", "untitled"),
        root=_node(d.get("root", {"title": "root"})),
        version=d.get("version", "1.0"),
        author=d.get("author", "Test-Agent"),
    )


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


if __name__ == "__main__":
    app()
