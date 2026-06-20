"""# Operations: MCP + cron/task/model/search + API/plugins/alias/ws/gateway/cross/clean — extracted from slash_handlers.py."""
from __future__ import annotations
import os, re, sys, time
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


def _cmd_mcp_tools(args: str) -> None:
    """List MCP tools across all configured servers."""
    import asyncio

    from rich.table import Table

    from runtime.mcp.client import get_client

    client = get_client()

    async def _list() -> list:
        return await client.list_all_tools()

    try:
        tools = asyncio.run(_list())
    except Exception as exc:
        console.print(f"[red]Failed to discover MCP tools: {exc}[/]")
        return

    if not tools:
        console.print("[dim]No MCP tools discovered. Check config/.mcp.json[/]")
        return

    table = Table(title=f"MCP Tools · {len(tools)} across {len(client.servers)} servers", show_header=True)
    table.add_column("Server", style="dim")
    table.add_column("Tool", style="cyan")
    table.add_column("Description")

    for t in sorted(tools, key=lambda x: (x.server_name, x.tool_name)):
        table.add_row(t.server_name, t.tool_name, t.description[:80])

    console.print(table)
    console.print("[dim]Call a tool: /mcp-call <server> <tool> [json_args][/]")


def _cmd_mcp_call(args: str) -> None:
    """Call an MCP tool: /mcp-call <server> <tool> [json_args]"""
    import asyncio
    import json as _json

    from runtime.mcp.client import get_client

    parts = args.strip().split(maxsplit=2)
    if len(parts) < 2:
        console.print("[red]Usage: !mcp-call <server> <tool> [json_args][/]")
        console.print("[dim]Example: /mcp-call test-orchestrator catalog[/]")
        return

    server_name, tool_name = parts[0], parts[1]
    tool_args = {}
    if len(parts) > 2:
        try:
            tool_args = _json.loads(parts[2])
        except _json.JSONDecodeError:
            console.print(f"[red]Invalid JSON args: {parts[2]}[/]")
            return

    client = get_client()

    async def _call():
        return await client.call_tool(server_name, tool_name, tool_args)

    with console.status(f"[bold green]Calling {server_name}/{tool_name}..."):
        try:
            result = asyncio.run(_call())
        except Exception as exc:
            console.print(f"[red]MCP call failed: {exc}[/]")
            return

    if result.ok:
        preview = result.content[:500] + ("..." if len(result.content) > 500 else "")
        console.print(f"[green]✓ {server_name}/{tool_name}[/] ({len(result.content)} chars)")
        console.print(preview)
    else:
        console.print(f"[red]✗ {server_name}/{tool_name}: {result.error}[/]")


# ── /cron — scheduled task management ─────────────────────────────


