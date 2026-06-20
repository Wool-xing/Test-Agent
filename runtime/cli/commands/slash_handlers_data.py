"""# Data commands: data/prioritize/progress/flaky/regression/insights — extracted from slash_handlers.py."""
from __future__ import annotations
import os, sys, time
from pathlib import Path
from runtime.cli._shared import console
from runtime.cli.slash_commands import _PROVIDERS
from runtime.cli.conversation import ConversationMemory
from runtime.config.settings import get_settings
from runtime.cli.interactive import _get_memory  # cross-sub-file
_SESSION_FILE = get_settings().gateway_dir / "active_session.json"
_SESSION_DIR = _SESSION_FILE.parent
# Module-local mutable state
_command_history_list = []
_last_fix = None
_last_trace = None
_start_time = 0.0


def _cmd_clean(args: str) -> None:
    """Clean temporary data. /clean list | run. Delivery artifacts preserved."""
    from runtime.cli.data_cleaner import get_cleanable, run_cleanup
    from rich.table import Table

    action = args.strip().lower()
    if action == "run":
        result = run_cleanup(dry_run=False)
        console.print(f"[green]Cleaned:[/] {result['cleaned_count']} files, {result['freed_kb']} KB freed")
        console.print("[dim]Reports/cases/plans/scripts/baselines preserved.[/]")
        return

    cleanable = get_cleanable()
    if not cleanable:
        console.print("[dim]Nothing to clean.[/]")
        return

    total_kb = sum(c["size_kb"] for c in cleanable)
    console.print(f"[bold]{len(cleanable)} cleanable files ({total_kb:.0f} KB):[/]")
    table = Table(show_header=True)
    table.add_column("File")
    table.add_column("Size")
    table.add_column("Age")
    for c in cleanable[:15]:
        table.add_row(c["path"][:60], f"{c['size_kb']} KB", f"{c['age_hours']}h ago")
    console.print(table)
    console.print("[dim]Run !clean run to delete. Delivery artifacts never touched.[/]")


# ── /data — test data generation ────────────────────────────────────


def _cmd_data(args: str) -> None:
    """Generate test data: /data users <N> | related <N> | product | order | address."""
    from pathlib import Path

    parts = args.strip().split()
    entity = parts[0].lower() if parts else ""
    count = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 10

    try:
        from utils.data.data_factory_v2 import DataFactoryV2
        factory = DataFactoryV2()

        if entity == "related":
            data = factory.generate_related(count)
            out = Path(f"workspace/测试数据/related_{count}.json")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(factory.to_json(list(data.values())[0] if data else []), encoding="utf-8")
            console.print(f"[green]Generated:[/] {', '.join(f'{k}={len(v)}' for k, v in data.items())} [dim]→ {out}[/]")

        elif entity == "users":
            data = [factory.user() for _ in range(count)]
            out = Path(f"workspace/测试数据/users_{count}.json")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(factory.to_json(data), encoding="utf-8")
            console.print(f"[green]Generated:[/] {count} users [dim]→ {out}[/]")

        elif entity == "products":
            data = [factory.product() for _ in range(count)]
            out = Path(f"workspace/测试数据/products_{count}.json")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(factory.to_json(data), encoding="utf-8")
            console.print(f"[green]Generated:[/] {count} products [dim]→ {out}[/]")

        else:
            console.print("[dim]Usage: !data users|products|related <count>[/]")
            console.print("[dim]Example: /data users 100[/]")
    except ImportError:
        console.print("[red]DataFactoryV2 not available. Install: pip install faker[/]")


# ── /prioritize — test priority by changed code ─────────────────────


def _cmd_prioritize(args: str) -> None:
    """Show which tests to run first based on git changes."""
    from runtime.cli.test_prioritizer import prioritize
    from rich.table import Table

    result = prioritize()
    if result["changed_files"] == 0:
        console.print("[dim]No git changes detected. Run full suite.[/]")
        return

    console.print(f"[bold]{result['changed_files']} changed files → {len(result['changed_modules'])} affected modules[/]")
    if result["priority_detail"]:
        table = Table(title="Test Priority Order", show_header=True)
        table.add_column("Priority", style="cyan")
        table.add_column("Module")
        table.add_column("Changes")
        for i, (module, count) in enumerate(result["priority_detail"], 1):
            marker = "🔴" if count >= 5 else "🟡" if count >= 2 else "🟢"
            table.add_row(f"{marker} #{i}", module, str(count))
        console.print(table)
        console.print("[dim]Tip: Run affected modules first, then full suite if time permits.[/]")
    else:
        console.print("[dim]Changed files not matched to known test modules.[/]")


