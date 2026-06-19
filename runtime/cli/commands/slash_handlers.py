"""Slash command handlers — extracted from interactive.py."""
from __future__ import annotations
import os, sys, time
from pathlib import Path
from runtime.cli._shared import console
from runtime.cli.completer import _PROVIDERS
from runtime.cli.conversation import ConversationMemory
from runtime.config.settings import get_settings
_SESSION_FILE = get_settings().gateway_dir / "active_session.json"
_SESSION_DIR = _SESSION_FILE.parent
_command_history_list = []
_last_fix = None
_last_trace = None
_start_time = 0.0


def _get_memory():
    from runtime.cli.interactive import _get_memory as _m
    return _m()


def _current_provider():
    from runtime.cli.interactive import _current_provider as _f
    return _f()


def _current_model():
    from runtime.cli.interactive import _current_model as _f
    return _f()


def _closest_command(name: str) -> str | None:
    """Find closest matching command for typo correction. Returns name or None."""
    from runtime.cli.slash_commands import closest as _c
    return _c(name)
    for candidate in all_names:
        d = _edit_distance(name, candidate)
        if d < best_dist:
            best, best_dist = candidate, d

    # Only suggest if reasonably close (max 2 edits for short, 3 for long)
    threshold = 2 if len(name) <= 5 else 3
    return best if best_dist <= threshold else None


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein distance between two strings."""
    if len(a) < len(b):
        a, b = b, a
    if len(b) == 0:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(
                prev[j + 1] + 1,   # delete
                curr[j] + 1,        # insert
                prev[j] + (ca != cb),  # substitute
            ))
        prev = curr
    return prev[-1]


def _do_quit() -> None:
    _save_session()
    console.print("[dim]Session saved. Goodbye.[/]")
    raise SystemExit(0)


# ── !status ───────────────────────────────────────────────────────


def _cmd_status(args: str) -> None:
    from rich.panel import Panel

    mem = _get_memory()
    turns = len(mem.messages)
    chars = sum(len(m.content) for m in mem.messages)
    uptime_s = int(time.time() - _start_time)
    uptime = f"{uptime_s // 60}m {uptime_s % 60}s" if uptime_s > 0 else "just started"

    from runtime.cli.conversation import get_personality
    persona = get_personality()
    info = [
        f"Model:       [cyan]{_current_model()}[/]",
        f"Provider:    [cyan]{_current_provider()}[/]",
        f"Personality: [cyan]{persona or 'default'}[/]",
        f"Session:     [cyan]{mem.session_id}[/] · {turns} turns · {chars}/{mem.max_chars} chars",
        f"Uptime:      {uptime}",
    ]
    console.print(Panel("\n".join(info), title="Status", title_align="left"))

    if turns > 0:
        console.print(f"[bold]Recent ({min(turns, 5)} of {turns} turns):[/]")
        for m in mem.messages[-5:]:
            label = "[cyan]You[/]" if m.role == "user" else "[green]Agent[/]"
            text = m.content if len(m.content) <= 120 else m.content[:117] + "..."
            console.print(f"  {label}: {text}")
    else:
        console.print("[dim]No conversation yet.[/]")


# ── !model ────────────────────────────────────────────────────────


def _cmd_model(args: str) -> None:
    parts = args.strip().split()
    name = parts[0].lower() if parts else ""
    model_override = parts[1] if len(parts) > 1 else None
    current = _current_provider()

    if not name:
        console.print(f"Current: [cyan]{current}[/] → {_current_model()}\n")
        console.print("Available:")
        for p in _PROVIDERS:
            models = {
                "claude": "sonnet-4-6 / opus-4-8 / haiku-4-5",
                "openai": "gpt-4o / gpt-4.1 / o4-mini",
                "gemini": "gemini-1.5-pro / gemini-2.5-flash",
                "deepseek": "deepseek-chat / deepseek-reasoner",
                "qwen": "qwen-plus / qwen-max / qwen-turbo",
                "ollama": "any local model (e.g. qwen2.5:7b)",
            }
            marker = " [bold green]← current[/]" if p == current else ""
            detail = models.get(p, "")
            console.print(f"  [cyan]{p}[/]{marker}  [dim]{detail}[/]")
        console.print("\n[dim]Usage: !model <provider> [model]   e.g. !model deepseek deepseek-chat[/]")
        return

    # Check if user typed a model name instead of provider
    if name not in _PROVIDERS:
        # Try fuzzy match against known models → providers
        for p in _PROVIDERS:
            if name.startswith(p) or p.startswith(name):
                console.print(f"[yellow]'{name}' is a model name. Did you mean [cyan]!model {p}[/]?[/]")
                break
        else:
            console.print(f"[red]Unknown provider: {name}[/]")
            console.print(f"[dim]Available: {', '.join(_PROVIDERS)}[/]")
            console.print("[dim]Tip: provider first, then model — e.g. [cyan]!model deepseek deepseek-chat[/][/]")
        return

    os.environ["TAGENT_LLM_PROVIDER"] = name
    if model_override:
        os.environ["TAGENT_LLM_MODEL"] = model_override
    else:
        os.environ.pop("TAGENT_LLM_MODEL", None)  # use default

    # P3 #20: auto-learn provider preference
    try:
        from runtime.cli.user_profile import set_preference
        set_preference("provider", name)
        set_preference("model", _current_model())
    except Exception:
        pass

    console.print(f"[green]Switched[/] → provider: [cyan]{name}[/]  model: [cyan]{_current_model()}[/]")


# ── !cache — LLM response cache stats/clear ─────────────────────────


def _cmd_cache(args: str) -> None:
    """Show or clear the LLM response cache. Usage: !cache [clear]."""
    from runtime.router.llm_cache import cache_stats, clear_cache
    if args.strip() == "clear":
        n = clear_cache()
        console.print(f"[green]Cache cleared:[/] {n} entries removed")
        return
    stats = cache_stats()
    console.print(f"[bold]LLM Cache:[/] {stats['entries']} entries, {stats['size_kb']} KB, TTL={stats['ttl_hours']}h")
    if stats["entries"] > 0:
        console.print("[dim]Use !cache clear to flush.[/]")


# ── /! — command history ────────────────────────────────────────────


def _rerun_history(index: int) -> None:
    """Re-run a command from history by index (0=most recent)."""
    if not _command_history_list:
        console.print("[dim]No commands in history.[/]")
        return
    try:
        cmd = list(reversed(_command_history_list))[index]
        console.print(f"[dim]Re-running: [cyan]{cmd[:80]}{'...' if len(cmd) > 80 else ''}[/][/]")
        _handle_natural_language(cmd)
    except IndexError:
        console.print(f"[dim]History index {index + 1} not available.[/]")


def _cmd_history(args: str) -> None:
    """Show recent command history. Use /1..9 to re-run."""
    if not _command_history_list:
        console.print("[dim]No commands in history yet.[/]")
        return
    for i, cmd in enumerate(reversed(_command_history_list[-9:]), 1):
        preview = cmd[:100] + ("..." if len(cmd) > 100 else "")
        console.print(f"  [cyan]/{i}[/]  {preview}")
    console.print(f"[dim]Run /1 (most recent) through /{min(9, len(_command_history_list))} to re-execute.[/]")


# ── !fc — fix last command typo (thefuck-style) ────────────────────


def _cmd_fc(args: str) -> None:
    """Re-execute the last suggested command correction. Like 'thefuck' for slash commands."""
    global _last_fix
    if _last_fix is None:
        console.print("[dim]Nothing to fix. Type a command to get suggestions.[/]")
        return
    suggestion = _last_fix
    _last_fix = None
    console.print(f"[green]Running: /{suggestion}[/]")
    from runtime.cli.interactive import _BUILTIN_MAP
    _BUILTIN_MAP.get(suggestion, lambda a: None)("")


# ── /ready — release readiness score ─────────────────────────────────


def _cmd_ready(args: str) -> None:
    """Multi-dimensional release readiness check. Usage: !ready [--fast]."""
    from runtime.cli.readiness import run_readiness
    from rich.table import Table

    fast = "--fast" in args
    with console.status("[bold]Checking readiness...", spinner="dots"):
        report = run_readiness(fast=fast)

    table = Table(title="Release Readiness", show_header=True)
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")

    for g in report.gates:
        icon = "[green]✓[/]" if g.passed else "[red]✗[/]"
        table.add_row(f"{icon} {g.label}", f"{g.score:.0%}", g.detail)

    console.print(table)

    score_pct = report.overall_score * 100
    color = "green" if report.ready else "red"
    verdict = "✓ Ready to release" if report.ready else "✗ Not ready"
    console.print(f"\n[{color}]Overall: {score_pct:.0f}% — {verdict}[/]")
    if not report.ready:
        console.print("[dim]Fix failing checks above before release.[/]")


# ── /update — check for new version ──────────────────────────────────


def _cmd_update(args: str) -> None:
    """Check GitHub for newer version. Thin wrapper around deploy/config/check_version.py."""
    import subprocess
    import sys
    from runtime.config.settings import get_settings
    checker = get_settings().config_dir / "check_version.py"
    if not checker.is_file():
        console.print("[dim]Version checker not found.[/]")
        return
    r = subprocess.run([sys.executable, str(checker)], capture_output=True, text=True)
    if r.stdout.strip():
        console.print(r.stdout.strip())
    else:
        console.print("[green]Already up to date.[/]")


# ── /hook — lifecycle hook management ───────────────────────────────


def _cmd_hook(args: str) -> None:
    """Manage lifecycle hooks: /hook list | add <phase> <cmd> | remove <id> | prebuilt."""
    from runtime.orchestrator.user_hooks import (
        list_hooks, add_hook, remove_hook, PREBUILT_HOOKS, activate_all,
    )
    from rich.table import Table

    parts = args.strip().split(maxsplit=1)
    action = parts[0].lower() if parts else "list"
    rest = parts[1] if len(parts) > 1 else ""

    if action == "list" or not action:
        hooks = list_hooks()
        if not hooks:
            console.print("[dim]No hooks registered. Use !hook add or /hook prebuilt[/]")
            return
        table = Table(title=f"Hooks · {len(hooks)}", show_header=True)
        table.add_column("ID", style="dim")
        table.add_column("Phase")
        table.add_column("Label")
        active = 0
        for h in hooks:
            icon = "[green]✓[/]" if h.enabled else "[dim]—[/]"
            table.add_row(h.id[:8], f"{icon} {h.phase}", h.label or h.command[:60])
            if h.enabled:
                active += 1
        console.print(table)
        console.print(f"[dim]{active}/{len(hooks)} active[/]")

    elif action == "add":
        sub_parts = rest.strip().split(maxsplit=1)
        if len(sub_parts) < 2:
            console.print("[dim]Usage: !hook add <phase> <command>[/]")
            console.print("[dim]Phases: before | after | on_error[/]")
            console.print("[dim]Example: /hook add after 'echo done'[/]")
            return
        phase = sub_parts[0]
        if phase not in ("before", "after", "on_error"):
            console.print(f"[red]Unknown phase: {phase}. Use: before | after | on_error[/]")
            return
        h = add_hook(phase, sub_parts[1], f"user:{phase}")
        console.print(f"[green]Hook #{h.id}:[/] {phase} → {sub_parts[1][:60]}")

    elif action == "prebuilt":
        count = 0
        for p in PREBUILT_HOOKS:
            h = add_hook(p["phase"], p["command"], p["label"])
            count += 1
            console.print(f"[green]+ #{h.id}:[/] {p['label']}")
        console.print(f"[dim]{count} pre-built hooks added[/]")

    elif action == "remove":
        hid = rest.strip()
        if not hid:
            console.print("[dim]Usage: !hook remove <id>[/]")
            return
        if remove_hook(hid):
            console.print(f"[green]Hook #{hid} removed[/]")
        else:
            console.print(f"[red]Hook #{hid} not found[/]")

    elif action == "activate":
        n = activate_all()
        console.print(f"[green]{n} hooks activated[/]")


# ── !skin — switch CLI theme ────────────────────────────────────────


def _cmd_skin(args: str) -> None:
    """Switch CLI skin/theme. Usage: !skin [name]. No args lists available."""
    from runtime.cli.skins import list_skins, set_skin, get_current_skin_name

    name = args.strip().lower()
    if not name:
        current = get_current_skin_name()
        skins = list_skins()
        console.print(f"[bold]Available skins ({len(skins)}):[/]")
        for s in skins:
            marker = " [green]← active[/]" if s["active"] else ""
            console.print(f"  [cyan]{s['name']}{marker}[/] — {s['description']}")
        return

    if set_skin(name):
        console.print(f"[green]Skin:[/] [cyan]{name}[/] (restart REPL to see banner)")
    else:
        console.print(f"[dim]Unknown skin '{name}'. Use !skin to list.[/]")


# ── /lang — switch UI language ──────────────────────────────────────


def _cmd_lang(args: str) -> None:
    """Switch UI language. Supports: zh, en, zh-en (bilingual)."""
    from runtime.tutor.i18n import get_lang, set_lang
    name = args.strip().lower()
    if name not in ("zh", "en", "zh-en"):
        current = get_lang()
        console.print(f"Current: [cyan]{current}[/]")
        console.print("[dim]Usage: !lang zh | en | zh-en[/]")
        return
    set_lang(name)
    labels = {"zh": "中文", "en": "English", "zh-en": "中文/English"}
    console.print(f"[green]{labels.get(name, name)}[/]")


# ── /personality — set agent persona ────────────────────────────────


def _cmd_personality(args: str) -> None:
    """Switch active personality (loads agent .md as system prompt)."""
    from runtime.cli.conversation import get_personality, list_personalities, set_personality

    name = args.strip().lower()
    if not name:
        current = get_personality()
        personalities = list_personalities()
        console.print(f"[bold]Available personalities ({len(personalities)}):[/]")
        for p in personalities:
            marker = " [green]← active[/]" if p["name"] == current else ""
            console.print(f"  [cyan]{p['name']}{marker}[/] — {p['description']}")
        if not current:
            console.print("\n[dim]Usage: !personality <name>[/]")
        return

    if set_personality(name):
        console.print(f"[green]Personality:[/] [cyan]{name}[/] (injected into context)")
    else:
        console.print(f"[dim]Unknown personality '{name}'. Use !personality to list.[/]")


# ── /tools — dynamic agent/skill list ──────────────────────────────


def _cmd_tools(args: str) -> None:
    """List agents + skills with impl status (like Hermes /tools)."""
    from rich.table import Table

    try:
        from runtime.registry.registry import build_catalog
        catalog = build_catalog()
    except Exception:
        console.print("[red]Catalog unavailable.[/]")
        return

    entries = list(catalog.experts.values()) + list(catalog.skills.values())
    status_style = {"production": "green", "script": "yellow", "vision": "dim"}

    table = Table(title=f"Tools · {len(catalog.experts)} agents + {len(catalog.skills)} skills", show_header=True)
    table.add_column("Kind", style="dim", width=6)
    table.add_column("Name", style="cyan")
    table.add_column("Status", width=12)
    table.add_column("Description")

    for e in entries:
        s = e.impl_status
        style = status_style.get(s, "dim")
        table.add_row(e.kind, e.name, f"[{style}]{s}[/]", e.description[:60])

    console.print(table)


# ── /context /clear ───────────────────────────────────────────────


def _cmd_context(args: str) -> None:
    mem = _get_memory()
    if not mem.messages:
        console.print("[dim]No history.[/]")
        return
    console.print(f"[bold]Conversation ({len(mem.messages)} turns):[/]")
    for m in mem.messages:
        label = "[cyan]You[/]" if m.role == "user" else "[green]Agent[/]"
        text = m.content if len(m.content) <= 120 else m.content[:117] + "..."
        console.print(f"  {label}: {text}")


def _cmd_clear(args: str) -> None:
    _get_memory().clear()
    console.print("[dim]Cleared.[/]")


# ── /undo /retry — conversation control ────────────────────────────


def _cmd_undo(args: str) -> None:
    """Remove last user+assistant exchange from conversation memory.

    Can be called repeatedly to unwind multiple turns.
    Run !retry after undo to re-submit the undone prompt.
    """
    mem = _get_memory()
    user_text, assistant_text = mem.undo_last_exchange()
    if user_text is None:
        console.print("[dim]Nothing to undo.[/]")
        return
    console.print(f"[dim]Undone: [yellow]{user_text[:80]}{'...' if len(user_text) > 80 else ''}[/][/]")


def _cmd_retry(args: str) -> None:
    """Undo last assistant response and re-submit the last user prompt.

    Equivalent to /undo (assistant only) + re-running the prompt.
    Use when the agent gave a wrong or incomplete answer.
    """
    mem = _get_memory()
    if mem._messages and mem._messages[-1].role == "assistant":
        mem._messages.pop()
    last_user = mem.last_user_message()
    if last_user is None:
        console.print("[dim]Nothing to retry.[/]")
        return
    console.print(f"[dim]Retrying: [yellow]{last_user[:80]}{'...' if len(last_user) > 80 else ''}[/][/]")
    _handle_natural_language(last_user)


# ── /cost — token usage and cost estimate ─────────────────────────


_PRICE_PER_1K = {  # $ per 1K tokens (input, output)
    "claude": (0.003, 0.015),
    "openai": (0.0025, 0.01),
    "gemini": (0.000125, 0.000375),
    "deepseek": (0.00027, 0.0011),
    "qwen": (0.0005, 0.002),
    "ollama": (0, 0),
}


def _estimate_cost(mem: ConversationMemory) -> tuple[int, float]:
    """Estimate tokens and cost from conversation history. ~4 chars/token."""
    total_chars = sum(len(m.content) for m in mem.messages)
    user_chars = sum(len(m.content) for m in mem.messages if m.role == "user")
    assistant_chars = total_chars - user_chars
    in_tokens = max(user_chars // 4, 1)
    out_tokens = max(assistant_chars // 4, 1)

    provider = _current_provider()
    in_price, out_price = _PRICE_PER_1K.get(provider, (0, 0))
    cost = (in_tokens / 1000) * in_price + (out_tokens / 1000) * out_price
    return in_tokens + out_tokens, cost


def _cmd_cost(args: str) -> None:
    from rich.panel import Panel

    mem = _get_memory()
    tokens, cost = _estimate_cost(mem)

    info = [
        f"Provider: [cyan]{_current_provider()}[/] → {_current_model()}",
        f"Turns:    {len(mem.messages)}",
        f"Est. tokens: ~{tokens:,} (input + output)",
        f"Est. cost:   [bold]${cost:.4f}[/]",
    ]
    if _current_provider() == "ollama":
        info.append("[dim]Ollama is local — no API cost[/]")
    else:
        info.append("[dim]Estimate based on ~4 chars/token. Real costs may vary.[/]")
    console.print(Panel("\n".join(info), title="Cost", title_align="left"))


# ── /sessions — list saved sessions ────────────────────────────────


def _cmd_sessions(args: str) -> None:
    from datetime import datetime

    from rich.table import Table

    if not _SESSION_DIR.is_dir():
        console.print("[dim]No saved sessions.[/]")
        return

    files = sorted(_SESSION_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        console.print("[dim]No saved sessions.[/]")
        return

    table = Table(title=f"Saved Sessions ({len(files)})", show_header=True)
    table.add_column("Session ID", style="cyan")
    table.add_column("Turns")
    table.add_column("Date", style="dim")

    for f in files[:10]:
        sid = f.stem
        try:
            import json
            data = json.loads(f.read_text(encoding="utf-8"))
            turns = len(data.get("messages", []))
        except Exception:
            turns = "?"
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%m-%d %H:%M")
        marker = " [bold green]← active[/]" if f.name == "active_session.json" else ""
        table.add_row(sid, str(turns), mtime + marker)

    console.print(table)


# ── /resume — load a saved session ──────────────────────────────────


def _cmd_resume(args: str) -> None:
    """Load a previously saved session by filename or session_id prefix."""
    global _memory

    sid = args.strip()
    if not sid:
        console.print("[dim]Usage: !resume <session_id_or_filename>[/]")
        return

    match = None
    for f in sorted(_SESSION_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.name == sid or f.name == f"{sid}.json" or f.stem.startswith(sid):
            match = f
            break

    if match is None:
        console.print(f"[dim]No session matching '{sid}' found. Use !sessions to list.[/]")
        return

    loaded = ConversationMemory.load(match)
    if not loaded.messages:
        console.print("[dim]Session empty or corrupt.[/]")
        return

    _memory = loaded
    console.print(f"[green]Resumed:[/] {match.stem} ({len(loaded.messages)} messages)")


# ── /export — export conversation to markdown ──────────────────────


def _cmd_export(args: str) -> None:
    from datetime import datetime

    mem = _get_memory()
    if not mem.messages:
        console.print("[dim]Nothing to export.[/]")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _SESSION_DIR / f"export_{ts}.md"

    lines = [
        "# Test-Agent Session Export",
        "",
        f"**Session:** {mem.session_id}",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Turns:** {len(mem.messages)}",
        f"**Provider:** {_current_provider()}",
        "",
        "---",
        "",
    ]
    for m in mem.messages:
        role = "You" if m.role == "user" else "Agent"
        lines.append(f"### {role}")
        lines.append("")
        lines.append(m.content)
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"[green]Exported to {path}[/]")


# ── /compact — summarize and compress context ──────────────────────


def _cmd_compact(args: str) -> None:
    mem = _get_memory()
    if len(mem.messages) <= 4:
        console.print("[dim]Not enough conversation to compact.[/]")
        return

    kept = mem.messages[:2] + mem.messages[-2:]
    removed = len(mem.messages) - 4

    summary_parts = []
    for m in mem.messages[2:-2]:
        text = m.content[:80] + "..." if len(m.content) > 80 else m.content
        summary_parts.append(f"[{m.role}]: {text}")

    from runtime.cli.conversation import Message
    summary_msg = Message(
        role="assistant",
        content=f"[Compacted {removed} turns]\n" + "\n".join(summary_parts[:10]),
    )

    mem._messages = kept[:2] + [summary_msg] + kept[2:]
    mem._truncate()  # re-enforce budget after manual message manipulation
    console.print(f"[green]Compacted {removed} turns → summary.[/]")
    console.print(f"[dim]Turns: {len(mem.messages)} · Chars: {sum(len(m.content) for m in mem.messages)}[/]")


# ── /remember /forget — persistent cross-session memory ────────────


def _cmd_remember(args: str) -> None:
    """Save a fact to MEMORY.md for cross-session persistence."""
    fact = args.strip()
    if not fact:
        console.print("[red]Usage: !remember <fact>[/]")
        console.print("[dim]Example: /remember This project uses PostgreSQL[/]")
        return
    from runtime.cli.conversation import load_memory_md, save_memory_fact
    save_memory_fact(fact)
    console.print(f"[green]Remembered:[/] {fact}")
    # Show current memory size
    mem = load_memory_md()
    lines = mem.count("\n") + 1 if mem else 0
    console.print(f"[dim]{lines} fact(s) in MEMORY.md[/]")


def _cmd_forget(args: str) -> None:
    """Remove facts from MEMORY.md matching a keyword."""
    keyword = args.strip()
    if not keyword:
        console.print("[red]Usage: !forget <keyword>[/]")
        console.print("[dim]Example: /forget PostgreSQL[/]")
        return
    from runtime.cli.conversation import forget_memory_fact, load_memory_md
    removed = forget_memory_fact(keyword)
    if removed > 0:
        console.print(f"[green]Forgot {removed} fact(s) matching '{keyword}'[/]")
    else:
        console.print(f"[dim]No facts matching '{keyword}'[/]")
    mem = load_memory_md()
    lines = mem.count("\n") + 1 if mem else 0
    console.print(f"[dim]{lines} fact(s) remaining[/]")


def _cmd_memory(args: str) -> None:
    """Display current MEMORY.md contents."""
    from runtime.cli.conversation import load_memory_md
    mem = load_memory_md()
    if not mem:
        console.print("[dim]MEMORY.md is empty. Use !remember <fact> to save knowledge.[/]")
        return
    from rich.panel import Panel
    lines = mem.count("\n") + 1
    console.print(Panel(mem, title=f"MEMORY.md ({lines} facts)", title_align="left"))


# ── /mcp — list and call MCP tools ────────────────────────────────


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
    path = distill_skill(trace, name)
    console.print(f"[green]Skill created:[/] {path}")
    _last_trace = None  # consume once


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


def _cmd_task(args: str) -> None:
    """Manage tasks: add, list, done, cancel. Usage: !task <action> [args]."""
    from rich.table import Table

    from runtime.cli.tasks import add_task, delete_task, list_tasks, stats, update_task

    parts = args.strip().split(maxsplit=1)
    action = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""

    if action == "add":
        # Format: /task add <title> [--criteria <cond1>,<cond2>]
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

    elif action == "list" or not action:
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

    elif action == "done":
        tid = rest.strip()
        if not tid:
            console.print("[dim]Usage: !task done <id>[/]")
            return
        t = update_task(tid, status="done")
        if t:
            console.print(f"[green]Task #{tid} marked done:[/] {t.title}")
        else:
            console.print(f"[red]Task #{tid} not found.[/]")

    elif action == "start":
        tid = rest.strip()
        if not tid:
            console.print("[dim]Usage: !task start <id>[/]")
            return
        t = update_task(tid, status="in_progress")
        if t:
            console.print(f"[cyan]Task #{tid} started:[/] {t.title}")
        else:
            console.print(f"[red]Task #{tid} not found.[/]")

    elif action == "cancel":
        tid = rest.strip()
        if not tid:
            console.print("[dim]Usage: !task cancel <id>[/]")
            return
        t = update_task(tid, status="cancelled")
        if t:
            console.print(f"[dim]Task #{tid} cancelled.[/]")
        else:
            console.print(f"[red]Task #{tid} not found.[/]")

    elif action == "delete":
        tid = rest.strip()
        if not tid:
            console.print("[dim]Usage: !task delete <id>[/]")
            return
        if delete_task(tid):
            console.print(f"[dim]Task #{tid} deleted.[/]")
        else:
            console.print(f"[red]Task #{tid} not found.[/]")

    else:
        console.print(f"[red]Unknown action: {action}[/]")
        console.print("[dim]Use: add, list, done, start, cancel, delete[/]")


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
    # Parse env names (before last part = prompt)
    tokens = rest.split(maxsplit=1)
    # env1 env2 ... → first is env, rest is prompt
    sub = tokens[0].split()
    envs = sub[:-1]  # env names
    prompt = sub[-1]  # last token is prompt start
    if len(tokens) > 1:
        prompt += " " + tokens[1]

    if not envs:
        envs = ["test", "staging"]

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


# ── /clean — data cleanup (preserve deliverables) ───────────────────


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
