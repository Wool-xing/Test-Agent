"""# Config commands: hook/skin/lang/personality + tools/context + cost/sessions/compact + memory — extracted from slash_handlers.py."""
from __future__ import annotations
import os, sys, time
from pathlib import Path
from runtime.cli._shared import console
from runtime.cli.slash_commands import _PROVIDERS
from runtime.cli.conversation import ConversationMemory
from runtime.config.settings import get_settings
from runtime.cli.interactive import _get_memory, _current_provider, _current_model, _handle_natural_language  # cross-sub-file
_SESSION_FILE = get_settings().gateway_dir / "active_session.json"
_SESSION_DIR = _SESSION_FILE.parent
# Module-local mutable state
_command_history_list = []
_last_fix = None
_last_trace = None
_start_time = 0.0


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
    """Compress conversation context. DCP-style: protect key content, nest summaries."""
    mem = _get_memory()
    if len(mem.messages) <= 4:
        console.print("[dim]Not enough conversation to compact.[/]")
        return

    # DCP: Protected content — never compress messages containing these patterns
    _PROTECT_PATTERNS = [
        "决策", "verdict", "no-go", "go", "conditional",
        "FAIL", "ERROR", "Bug", "P0", "P1",
        "[Compacted",  # nested summary preservation
    ]

    _protect = lambda m: any(p in m.content for p in _PROTECT_PATTERNS)

    # Separate protected from compressible
    protected_msgs = [m for m in mem.messages if _protect(m)]
    compressible = [m for m in mem.messages if not _protect(m)]

    if len(compressible) <= 4:
        console.print("[dim]Most content is protected — nothing to compact.[/]")
        return

    # Keep first 2 + last 2 of compressible, summarize middle
    kept = compressible[:2] + compressible[-2:]
    removed = len(compressible) - 4

    summary_parts = []
    prev_summary = None
    for m in compressible[2:-2]:
        if "[Compacted" in m.content:
            prev_summary = m.content[:120]  # DCP: preserve nested summary
            continue
        text = m.content[:60] + "..." if len(m.content) > 60 else m.content
        summary_parts.append(f"[{m.role}]: {text}")

    summary_text = f"[Compacted {removed} turns]"
    if prev_summary:
        summary_text += f"\n  (包含先前摘要: {prev_summary})"
    summary_text += "\n" + "\n".join(summary_parts[:8])

    from runtime.cli.conversation import Message
    summary_msg = Message(role="assistant", content=summary_text)

    # Reconstruct: first 2 compressible + summary + last 2 compressible + all protected
    mem._messages = kept[:2] + [summary_msg] + kept[2:] + protected_msgs
    mem._truncate()
    console.print(f"[green]Compacted {removed} turns → summary ({len(protected_msgs)} protected).[/]")
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
