"""demo: one-command full demo."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import typer

from runtime.api.parsers import parse_path
from runtime.cli._shared import _SMOKE_PRD_FIXTURE, console


def register(app: typer.Typer) -> None:
    @app.command()
    def demo(
        out: str = typer.Option("workspace/_demo", "--out", help="demo output dir"),
        preset: str = typer.Option("minimal", "--preset", help="init preset · minimal=offline 0-config"),
        keep: bool = typer.Option(False, "--keep", help="keep previous output"),
        real_llm: bool = typer.Option(False, "--real-llm", help="real LLM path (~$1-3) · default stub"),
        skip_smoke: bool = typer.Option(False, "--skip-smoke", help="skip pre-flight smoke test"),
        yes: bool = typer.Option(False, "-y", "--yes", help="skip cost confirmation prompt"),
    ):
        """One-command full demo · default 0-config stub · --real-llm for real LLM."""
        if sys.platform == "win32":
            os.environ.setdefault("PYTHONIOENCODING", "utf-8")
            os.environ.setdefault("PYTHONUTF8", "1")

        if real_llm:
            provider = os.getenv("TAGENT_LLM_PROVIDER", "(unset)")
            console.print(f"[bold yellow]⚠ --real-llm mode[/]  provider={provider}")
            console.print("  · Real LLM calls ~$1-3 / 60-120s (16 agents × multi-turn)")
            if not yes and not typer.confirm("  Continue? (N=exit)", default=False):
                raise typer.Exit(0)
            if not skip_smoke:
                from runtime.healthcheck.llm_smoke import run_llm_smoke
                console.print("\n[bold]Pre-flight · doctor --llm-smoke (single round-trip)[/]")
                r = run_llm_smoke()
                mark = "[green]✓[/]" if r.ok else "[red]✗[/]"
                console.print(f"  {mark} {r.provider} / {r.model}  {r.latency_ms} ms  {r.reason or ''}")
                if not r.ok:
                    console.print("  [red]LLM unreachable -> exiting.[/] Fix config or add --skip-smoke")
                    raise typer.Exit(1)
                if r.response:
                    console.print(f"    response: {r.response!r}")
        else:
            os.environ["TAGENT_LLM_PROVIDER"] = "stub"
            os.environ["TAGENT_LLM_PROVIDER_FALLBACK"] = "stub"

        import runtime.config.settings as _settings_mod
        _settings_mod._settings = None
        from runtime.api.deps import Kernel as _Kernel
        demo_kernel = _Kernel()

        from runtime.init.matrix import load_matrix
        from runtime.init.renderer import render_all
        from runtime.init.wizard import from_preset

        mode_label = "real LLM" if real_llm else "stub LLM"
        console.print(f"\n[bold cyan]Test-Agent · One-Command Demo[/]  ({mode_label})\n")

        out_path = Path(out)
        if out_path.exists() and not keep:
            console.print(f"[dim]Clearing previous output {out_path}[/]")
            shutil.rmtree(out_path, ignore_errors=True)
        out_path.mkdir(parents=True, exist_ok=True)

        console.print(f"[bold]Step 1/4 · tagent init --preset {preset}[/]")
        matrix = load_matrix()
        answers = from_preset(preset, matrix=matrix)
        res = render_all(answers, out_path, matrix=matrix, overwrite=True)
        console.print(f"  ✓ {res.env_path.name}  /  {res.yml_path.name}  /  {res.startup_path.name}")

        console.print("\n[bold]Step 2/4 · tagent doctor --agents (L1 frontmatter lint)[/]")
        from runtime.healthcheck.agent_smoke import run_smoke
        report = run_smoke()
        if report.ok:
            console.print(f"  ✓ agents={report.expert_count}/16  skills={report.skill_count}/32")
        else:
            console.print(f"  [red]✗ {len(report.issues)} issue(s)[/]")
            raise typer.Exit(1)

        step3_label = "real LLM · ~$1-3" if real_llm else "stub LLM · 0 cost"
        console.print(f"\n[bold]Step 3/4 · tagent selftest --e2e (16 agent DAG · {step3_label})[/]")
        fixture_path = Path("examples/_smoke_prd.md")
        if not fixture_path.exists():
            fixture_path.parent.mkdir(parents=True, exist_ok=True)
            fixture_path.write_text(_SMOKE_PRD_FIXTURE, encoding="utf-8")
            console.print(f"  [yellow]⚡ auto-generated fixture:[/] {fixture_path}")
        art = parse_path(fixture_path)
        run_id, decision = demo_kernel.submit(art, persist=False)
        summary = demo_kernel.execute_sync(run_id, decision)
        total = summary["total"]
        succ = summary["succeeded"]
        rate = succ / total if total else 0.0
        console.print(f"  ✓ DAG executed: {succ}/{total} ok ({rate:.0%})")

        console.print("\n[bold]Step 4/4 · Artifacts[/]")
        artifacts = []
        for d in (Path("workspace/测试用例"), Path("workspace/测试报告"), Path("workspace/执行日志")):
            if d.exists():
                for f in sorted(d.glob("**/*")):
                    if f.is_file() and not f.name.startswith("_"):
                        artifacts.append(f)
        if artifacts:
            for f in artifacts[:12]:
                console.print(f"  · {f}")
            if len(artifacts) > 12:
                console.print(f"  · [dim]... +{len(artifacts) - 12} more[/]")
        else:
            console.print("  [yellow](no artifacts · may need `pip install -r requirements.txt`)[/]")

        console.print(f"\n[bold green]✓ demo done[/]  config: {out_path}  artifacts: workspace/")
        console.print(f"[dim]Next: `cat {res.startup_path}` for startup guide; edit `.env` to use real LLM[/]")
