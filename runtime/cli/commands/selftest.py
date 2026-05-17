"""selftest: L3 full self-test."""

from __future__ import annotations

from pathlib import Path

import typer

from runtime.api.parsers import parse_path
from runtime.cli._shared import console, _kernel


def register(app: typer.Typer) -> None:
    @app.command()
    def selftest(
        e2e: bool = typer.Option(False, "--e2e", help="L3 full E2E (16 agent DAG, real LLM, ~$3)"),
        fixture: str = typer.Option("examples/_smoke_prd.md", "--fixture", help="PRD fixture path"),
        persist: bool = typer.Option(False, "--persist", help="write to DB"),
        strict: bool = typer.Option(False, "--strict", help="100% node pass rate required; default >=80%"),
        pass_threshold: float = typer.Option(0.80, "--pass-threshold", help="minimum pass rate 0.0-1.0 in non-strict mode"),
    ):
        """L3 full self-test. Default tolerant mode: pass if node pass rate >= threshold (0.80). --strict disables tolerance."""
        if not e2e:
            console.print("[yellow]nothing to do; pass --e2e[/]")
            raise typer.Exit(0)

        fixture_path = Path(fixture)
        if not fixture_path.exists():
            console.print(f"[red]fixture not found:[/] {fixture}")
            raise typer.Exit(2)

        console.print(f"[bold]L3 E2E selftest[/]  fixture={fixture}  mode={'strict' if strict else f'tolerant ≥{pass_threshold:.0%}'}")
        art = parse_path(fixture_path)
        run_id, decision = _kernel.submit(art, persist=persist)
        console.print(f"  run_id      = {run_id}")
        console.print(f"  target_type = {decision.detected_target_type}  confidence={decision.confidence:.2f}")
        console.print(f"  dag nodes   = {len(decision.dag)}")
        summary = _kernel.execute_sync(run_id, decision)

        total = summary["total"]
        succ = summary["succeeded"]
        rollout_skipped = summary.get("rollout_skipped", [])
        n_skipped = len(rollout_skipped)
        if strict:
            ok = summary["failed"] == 0
            rate = succ / total if total else 0.0
            label = "strict (100%)"
        else:
            effective_total = max(1, total - n_skipped)
            rate = succ / effective_total
            ok = rate >= pass_threshold
            label = f"tolerant ≥{pass_threshold:.0%} (排除 {n_skipped} 个 rollout)"

        mark = "[green]✓ PASS[/]" if ok else "[red]✗ FAIL[/]"
        skip_hint = f" / {n_skipped} rollout" if n_skipped else ""
        console.print(f"{mark}  {succ}/{total} ok ({rate:.0%}, {label})  {summary['failed']} failed{skip_hint}")
        if not ok:
            raise typer.Exit(1)