def _cmd_cron(args: str) -> None:
    """Manage scheduled tasks: /cron list | add | remove | run.

    /cron list                     — show all scheduled jobs
    /cron add <cron> <prompt>      — schedule a test (e.g. "0 9 * * *" smoke test)
    /cron remove <job_id>          — delete a scheduled job
    /cron run                      — run all due jobs now
    """
    parts = args.strip().split(maxsplit=1)
    sub = parts[0].lower() if parts else "list"
    rest = parts[1] if len(parts) > 1 else ""

    if sub == "list":
        from rich.table import Table

        from runtime.scheduler.jobs import list_jobs

        jobs = list_jobs()
        if not jobs:
            console.print("[dim]No scheduled jobs. Use !cron add <cron> <prompt>[/]")
            console.print("[dim]Example: /cron add '0 9 * * *' smoke test daily[/]")
            return

        table = Table(title=f"Scheduled Jobs · {len(jobs)}", show_header=True)
        table.add_column("ID", style="dim", width=16)
        table.add_column("Cron", style="cyan")
        table.add_column("Prompt")
        table.add_column("Next At", style="dim")
        table.add_column("Status")

        for j in jobs:
            status = "[green]enabled[/]" if j.get("enabled") else "[dim]disabled[/]"
            cnt = j.get("run_count", 0)
            if cnt:
                status += f" ({cnt} runs)"
            table.add_row(
                j["id"][:16],
                j.get("cron", ""),
                j.get("prompt", "")[:50],
                (j.get("next_at") or "")[:19],
                status,
            )
        console.print(table)

    elif sub == "add":
        # Parse: /cron add "0 9 * * *" "smoke test"  OR  /cron add "every morning" "smoke test"
        import shlex

        try:
            tokens = shlex.split(rest)
        except ValueError:
            tokens = rest.split(maxsplit=1)

        if len(tokens) < 2:
            console.print("[red]Usage: !cron add <schedule> <prompt>[/]")
            console.print("[dim]Cron: /cron add '0 9 * * *' run full regression[/]")
            console.print("[dim]Natural: /cron add 'every morning' run smoke tests[/]")
            console.print("[dim]Try: every morning / every day at 18 / every monday / hourly[/]")
            return

        cron_expr = tokens[0]
        prompt = tokens[1] if len(tokens) > 1 else ""

        # Auto-detect natural language → convert to cron expression
        if not re.match(r"^[\d*/,\-]+\s+[\d*/,\-]+\s+[\d*/,\-]+\s+[\d*/,\-]+\s+[\d*/,\-]+$", cron_expr):
            from runtime.scheduler.nl_cron import parse as nl_parse
            parsed = nl_parse(cron_expr)
            if parsed:
                console.print(f"[dim]Parsed '{cron_expr}' → [cyan]{parsed}[/][/]")
                cron_expr = parsed
            else:
                console.print(f"[red]Cannot parse schedule: '{cron_expr}'[/]")
                console.print("[dim]Use cron format (5 fields) or natural language (e.g. 'every morning')[/]")
                return

        try:
            from runtime.scheduler.jobs import add_job

            job_id = add_job(cron_expr, prompt, delivery=["telegram"])
            console.print(f"[green]✓ Scheduled[/] {job_id}")
            console.print(f"[dim]  Cron: {cron_expr}[/]")
            console.print(f"[dim]  Prompt: {prompt}[/]")
        except Exception as e:
            console.print(f"[red]Failed: {e}[/]")
            console.print("[dim]Ensure croniter is installed: pip install croniter[/]")

    elif sub == "remove":
        job_id = rest.strip()
        if not job_id:
            console.print("[red]Usage: !cron remove <job_id>[/]")
            return
        from runtime.scheduler.jobs import remove_job

        if remove_job(job_id):
            console.print(f"[green]✓ Removed {job_id}[/]")
        else:
            console.print(f"[red]Job not found: {job_id}[/]")

    elif sub == "run":
        from runtime.scheduler.scheduler import tick

        n = tick()
        console.print(f"[green]✓ Tick complete — {n} job(s) processed[/]")


def _cmd_cron_health(args: str) -> None:
    """Add built-in hourly health check job."""
    from runtime.scheduler.jobs import add_job, list_jobs

    # Check if health check already exists
    existing = [j for j in list_jobs() if j.get("metadata", {}).get("kind") == "health-check"]
    if existing:
        console.print(f"[dim]Health check already scheduled: {existing[0]['id'][:16]}[/]")
        return

    job_id = add_job(
        "0 * * * *",  # every hour
        "Run framework self-check: verify all 16 experts + 32 skills load correctly",
        delivery=["telegram"],
        metadata={"kind": "health-check", "description": "Hourly self-check"},
    )
    console.print(f"[green]✓ Health check scheduled hourly[/] {job_id}")


# ── !model-router — display auto-routing configuration ─────────────


