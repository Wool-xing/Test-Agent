"""`tagent readiness` — release readiness scoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.panel import Panel

from runtime.cli._shared import console
from runtime.orchestrator.release_readiness import score_from_run_summary, score_readiness


def register(app: typer.Typer) -> None:

    @app.command()
    def readiness(
        smoke: float = typer.Option(1.0, "--smoke", help="Smoke pass rate (0-1)"),
        regression: float = typer.Option(1.0, "--regression", help="Regression pass rate (0-1)"),
        perf_ok: bool = typer.Option(False, "--perf-ok", help="Performance gate passed"),
        security_ok: bool = typer.Option(False, "--security-ok", help="Security gate passed"),
        p0_bugs: int = typer.Option(0, "--p0-bugs", help="P0 bug count"),
        from_summary: Optional[Path] = typer.Option(None, "--from-summary", help="Run summary JSON path"),
    ) -> None:
        """Weighted release readiness score (smoke×0.4 + regression×0.3 + perf×0.2 + security×0.1)."""
        if from_summary:
            data = json.loads(from_summary.read_text(encoding="utf-8"))
            result = score_from_run_summary(data)
        else:
            result = score_readiness(
                smoke_pass_rate=smoke,
                regression_pass_rate=regression,
                perf_gate_ok=perf_ok,
                security_ok=security_ok,
                p0_bug_count=p0_bugs,
            )

        color_map = {"GREEN": "green", "YELLOW": "yellow", "RED": "red"}
        c = color_map.get(result.verdict, "white")

        console.print(Panel.fit(
            f"[bold {c}]Verdict: {result.verdict}[/bold {c}]\n"
            f"Score: {result.score:.3f}\n"
            f"Breakdown: smoke={result.breakdown['smoke']:.2f} "
            f"regression={result.breakdown['regression']:.2f} "
            f"perf={result.breakdown['performance']:.2f} "
            f"security={result.breakdown['security']:.2f}\n\n"
            f"Reason: {result.reason}\n"
            f"Recommendation: {result.recommendation}",
            title="Release Readiness",
            border_style=c,
        ))

        if result.verdict == "RED":
            raise typer.Exit(code=1)
