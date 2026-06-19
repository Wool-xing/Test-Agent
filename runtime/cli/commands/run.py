"""run + plan: execute and plan test runs."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from runtime.cli._shared import _kernel, build_artifact, console, print_dag
from runtime.tutor.i18n import set_lang
from runtime.tutor.verbosity import Mode, set_mode


def register(app: typer.Typer) -> None:
    @app.command()
    def run(
        target: str = typer.Argument(..., help="path / url / free-form text"),
        note: str = typer.Option("", "--note", help="extra hint to the router"),
        no_persist: bool = typer.Option(False, "--no-persist", help="skip DB write"),
        json_only: bool = typer.Option(False, "--json", help="print full result JSON only"),
        mode: Mode | None = typer.Option(  # noqa: B008
            None, "--mode", help="exec | learn | silent (default: $TAGENT_MODE or exec)"
        ),
        lang: str | None = typer.Option(  # noqa: B008
            None, "--lang", help="zh | en | zh-en (default: $TAGENT_LANG or zh)"
        ),
    ):
        """Plan + execute a test run."""
        if mode is not None:
            set_mode(mode)
        if lang is not None:
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
        note: str = typer.Option("", "--note"),  # noqa: B008
        out: Path | None = typer.Option(None, "--out", help="write decision JSON to file"),  # noqa: B008
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
