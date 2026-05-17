"""run + plan: execute and plan test runs."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from runtime.cli._shared import build_artifact, console, print_dag, _kernel
from runtime.tutor.i18n import set_lang
from runtime.tutor.verbosity import set_mode


def register_run(app: typer.Typer) -> None:
    @app.command()
    def run(
        target: str = typer.Argument(..., help="path / url / free-form text"),
        note: str = typer.Option("", "--note", help="extra hint to the router"),
        no_persist: bool = typer.Option(False, "--no-persist", help="skip DB write"),
        json_only: bool = typer.Option(False, "--json", help="print full result JSON only"),
        mode: str = typer.Option("exec", "--mode", help="exec | learn | silent"),
        lang: str = typer.Option("zh", "--lang", help="zh | en | zh-en"),
    ):
        """Plan + execute a test run."""
        set_mode(mode)
        set_lang(lang)
        art = build_artifact(target, note)
        run_id, decision = _kernel.submit(art, persist=not no_persist)
        if not json_only:
            console.print(f"[bold green]run_id[/]: {run_id}")
            console.print(f"target_type: {decision.detected_target_type}  confidence={decision.confidence:.2f}")
            console.print("rationale:", decision.rationale)
            print_dag(decision)
        summary = _kernel.execute_sync(run_id, decision)
        if json_only:
            typer.echo(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            console.print(f"[bold]done[/]: {summary['succeeded']}/{summary['total']} ok, {summary['failed']} failed")

    @app.command()
    def plan(
        target: str = typer.Argument(...),
        note: str = typer.Option("", "--note"),
        out: Path | None = typer.Option(None, "--out", help="write decision JSON to file"),
    ):
        """Plan only (no execution)."""
        art = build_artifact(target, note)
        decision = _kernel.decide(art)
        payload = decision.model_dump()
        if out:
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            console.print(f"decision written -> {out}")
        else:
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