# ── /progress — test coverage matrix ────────────────────────────────


def _cmd_progress(args: str) -> None:
    """Show test coverage progress matrix: test types × modules."""
    from runtime.cli.coverage_progress import get_matrix, get_summary, DEFAULT_MODULES, TEST_TYPES
    from rich.table import Table

    summary = get_summary()
    console.print(
        f"[bold]Coverage Progress:[/] {summary['coverage_pct']}% "
        f"({summary['covered_slots']}/{summary['total_slots']} slots covered) "
        f"[dim]({summary['recent_runs_24h']} runs in 24h)[/]"
    )

    modules, types, matrix = get_matrix()
    # Show as ASCII heatmap
    widths = {t: max(len(t), 6) for t in types}
    header = " " * 12 + "".join(f"{t:^{widths[t]}}" for t in types)
    console.print(f"[dim]{header}[/]")
    for m in modules[:15]:
        row = f" [cyan]{m:<10}[/] "
        for t in types:
            entry = matrix.get((m, t))
            if entry and entry.run_count > 0:
                rate = entry.pass_count / entry.run_count if entry.run_count else 0
                if rate >= 0.9:
                    cell = f"[green]{'■':^{widths[t]}}[/]"
                elif rate >= 0.5:
                    cell = f"[yellow]{'■':^{widths[t]}}[/]"
                else:
                    cell = f"[red]{'■':^{widths[t]}}[/]"
            else:
                cell = f"[dim]{'·':^{widths[t]}}[/]"
            row += cell
        console.print(row)
    console.print(
        "[dim]■=covered ·=not yet[/]  "
        "[dim]Auto-record via hook: /hook prebuilt[/]"
    )


# ── /flaky — flaky test management ─────────────────────────────────


def _cmd_flaky(args: str) -> None:
    """Show flaky test analysis. /flaky list | quarantine | clear."""
    from runtime.cli.flaky_manager import get_flaky_list, get_quarantined, clear_tracker
    from rich.table import Table

    action = args.strip().lower()
    if action == "clear":
        clear_tracker()
        console.print("[green]Flaky tracker cleared.[/]")
        return
    if action == "quarantine":
        q = get_quarantined()
        if q:
            console.print(f"[yellow]Quarantined ({len(q)}):[/]")
            for n in q:
                console.print(f"  ⊘ {n}")
        else:
            console.print("[dim]No quarantined tests.[/]")
        return

    entries = get_flaky_list()
    if not entries:
        console.print("[dim]No flaky data yet. Run tests multiple times to collect.[/]")
        return

    table = Table(title="Flaky Tests", show_header=True)
    table.add_column("Name")
    table.add_column("Score")
    table.add_column("Runs")
    table.add_column("Pass Rate")
    table.add_column("Status")
    for e in entries[:15]:
        history = e.run_history
        runs = len(history)
        passes = sum(1 for r in history if r["ok"])
        rate = f"{passes}/{runs}" if runs else "-"
        status = "[red]quarantined[/]" if e.quarantined else "[dim]tracking[/]"
        score_color = "red" if e.flaky_score >= 0.5 else "yellow" if e.flaky_score >= 0.2 else "dim"
        table.add_row(e.node_name[:40], f"[{score_color}]{e.flaky_score:.2f}[/]", str(runs), rate, status)
    console.print(table)


# ── /regression — view regression report ────────────────────────────


def _cmd_regression(args: str) -> None:
    """Show regression report: current vs previous run."""
    from runtime.cli.regression_tracker import _latest_baseline, RunResult, compare_with_baseline, is_regression
    from rich.table import Table

    baseline = _latest_baseline()
    if baseline is None:
        console.print("[dim]No regression baseline yet. Run a test first.[/]")
        return

    import json
    try:
        data = json.loads(baseline.read_text(encoding="utf-8"))
    except Exception:
        console.print("[red]Could not read baseline.[/]")
        return

    current = RunResult(**{k: v for k, v in data.items() if k in RunResult.__dataclass_fields__})
    report = compare_with_baseline(current)

    if report.summary == "No previous baseline — first run.":
        console.print(f"[dim]Baseline from: {baseline.stem} (no comparison yet)[/]")
    else:
        color = "red" if is_regression(report) else "green"
        console.print(f"[{color}]Regression: {report.summary}[/]")

    if report.new_failures:
        console.print(f"\n[red]New failures ({len(report.new_failures)}):[/]")
        for f in report.new_failures:
            console.print(f"  ✗ {f}")
    if report.fixed:
        console.print(f"\n[green]Fixed ({len(report.fixed)}):[/]")
        for f in report.fixed:
            console.print(f"  ✓ {f}")
    if report.perf_regressions:
        console.print(f"\n[yellow]Performance regressions ({len(report.perf_regressions)}):[/]")
        for p in report.perf_regressions:
            console.print(f"  ⏱ {p['node']}: {p['prev_ms']}ms → {p['curr_ms']}ms (+{p['increase_pct']}%)")