def _cmd_model_router(args: str) -> None:
    """Show model auto-routing tiers (P2 #14)."""
    from rich.table import Table

    from runtime.router.model_router import (
        get_current_provider,
        get_model_tier,
    )

    current = get_current_provider()
    table = Table(title="Model Auto-Router · P2 #14", show_header=True)
    table.add_column("Provider", style="cyan")
    table.add_column("Light (routing)", style="dim")
    table.add_column("Heavy (execution)", style="bold")

    # Provider list for display — any provider works, these show defaults
    display_providers = [
        "claude", "openai", "gemini", "deepseek", "qwen", "zhipu", "ollama",
    ]
    for prov in display_providers:
        tier = get_model_tier(prov)
        marker = " ←" if prov == current else ""
        table.add_row(
            prov + marker,
            tier.light_model,
            tier.heavy_model,
        )

    # Show relay/proxy config
    api_base = os.environ.get("TAGENT_LLM_API_BASE")
    if api_base:
        console.print(f"[dim]Relay endpoint: {api_base}[/]")

    console.print(table)
    console.print("[dim]Auto: classify_task(prompt) → LIGHT/HEAVY → model selection[/]")
    console.print("[dim]Override via !model <provider> [model] or TAGENT_LLM_MODEL env[/]")


# ── /search — full-text conversation search (P3 #16) ───────────────


def _cmd_search(args: str) -> None:
    """Search conversation history with FTS5."""
    query = args.strip()
    if not query:
        console.print("[red]Usage: !search <query>[/]")
        console.print("[dim]Example: /search login page bug[/]")
        return

    from rich.table import Table

    from runtime.cli.search import search

    results = search(query, limit=15)
    if not results:
        console.print(f"[dim]No results for '{query}'[/]")
        return

    table = Table(title=f"Search: '{query}' · {len(results)} results", show_header=True)
    table.add_column("Session", style="dim", width=14)
    table.add_column("Role", width=8)
    table.add_column("Content")
    table.add_column("Date", style="dim", width=19)

    for r in results:
        role = "[cyan]You[/]" if r["role"] == "user" else "[green]Agent[/]"
        preview = r["content"][:100] + ("..." if len(r["content"]) > 100 else "")
        ts = r.get("ts", "")[:19]
        table.add_row(r["session_id"][:12], role, preview, ts)

    console.print(table)


# ── /skill-score — auto-rate skills (P3 #18) ──────────────────────


def _cmd_skill_score(args: str) -> None:
    """Score skills based on execution history."""
    from rich.table import Table

    from runtime.learning_loop.skill_scorer import collect_execution_stats, compute_scores

    with console.status("[bold green]Scanning execution history..."):
        records = collect_execution_stats()
        if not records:
            console.print("[dim]No execution history found. Run some tests first.[/]")
            return
        scores = compute_scores(records)

    table = Table(title=f"Skill Scores · {len(scores)} skills · {len(records)} records", show_header=True)
    table.add_column("Skill", style="cyan")
    table.add_column("Runs", width=6)
    table.add_column("OK%", width=6)
    table.add_column("Avg Dur", width=8)
    table.add_column("Score", width=6)

    for s in sorted(scores.values(), key=lambda x: x.score, reverse=True)[:20]:
        ok_str = f"{s.success_rate:.0%}"
        dur_str = f"{s.avg_duration_ms}ms" if s.avg_duration_ms else "-"
        score_style = "[green]" if s.score >= 70 else "[yellow]" if s.score >= 40 else "[red]"
        table.add_row(
            s.name, str(s.runs),
            ok_str, dur_str,
            f"{score_style}{s.score:.0f}[/]",
        )

    console.print(table)
    console.print("[dim]Score = success_rate×50 + frequency×30 + speed×20 (max 100)[/]")


# ── /speak — voice announce (P3 #23) ──────────────────────────────


def _cmd_speak(args: str) -> None:
    """Read last result or given text aloud."""
    text = args.strip()
    if not text:
        mem = _get_memory()
        assistant_msgs = [m.content for m in mem.messages if m.role == "assistant"]
        text = assistant_msgs[-1][:300] if assistant_msgs else "No results to speak."
    try:
        from runtime.cli.voice import speak
        ok = speak(text)
        console.print(f"[dim]{'Spoke' if ok else 'TTS unavailable'}: {text[:80]}[/]")
    except Exception as e:
        console.print(f"[red]Voice error: {e}[/]")


