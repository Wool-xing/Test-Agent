"""doctor: sanity check settings + catalog + optional DB/MinIO ping + L1/L3 self-check."""

from __future__ import annotations

import typer

from runtime.cli._shared import console, ping_db, ping_minio, _kernel
from runtime.config.settings import get_settings


def register(app: typer.Typer) -> None:
    @app.command()
    def doctor(
        agents: bool = typer.Option(False, "--agents", help="L1 frontmatter lint + optional --probe LLM ping"),
        probe: bool = typer.Option(False, "--probe", help="L3 real LLM ping each agent once (~$0.5)"),
        llm_smoke: bool = typer.Option(False, "--llm-smoke", help="L3 5s round-trip smoke test (single real LLM call)"),
    ):
        """Sanity check: settings + catalog + optional DB/MinIO ping + L1/L3 self-check."""
        s = get_settings()
        console.print("[bold]Settings:[/]")
        console.print(f"  project_root      = {s.project_root}")
        console.print(f"  llm_provider      = {s.llm_provider} (fallback {s.llm_provider_fallback})")
        console.print(f"  db_url            = {s.db_url or '(not set)'}")
        console.print(f"  minio_endpoint    = {s.minio_endpoint}")
        console.print(f"  otel_enabled      = {s.otel_enabled}")
        cat = _kernel.catalog()
        console.print(f"\n[bold]Catalog:[/] {cat['counts']['experts']} experts, {cat['counts']['skills']} skills")
        ping_db()
        ping_minio()

        if agents:
            from runtime.healthcheck.agent_smoke import run_smoke
            console.print("\n[bold]L1 frontmatter lint:[/]")
            report = run_smoke()
            if report.ok:
                console.print(f"[green]OK[/] agents={report.expert_count}/16 skills={report.skill_count}/32")
            else:
                console.print(f"[red]FAIL[/] {len(report.issues)} issue(s):")
                for i in report.issues:
                    console.print(f"  - {i}")
                raise typer.Exit(1)

        if llm_smoke:
            from runtime.healthcheck.llm_smoke import run_llm_smoke
            console.print("\n[bold]L3 LLM smoke (single round-trip 'Hello'):[/]")
            r = run_llm_smoke()
            mark = "[green]✓[/]" if r.ok else "[red]✗[/]"
            console.print(f"  {mark} {r.provider} / {r.model}  {r.latency_ms} ms")
            if r.response:
                console.print(f"    response: {r.response!r}")
            if r.prompt_tokens or r.completion_tokens:
                console.print(f"    tokens:   prompt={r.prompt_tokens} completion={r.completion_tokens}")
            if r.cost_usd > 0:
                console.print(f"    cost:     ${r.cost_usd:.6f}")
            if r.reason:
                console.print(f"    reason:   {r.reason}")
            if not r.ok:
                raise typer.Exit(1)

        if probe:
            from runtime.healthcheck.llm_probe import probe_all_agents
            console.print("\n[bold]L3 LLM probe (real call):[/]")
            results = probe_all_agents()
            for r in results:
                mark = "[green]✓[/]" if r.ok else "[red]✗[/]"
                console.print(f"  {mark} {r.name:30}  {r.latency_ms:>5} ms  {r.reason or ''}")
            failed = [r for r in results if not r.ok]
            if failed:
                console.print(f"[red]{len(failed)}/{len(results)} agents probe failed[/]")
                raise typer.Exit(1)
            console.print(f"[green]all {len(results)} agents responded[/]")