# ── /insights — cross-session analytics ─────────────────────────────


def _cmd_insights(args: str) -> None:
    """Show usage analytics across saved sessions.

    Scans workspace/gateway/*.json for session data.
    Usage: !insights [days] — default 30 days.
    Shows: session count, avg turns, top agents, daily activity chart.
    """
    from rich.table import Table

    from runtime.cli.insights import collect_stats, compute_insights

    days = 30
    try:
        if args.strip():
            days = int(args.strip())
    except ValueError:
        pass

    with console.status("[bold]Analyzing sessions...", spinner="dots"):
        stats = collect_stats(days=days)
        insights = compute_insights(stats)

    if "error" in insights:
        console.print(f"[dim]{insights['error']}[/]")
        return

    table = Table(title=f"Insights · Last {days} days", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value")
    table.add_row("Sessions", str(insights["sessions"]))
    table.add_row("Total messages", str(insights["total_messages"]))
    table.add_row("Avg turns/session", str(insights["avg_turns_per_session"]))
    table.add_row("Avg duration", f"{insights['avg_duration_s']:.0f}s")
    table.add_row("Data range", f"{insights['oldest_session_days']} days")
    console.print(table)

    if insights["top_agents"]:
        console.print("\n[bold]Top agents:[/]")
        for agent, count in insights["top_agents"]:
            console.print(f"  [cyan]{agent}[/]: {count}")

    if insights["daily_activity"]:
        console.print("\n[bold]Daily activity:[/]")
        max_count = max(c for _, c in insights["daily_activity"])
        for day, count in insights["daily_activity"]:
            bar = "█" * max(1, int(count / max(max_count, 1) * 20))
            console.print(f"  {day}  {bar} {count}")


# ── !doctor — comprehensive environment health check ────────────────


def _cmd_doctor(args: str) -> None:
    """Run comprehensive environment health check.

    7 categories: Environment, Catalog, Config, Dependencies,
    LLM, Workspace, MCP. Use --agents to probe individual experts.
    """
    from rich.table import Table

    from runtime.cli.doctor import run_doctor

    with console.status("[bold green]Running diagnostics...", spinner="dots"):
        results, ok_count, _ = run_doctor()

    table = Table(title="Doctor · Health Check", show_header=True)
    table.add_column("Section")
    table.add_column("Status")

    for section in results:
        for check in section["checks"]:
            icon = "[green]✓[/]" if check["ok"] else "[red]✗[/]"
            label = f"{icon} {check['label']}"
            table.add_row(label, check.get("detail", ""))

    console.print(table)
    console.print(f"\n[bold]{ok_count} checks passed[/]   [dim]Run !help for next steps.[/]")


# ── /nudge — suggest facts worth remembering ───────────────────────


def _cmd_nudge(args: str) -> None:
    """Scan recent conversation for facts worth persisting to MEMORY.md.

    Detects patterns: config changes, preferences, decisions.
    Use !remember <fact> to save suggestions, /memory to review.
    """
    mem = _get_memory()
    if not mem.messages:
        console.print("[dim]No conversation to scan.[/]")
        return
    from runtime.cli.conversation import load_memory_md
    existing = load_memory_md()
    suggestions: list[str] = []
    seen: set[str] = set()
    for m in reversed(mem.messages):
        if m.role != "user":
            continue
        for kw in ["config", "setting", "prefer", "always", "never", "remember"]:
            if kw in m.content.lower() and m.content[:80] not in seen:
                suggestions.append(m.content[:120])
                seen.add(m.content[:80])
                break
    if not suggestions:
        console.print("[dim]No notable facts detected. Use !remember <fact> manually.[/]")
        return
    console.print("[bold]Suggestions from this session:[/]")
    for i, s in enumerate(suggestions[:5], 1):
        preview = s[:100] + ("..." if len(s) > 100 else "")
        console.print(f"  {i}. {preview}")
    if existing:
        console.print(f"\n[dim]MEMORY.md has {len(existing)} chars. /forget <keyword> to clean.[/]")