# ── /distill — create reusable skill from last execution ────────────


def _cmd_distill(args: str) -> None:
    """Distill the last execution into a reusable skill document.

    Requires a complex execution (3+ nodes, 2+ agent types).
    Usage: !distill [name] — name is auto-generated if omitted.
    The generated skill is saved to skills/<name>.md.
    """
    global _last_trace
    if _last_trace is None:
        console.print("[dim]No execution to distill. Run a test first.[/]")
        return

    user_text, decision_dict = _last_trace
    from runtime.learning_loop.skill_distiller import capture_trace, distill_skill, suggest_skill_name

    trace = capture_trace(user_text, decision_dict)
    if not trace.is_distillable:
        console.print("[dim]Last execution too simple to distill (need ≥3 nodes, ≥2 agent types).[/]")
        return

    name = args.strip() or suggest_skill_name(trace)
    try:
        path = distill_skill(trace, name)
        console.print(f"[green]Skill created:[/] {path}")
    finally:
        _last_trace = None  # consume once, even on error


# ── /api — API contract testing ────────────────────────────────────


def _cmd_api(args: str) -> None:
    """API testing: /api gen <spec> <base_url> | test <base_url> [spec]."""
    from rich.table import Table
    parts = args.strip().split(maxsplit=1)
    action = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""

    if action == "gen":
        sub = rest.split(maxsplit=1)
        if len(sub) < 2:
            console.print("[dim]Usage: !api gen <spec_path_or_url> <base_url>[/]")
            return
        try:
            from utils.design.openapi_test_gen import load_openapi_spec, generate_test_cases
            spec = load_openapi_spec(sub[0])
            path = generate_test_cases(spec, sub[1])
            endpoints = len(spec.get("paths", {}))
            console.print(f"[green]Generated:[/] ~{endpoints * 5} test cases [dim]→ {path}[/]")
        except Exception as e:
            console.print(f"[red]{e}[/]")

    elif action == "test":
        sub = rest.split(maxsplit=1)
        if not sub:
            console.print("[dim]Usage: !api test <base_url> [spec_path][/]")
            return
        console.print(f"[bold]API Smoke:[/] {sub[0]}")
        try:
            from utils.design.openapi_test_gen import load_openapi_spec, smoke_test_all_endpoints
            spec = load_openapi_spec(sub[1]) if len(sub) > 1 else {"paths": {}}
            if not spec.get("paths"):
                console.print("[dim]No OpenAPI spec — use !api gen first[/]")
                return
            result = smoke_test_all_endpoints(spec, sub[0])
            table = Table(title="API Smoke Results")
            table.add_column("Endpoint")
            table.add_column("Status")
            for d in result["details"][:15]:
                icon = "[green]✓[/]" if d.get("ok") else "[red]✗[/]"
                table.add_row(f"{d.get('method','GET')} {d.get('path','?')}", icon)
            console.print(table)
            console.print(f"[bold]{result['passed']}/{result['total']} ok[/]")
        except Exception as e:
            console.print(f"[red]{e}[/]")
    else:
        console.print("[dim]Usage: !api gen <spec> <base_url> | test <base_url> [spec][/]")


# ── /plugins — list loaded plugins (P3 #22) ────────────────────────


def _cmd_plugins_list(args: str) -> None:
    """List loaded plugins from workspace/plugins/."""
    from runtime.plugins import discover_plugins

    plugins = discover_plugins()
    if not plugins:
        console.print("[dim]No plugins found. Drop .py files in workspace/plugins/[/]")
        return

    from rich.table import Table
    table = Table(title=f"Plugins · {len(plugins)} loaded", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Registered")
    for name, mod in plugins.items():
        try:
            info = mod.register()
            desc = info.get("description", "-")[:60]
        except Exception:
            desc = "[red]error loading[/]"
        table.add_row(name, desc)
    console.print(table)


# ── !alias — command shortcuts ─────────────────────────────────────


def _cmd_alias(args: str) -> None:
    """Manage command aliases: /alias list | add <name> <cmd> | remove <name>."""
    from runtime.cli.aliases import list_aliases, add_alias, remove_alias
    from rich.table import Table

    parts = args.strip().split(maxsplit=1)
    action = parts[0].lower() if parts else "list"
    rest = parts[1] if len(parts) > 1 else ""

    if action == "list" or not action:
        aliases = list_aliases()
        if not aliases:
            console.print("[dim]No aliases. !alias add smoke '/test --quick'[/]")
            return
        table = Table(title=f"Aliases · {len(aliases)}", show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Command")
        for a in aliases:
            table.add_row(a.name, a.command[:80])
        console.print(table)

    elif action == "add":
        sub = rest.strip().split(maxsplit=1)
        name = sub[0] if sub else ""
        cmd = sub[1] if len(sub) > 1 else ""
        if not name or not cmd:
            console.print("[dim]Usage: !alias add <name> <command>[/]")
            console.print("[dim]Example: !alias add smoke '/test --quick'[/]")
            return
        a = add_alias(name, cmd)
        console.print(f"[green]Alias:[/] [cyan]{a.name}[/] → {a.command}")

    elif action == "remove":
        name = rest.strip()
        if not name:
            console.print("[dim]Usage: !alias remove <name>[/]")
            return
        if remove_alias(name):
            console.print(f"[green]Removed: {name}[/]")
        else:
            console.print(f"[red]Not found: {name}[/]")


# ── /ws — workspace management ─────────────────────────────────────


def _cmd_ws(args: str) -> None:
    """Manage workspaces: /ws list | add <name> [path] | switch <name> | auto."""
    from runtime.cli.workspaces import (
        list_workspaces, add_workspace, remove_workspace, switch_to, auto_discover, get_current,
    )
    from rich.table import Table

    parts = args.strip().split(maxsplit=1)
    action = parts[0].lower() if parts else "list"
    rest = parts[1] if len(parts) > 1 else ""

    if action == "list" or not action:
        current = get_current()
        workspaces = list_workspaces()
        if not workspaces:
            console.print("[dim]No workspaces. Use !ws add <name> [path] or /ws auto[/]")
            return
        table = Table(title=f"Workspaces · {len(workspaces)}", show_header=True)
        table.add_column("Name", style="cyan")
        table.add_column("Path")
        table.add_column("Project")
        for w in workspaces:
            marker = " [green]←[/]" if current and w.name == current.name else ""
            table.add_row(w.name + marker, w.path[:50], w.project_name)
        console.print(table)

    elif action == "add":
        sub = rest.strip().split(maxsplit=1)
        name = sub[0] if sub else ""
        path = sub[1] if len(sub) > 1 else str(get_settings().project_root)
        if not name:
            console.print("[dim]Usage: !ws add <name> [path][/]")
            return
        w = add_workspace(name, path)
        console.print(f"[green]Workspace:[/] {w.name} → {w.path}")

    elif action == "remove":
        name = rest.strip()
        if not name:
            console.print("[dim]Usage: !ws remove <name>[/]")
            return
        if remove_workspace(name):
            console.print(f"[green]Removed: {name}[/]")
        else:
            console.print(f"[red]Not found: {name}[/]")

    elif action == "switch":
        name = rest.strip()
        if not name:
            console.print("[dim]Usage: !ws switch <name>[/]")
            return
        w = switch_to(name)
        if w:
            console.print(f"[green]Switched to:[/] {w.name} [dim]({w.path})[/]")
        else:
            console.print(f"[red]Workspace '{name}' not found or path inaccessible[/]")

    elif action == "auto":
        w = auto_discover()
        if w:
            console.print(f"[green]Auto-discovered:[/] {w.name} [dim]({w.path})[/]")
        else:
            console.print("[dim]Current directory already registered[/]")


# ── /gateway — IM message gateway status/start ──────────────────────


def _cmd_gateway(args: str) -> None:
    """Show IM messaging gateway platform configuration status.

    Displays which of the 9 supported platforms are configured
    (env vars set). Start with: tagent gateway start or tagent serve.
    """
    import os as _os

    from rich.table import Table

    platforms = [
        ("Telegram", "TELEGRAM_BOT_TOKEN"),
        ("Discord", "DISCORD_WEBHOOK_URL"),
        ("Slack", "SLACK_WEBHOOK_URL"),
        ("飞书", "FEISHU_WEBHOOK_URL"),
        ("企微", "WECHAT_WEBHOOK_URL"),
        ("钉钉", "DINGTALK_WEBHOOK_URL"),
        ("QQ Bot", "QQBOT_APP_ID"),
        ("Email", "SMTP_HOST"),
        ("Webhook", "GENERIC_WEBHOOK_URL"),
    ]

    table = Table(title="Gateway Platforms", show_header=True)
    table.add_column("Platform")
    table.add_column("Status")

    active = 0
    for name, env_var in platforms:
        configured = bool(_os.getenv(env_var))
        if configured:
            active += 1
        table.add_row(name, "[green]✓ configured[/]" if configured else "[dim]—[/]")

    console.print(table)
    console.print(f"\n[dim]{active}/9 configured. Start with [cyan]tagent serve[/] (daemon) or [cyan]tagent gateway[/] (messaging only).[/]")

# ── /task — structured task management ──────────────────────────────


def _task_add(rest: str) -> None:
    """Handle /task add <title> [--criteria <cond1>,<cond2>]."""
    from runtime.cli.tasks import add_task

    title = rest
    criteria: list[str] = []
    if " --criteria " in title or title.endswith(" --criteria"):
        if " --criteria " in title:
            title, crit_str = title.split(" --criteria ", 1)
        else:
            title = title.replace(" --criteria", "")
            crit_str = ""
        criteria = [c.strip() for c in crit_str.split(",") if c.strip()]
    if not title.strip():
        console.print("[dim]Usage: !task add <title> [--criteria <cond1>,<cond2>][/]")
        console.print("[dim]Example: /task add Run API smoke tests --criteria all P0 pass,coverage 80%[/]")
        return
    task = add_task(title, criteria=criteria)
    console.print(f"[green]Task #{task.id}:[/] {task.title}")
    if task.criteria:
        for c in task.criteria:
            console.print(f"  [dim]✓ criteria: {c}[/]")


def _task_list(rest: str) -> None:
    """Handle /task list [status_filter]."""
    from rich.table import Table
    from runtime.cli.tasks import list_tasks, stats

    status_filter = rest if rest else None
    tasks = list_tasks(status_filter)
    if not tasks:
        console.print("[dim]No tasks. Use !task add <title> to create one.[/]")
        return
    st = stats()
    console.print(f"[bold]Tasks:[/] {st['total']} total ({st['pending']} pending, {st['in_progress']} active, {st['done']} done)")
    table = Table(show_header=True)
    table.add_column("ID", style="dim")
    table.add_column("Status")
    table.add_column("Title")
    icons = {"pending": "○", "in_progress": "◉", "done": "✓", "cancelled": "✗"}
    for t in tasks[:10]:
        icon = icons.get(t.status, "?")
        color = {"done": "green", "in_progress": "cyan", "cancelled": "dim"}.get(t.status, "")
        table.add_row(t.id, f"[{color}]{icon} {t.status}[/]", t.title[:80])
    console.print(table)


def _task_done(rest: str) -> None:
    """Handle /task done <id>."""
    from runtime.cli.tasks import update_task

    tid = rest.strip()
    if not tid:
        console.print("[dim]Usage: !task done <id>[/]")
        return
    t = update_task(tid, status="done")
    if t:
        console.print(f"[green]Task #{tid} marked done:[/] {t.title}")
    else:
        console.print(f"[red]Task #{tid} not found.[/]")


def _task_start(rest: str) -> None:
    """Handle /task start <id>."""
    from runtime.cli.tasks import update_task

    tid = rest.strip()
    if not tid:
        console.print("[dim]Usage: !task start <id>[/]")
        return
    t = update_task(tid, status="in_progress")
    if t:
        console.print(f"[cyan]Task #{tid} started:[/] {t.title}")
    else:
        console.print(f"[red]Task #{tid} not found.[/]")


def _task_cancel(rest: str) -> None:
    """Handle /task cancel <id>."""
    from runtime.cli.tasks import update_task

    tid = rest.strip()
    if not tid:
        console.print("[dim]Usage: !task cancel <id>[/]")
        return
    t = update_task(tid, status="cancelled")
    if t:
        console.print(f"[dim]Task #{tid} cancelled.[/]")
    else:
        console.print(f"[red]Task #{tid} not found.[/]")


def _task_delete(rest: str) -> None:
    """Handle /task delete <id>."""
    from runtime.cli.tasks import delete_task

    tid = rest.strip()
    if not tid:
        console.print("[dim]Usage: !task delete <id>[/]")
        return
    if delete_task(tid):
        console.print(f"[dim]Task #{tid} deleted.[/]")
    else:
        console.print(f"[red]Task #{tid} not found.[/]")


def _task_stats(rest: str = "") -> None:
    """Handle /task stats."""
    from runtime.cli.tasks import stats

    st = stats()
    console.print(f"[bold]Task Stats:[/] {st['total']} total ({st['pending']} pending, {st['in_progress']} active, {st['done']} done)")


def _cmd_task(args: str) -> None:
    """Manage tasks: add, list, done, start, cancel, delete, stats. Usage: !task <action> [args]."""
    parts = args.strip().split(maxsplit=1)
    action = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    handlers = {
        "add": _task_add,
        "list": _task_list,
        "done": _task_done,
        "start": _task_start,
        "cancel": _task_cancel,
        "delete": _task_delete,
        "stats": _task_stats,
    }
    handler = handlers.get(action)
    if handler is None:
        if action:
            console.print(f"[red]Unknown action: {action}[/]")
            console.print("[dim]Use: add, list, done, start, cancel, delete, stats[/]")
        else:
            _task_list(rest)
        return
    handler(rest)


# ── /cross — cross-environment orchestration ────────────────────────


def _cmd_cross(args: str) -> None:
    """Run tests across environments: /cross env test staging <prompt>."""
    from runtime.cli.cross_env import run_cross_env
    from rich.table import Table

    parts = args.strip().split(None, 1)
    if len(parts) < 2 or parts[0] != "env":
        console.print("[dim]Usage: !cross env <env1> [env2...] <prompt>[/]")
        console.print("[dim]Example: /cross env test staging run API smoke tests[/]")
        console.print("[dim]Presets saved via /env save <name>[/]")
        return

    rest = parts[1]
    tokens = rest.split(maxsplit=1)
    sub = tokens[0].split()
    # env1 env2 ... → last token is prompt start, rest are envs
    prompt_part = sub[-1] if len(sub) >= 2 else ""
    envs = sub[:-1] if len(sub) >= 2 else sub
    prompt = f"{prompt_part} {tokens[1]}".strip() if len(tokens) > 1 else prompt_part
    if not envs:
        envs = ["test", "staging"]
        console.print("[yellow]No env specified, defaulting to test -> staging[/]")

    console.print(f"[bold]Cross-env:[/] {' → '.join(envs)} [dim](stop on first failure)[/]")
    with console.status("[bold]Running...", spinner="dots"):
        report = run_cross_env(prompt, envs)

    table = Table(title="Cross-Environment Results", show_header=True)
    table.add_column("Env")
    table.add_column("Result")
    table.add_column("Duration")
    for r in report.results:
        icon = "[green]✓[/]" if r.ok else "[red]✗[/]"
        dur = f"{r.duration_ms}ms" if r.duration_ms else "-"
        detail = f"{r.succeeded}/{r.total} ok" if r.total else r.error
        table.add_row(f"{icon} {r.env}", detail, dur)
    console.print(table)

    color = "green" if report.all_passed else "red"
    console.print(f"[{color}]{report.summary}[/]")
