"""Interactive REPL — terminal-based testing agent.

Bare `tagent` enters interactive session:
  - Natural language → LLM routing → streaming activity feed
  - /command  → slash dispatch with Tab completion + history
  - ↑↓ arrows → command history
  - Ctrl+C    → interrupt (REPL stays alive)
  - Ctrl+D    → quit (auto-saves session)
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path as _Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from runtime.cli._shared import console
from runtime.cli.completer import _PROVIDERS, SlashCompleter
from runtime.cli.conversation import ConversationMemory
from runtime.cli.slash_commands import COMMAND_REGISTRY
from runtime.cli.slash_commands import resolve as resolve_command

_SHEEP = r"""
    ✧  ▗▛ 🐏 ▜▖  ✧
         ▀▀▀▀▀
         ▐▌ ▐▌

  ૮₍˶ᵔ ᗜ ᵔ˶₎ა  Test-Agent v{version}
  AI Router · {experts} Experts · {skills} Skills
  Type /help for commands, or describe your test task."""

_SESSION_DIR = _Path(__file__).resolve().parents[2] / "workspace" / "gateway"
_SESSION_FILE = _SESSION_DIR / "active_session.json"
_HISTORY_FILE = _SESSION_DIR / "history.txt"

_memory: ConversationMemory | None = None
_last_trace: tuple | None = None  # (user_text, decision_dict) for /distill
_last_fix: str | None = None  # last suggested command correction
_start_time: float = 0.0

_PROMPT_STYLE = Style.from_dict({
    "prompt": "bold cyan",
})

# Key bindings: Ctrl+D exits, Alt+Enter inserts newline for multi-line input
_kb = KeyBindings()


@_kb.add("escape", "enter")
def _insert_newline(event):
    """Alt+Enter: insert newline in multi-line input."""
    event.app.current_buffer.insert_text("\n")


@_kb.add("c-d")
def _ctrl_d_exit(event):
    """Ctrl+D: exit REPL."""
    event.app.exit(result=None)


_ML_START_MARKERS = ('"""', "'''", "```")  # triggers for auto multi-line mode


def _read_multiline(session: PromptSession | None) -> str:
    """Read multi-line input with continuation prompts.

    Submit with empty line. Code blocks (```) auto-continue until closed.
    Falls back to single-line if prompt_toolkit unavailable.
    """
    if session is None:
        return _fallback_multiline()

    lines = []
    try:
        first = session.prompt(
            message=[("class:prompt", "> "), ("class:prompt.dim", "[…] ")],
        )
        if first is None:
            return ""
        first = first.rstrip()
        if not first:
            return ""
        lines.append(first)

        # Auto-continue for code blocks
        in_block = any(first.strip().startswith(m) for m in _ML_START_MARKERS)

        while True:
            marker = "… " if in_block else "· "
            try:
                line = session.prompt(message=[("class:prompt.dim", marker)])
            except (EOFError, KeyboardInterrupt):
                break
            if line is None:
                break
            line = line.rstrip()
            # Empty line submits (unless inside code block)
            if not line and not in_block:
                break
            # Closing code block marker
            if in_block and any(line.strip().startswith(m) for m in _ML_START_MARKERS):
                lines.append(line)
                break
            lines.append(line)
            if not in_block:
                break  # single continuation only for non-block
    except (EOFError, KeyboardInterrupt):
        pass

    return "\n".join(lines)


def _fallback_multiline() -> str:
    """Read multi-line input without prompt_toolkit (Git Bash fallback)."""
    lines = []
    try:
        first = console.input("[bold cyan]> [/]").strip()
        if not first:
            return ""
        lines.append(first)
        in_block = any(first.startswith(m) for m in _ML_START_MARKERS)
        while True:
            line = console.input("… " if in_block else "· ").strip()
            if not line and not in_block:
                break
            if in_block and any(line.startswith(m) for m in _ML_START_MARKERS):
                lines.append(line)
                break
            lines.append(line)
            if not in_block:
                break
    except (EOFError, KeyboardInterrupt):
        pass
    return "\n".join(lines)


def _is_multiline_candidate(text: str) -> bool:
    """Check if text should trigger multi-line input mode."""
    text = text.strip()
    if not text:
        return False
    if any(text.startswith(m) for m in _ML_START_MARKERS):
        return True
    if "\n" in text:
        return True
    return False


def _get_memory() -> ConversationMemory:
    global _memory
    if _memory is None:
        _memory = ConversationMemory.load(_SESSION_FILE)
    return _memory


def _count_md_files(dirname: str) -> int:
    d = _Path(__file__).resolve().parents[2] / dirname
    if not d.is_dir():
        return 0
    return len([f for f in d.glob("*.md") if f.name.upper() != "README.MD"])


_PROVIDER_MODELS = {
    "claude": "claude-sonnet-4-6", "openai": "gpt-4o",
    "gemini": "gemini-1.5-pro", "deepseek": "deepseek-chat",
    "qwen": "qwen-plus", "ollama": "qwen2.5:7b",
}


def _current_provider() -> str:
    return os.environ.get("TAGENT_LLM_PROVIDER", "claude")


def _current_model() -> str:
    return os.environ.get("TAGENT_LLM_MODEL", _PROVIDER_MODELS.get(_current_provider(), "unknown"))


# ── Banner & Help ─────────────────────────────────────────────────


def _print_banner() -> None:
    from rich.live import Live
    from rich.text import Text

    banner = _SHEEP  # fallback
    try:
        from runtime.cli.skins import apply_skin_to_banner
        banner = apply_skin_to_banner()
    except Exception:
        pass  # use default _SHEEP

    # Animated typewriter reveal
    try:
        accumulated = Text("")
        with Live(accumulated, console=console, refresh_per_second=120, transient=False) as live:
            for ch in banner:
                accumulated.append_text(Text(ch, style="bold white"))
                live.update(accumulated)
                time.sleep(0.0005)
    except Exception:
        # Fallback: plain print if terminal doesn't support Live
        console.print(banner)

    console.print()


def _print_help() -> None:
    from rich.panel import Panel

    groups = [
        ("Run", [
            ("/task add|list|done|start", "Manage task list with criteria"),
            ("/test  <target>", "Full 11-step test pipeline"),
            ("/run   <target>", "Plan + execute (quick)"),
            ("/plan  <target>", "Plan only, no execution"),
        ]),
        ("Info", [
            ("/update", "Check for newer version"),
            ("/status", "Session, model, conversation stats"),
            ("/tools", "List agents + skills with status"),
            ("/ls", "Quick list experts + skills"),
            ("/doctor [--agents]", "Environment health check"),
            ("/ready", "Release readiness score"),
        ]),
        ("Control", [
            ("/model [provider] [model]", "Switch LLM (Tab to complete)"),
            ("/lang [zh|en|zh-en]", "Switch UI language"),
            ("/skin [name]", "Switch CLI theme (4 skins)"),
            ("/fc", "Fix last typo (like thefuck)"),
            ("/personality [name]", "Set agent persona (loads expert)"),
            ("/clear", "Reset conversation memory"),
            ("/undo", "Remove last exchange from memory"),
            ("/retry", "Re-run last prompt after undo"),
            ("/setup [--preset]", "Generate config files"),
            ("/check [--e2e]", "Framework self-test"),
        ]),
        ("Learning", [
            ("/distill", "Save last execution as reusable skill"),
        ]),
        ("Memory", [
            ("/remember <fact>", "Save fact to MEMORY.md"),
            ("/forget <keyword>", "Remove facts by keyword"),
            ("/nudge", "Scan session for facts worth remembering"),
            ("/memory", "Show MEMORY.md contents"),
        ]),
        ("Gateway", [
            ("/gateway", "IM platform connection status"),
        ]),
        ("Session", [
            ("/cost", "Token usage and cost estimate"),
            ("/cache [clear]", "LLM response cache stats/clear"),
            ("/insights [days]", "Cross-session usage analytics"),
            ("/sessions", "List saved sessions"),
            ("/resume <id>", "Load a saved session"),
            ("/export", "Export conversation to markdown"),
            ("/compact", "Summarize and compress context"),
            ("/context", "Full conversation history"),
            ("/help", "This help"),
            ("/quit  (Ctrl+D)", "Save session and exit"),
        ]),
    ]

    console.print()
    for title, items in groups:
        body = "\n".join(f"  {cmd:22s} {desc}" for cmd, desc in items)
        console.print(Panel(body, title=title, title_align="left"))
    console.print("[dim]↑↓ history · Tab completion · Bare text → LLM routing[/]")
    console.print()


# ── Error Diagnosis ─────────────────────────────────────────────────


def _diagnose_error(exc: Exception) -> str | None:
    """Return a friendly Chinese/English hint for common errors. None if no specific advice."""
    _msg = str(exc).lower()
    _t = type(exc).__name__

    # API key / auth errors
    if any(k in _msg for k in ("api_key", "api key", "apikey", "unauthorized", "401", "credential", "authentication")):
        provider = _current_provider()
        return (
            f"LLM ({provider}) needs an API key. "
            f"Set [cyan]TAGENT_LLM_API_KEY[/] in [cyan].env[/] or environment. "
            f"Run [cyan]tagent setup --preset minimal[/] to generate a template."
        )

    # Missing module / import errors
    if _t in ("ModuleNotFoundError", "ImportError"):
        mod = _msg.split("'")[1] if "'" in _msg else "?"
        return (
            f"Missing Python package: [cyan]{mod}[/]. "
            f"Run [cyan]pip install -e runtime/[/] or [cyan]pip install {mod}[/]."
        )

    # Connection / network errors
    if any(k in _msg for k in ("connection", "timeout", "refused", "unreachable", "ssl", "dns", "resolve")):
        return (
            "Cannot reach the LLM service. Check your network, proxy settings, "
            "or [cyan]TAGENT_LLM_API_BASE[/] in [cyan].env[/]."
        )

    # Rate limit
    if any(k in _msg for k in ("rate limit", "429", "too many")):
        return "Rate limited by the LLM provider. Wait a moment and try again."

    # Invalid request / bad gateway from LLM
    if any(k in _msg for k in ("500", "502", "503", "internal", "bad gateway")):
        provider = _current_provider()
        return f"{provider} service returned a server error. The provider may be down — try again or switch with [cyan]/model[/]."

    # General: give the error message itself as info, with next steps
    return None


# ── Streaming Activity Feed ────────────────────────────────────────


def _execute_with_progress(run_id: str, decision) -> dict:
    """Run decision with Rich Live progress table. Returns summary dict."""
    from rich.live import Live
    from rich.table import Table

    from runtime.cli._shared import _kernel

    progress_table = Table(show_header=True, box=None)
    progress_table.add_column("#", style="dim", width=3)
    progress_table.add_column("Node", style="cyan")
    progress_table.add_column("Status", width=8)
    progress_table.add_column("Duration", style="dim", width=8)

    completed: list[dict] = []

    def _on_node(result: dict) -> None:
        nid = result.get("id", "?")
        name = result.get("name", nid)[:30]
        ok = result.get("ok", False)
        dur = result.get("duration_ms", 0)
        status = "[green]✓[/]" if ok else "[red]✗[/]"
        dur_str = f"{dur:.0f}ms" if dur else ""
        completed.append(result)
        progress_table.add_row(str(len(completed)), name, status, dur_str)

    with Live(progress_table, console=console, refresh_per_second=8, transient=False):
        return _kernel.execute_sync(run_id, decision, on_progress=_on_node)


def _handle_natural_language(text: str) -> None:
    """Route through routing kernel with streaming activity output."""
    global _last_trace
    if not text.strip():
        return

    mem = _get_memory()
    has_history = len(mem.messages) > 0
    context_input = mem.build_context(text)
    mem.add("user", text)  # add AFTER build_context to avoid duplicating current input
    _label = text[:80] + ("..." if len(text) > 80 else "")

    if has_history:
        console.print(f"[dim]Turn {len(mem.messages)//2 + 1} · \"{_label}\"[/]")
    else:
        console.print(f"[dim]\"{_label}\"[/]")

    t0 = time.time()
    try:
        from runtime.cli._shared import _kernel, build_artifact

        # ── fast-path: direct agent/skill invocation ──
        from runtime.router.intent import try_fast_path
        decision = try_fast_path(text)

        if decision is not None:
            console.print(f"[dim]⚡ Direct: {', '.join(n.name for n in decision.dag)}[/]")
            run_id = f"direct-{decision.dag[0].id}" if decision.dag else "direct"
            # Submit for persistence but skip LLM routing
            art = build_artifact(text, "")
            run_id, _ = _kernel.submit(art, persist=False)
        else:
            with console.status("[bold green]Routing...", spinner="dots"):
                art = build_artifact(context_input, "")
                run_id, decision = _kernel.submit(art, persist=False)

        print_dag = __import__("runtime.cli._shared", fromlist=["print_dag"]).print_dag
        print_dag(decision)

        summary = _execute_with_progress(run_id, decision)

        elapsed = (time.time() - t0) * 1000
        total = summary["total"]
        succ = summary["succeeded"]
        rate = succ / total if total else 0.0
        console.print(f"  [green]✓ {succ}/{total} ok ({rate:.0%})[/]  [dim]({elapsed:.0f}ms)[/]")
        mem.add("assistant", f"DAG: {succ}/{total} ok, {summary.get('failed', 0)} failed")

        # P3 #18: auto-learn skill scores
        try:
            from runtime.learning_loop.skill_scorer import auto_learn_and_recommend
            rec = auto_learn_and_recommend()
            if rec:
                console.print(f"  [dim]📊 {rec}[/]")
        except Exception:
            pass

        # P3 #23: voice announce
        try:
            from runtime.cli.voice import announce_result
            announce_result(summary)
        except Exception:
            pass

        # Skill distillation hint (≥3 nodes, multi-agent)
        if total >= 3 and rate >= 0.8:
            ds = decision.model_dump() if hasattr(decision, "model_dump") else {}
            nodes = ds.get("dag", ds.get("nodes", []))
            if len(set(n.get("kind", "") for n in nodes)) >= 2:
                # Stash trace for /distill command
                _last_trace = (text, ds)
                console.print("  [dim]💡 Multi-agent pattern detected. Run [cyan]/distill[/] to save as reusable skill.[/]")
    except KeyboardInterrupt:
        console.print(f"  [yellow]Cancelled[/]  [dim]({(time.time()-t0)*1000:.0f}ms)[/]")
        mem.add("assistant", "[Cancelled]")
    except Exception as _exc:
        _err_msg = str(_exc)[:300]
        elapsed = (time.time() - t0) * 1000
        console.print(f"  [red]✗ {type(_exc).__name__}[/]  [dim]({elapsed:.0f}ms)[/]")

        # ── friendly guidance based on error type ──
        _hint = _diagnose_error(_exc)
        if _hint:
            console.print(f"  [yellow]💡 {_hint}[/]")
        elif _err_msg:
            console.print(f"  [dim]{_err_msg}[/]")
            console.print("  [dim]Run [cyan]/help[/] for commands, [cyan]/doctor[/] for health check.[/]")
        else:
            console.print("  [dim]Run [cyan]/doctor[/] to check environment, [cyan]/help[/] for commands.[/]")

        mem.add("assistant", f"[Error: {type(_exc).__name__}]")


# ── Fuzzy matching (thefuck-style) ─────────────────────────────────


def _closest_command(name: str) -> str | None:
    """Find closest matching command for typo correction. Returns name or None."""
    all_names = set(_BUILTIN_MAP.keys())
    for cmd in COMMAND_REGISTRY:
        all_names.add(cmd.name)
        all_names.update(cmd.aliases)

    best, best_dist = None, 999
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


# ── /status ───────────────────────────────────────────────────────


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


# ── /model ────────────────────────────────────────────────────────


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
        console.print("\n[dim]Usage: /model <provider> [model]   e.g. /model deepseek deepseek-chat[/]")
        return

    # Check if user typed a model name instead of provider
    if name not in _PROVIDERS:
        # Try fuzzy match against known models → providers
        for p in _PROVIDERS:
            if name.startswith(p) or p.startswith(name):
                console.print(f"[yellow]'{name}' is a model name. Did you mean [cyan]/model {p}[/]?[/]")
                break
        else:
            console.print(f"[red]Unknown provider: {name}[/]")
            console.print(f"[dim]Available: {', '.join(_PROVIDERS)}[/]")
            console.print("[dim]Tip: provider first, then model — e.g. [cyan]/model deepseek deepseek-chat[/][/]")
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


# ── /cache — LLM response cache stats/clear ─────────────────────────


def _cmd_cache(args: str) -> None:
    """Show or clear the LLM response cache. Usage: /cache [clear]."""
    from runtime.router.llm_cache import cache_stats, clear_cache
    if args.strip() == "clear":
        n = clear_cache()
        console.print(f"[green]Cache cleared:[/] {n} entries removed")
        return
    stats = cache_stats()
    console.print(f"[bold]LLM Cache:[/] {stats['entries']} entries, {stats['size_kb']} KB, TTL={stats['ttl_hours']}h")
    if stats["entries"] > 0:
        console.print("[dim]Use /cache clear to flush.[/]")


# ── /fc — fix last command typo (thefuck-style) ────────────────────


def _cmd_fc(args: str) -> None:
    """Re-execute the last suggested command correction. Like 'thefuck' for slash commands."""
    global _last_fix
    if _last_fix is None:
        console.print("[dim]Nothing to fix. Type a command to get suggestions.[/]")
        return
    suggestion = _last_fix
    _last_fix = None
    console.print(f"[green]Running: /{suggestion}[/]")
    _BUILTIN_MAP.get(suggestion, lambda a: None)("")


# ── /ready — release readiness score ─────────────────────────────────


def _cmd_ready(args: str) -> None:
    """Multi-dimensional release readiness check. Usage: /ready [--fast]."""
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
    """Check GitHub for newer version. Thin wrapper around config/check_version.py."""
    import subprocess
    import sys
    checker = _Path(__file__).resolve().parents[2] / "config" / "check_version.py"
    if not checker.is_file():
        console.print("[dim]Version checker not found.[/]")
        return
    r = subprocess.run([sys.executable, str(checker)], capture_output=True, text=True)
    if r.stdout.strip():
        console.print(r.stdout.strip())
    else:
        console.print("[green]Already up to date.[/]")


# ── /skin — switch CLI theme ────────────────────────────────────────


def _cmd_skin(args: str) -> None:
    """Switch CLI skin/theme. Usage: /skin [name]. No args lists available."""
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
        console.print(f"[dim]Unknown skin '{name}'. Use /skin to list.[/]")


# ── /lang — switch UI language ──────────────────────────────────────


def _cmd_lang(args: str) -> None:
    """Switch UI language. Supports: zh, en, zh-en (bilingual)."""
    from runtime.tutor.i18n import get_lang, set_lang
    name = args.strip().lower()
    if name not in ("zh", "en", "zh-en"):
        current = get_lang()
        console.print(f"Current: [cyan]{current}[/]")
        console.print("[dim]Usage: /lang zh | en | zh-en[/]")
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
            console.print("\n[dim]Usage: /personality <name>[/]")
        return

    if set_personality(name):
        console.print(f"[green]Personality:[/] [cyan]{name}[/] (injected into context)")
    else:
        console.print(f"[dim]Unknown personality '{name}'. Use /personality to list.[/]")


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
    Run /retry after undo to re-submit the undone prompt.
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
        console.print("[dim]Usage: /resume <session_id_or_filename>[/]")
        return

    match = None
    for f in sorted(_SESSION_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.name == sid or f.name == f"{sid}.json" or f.stem.startswith(sid):
            match = f
            break

    if match is None:
        console.print(f"[dim]No session matching '{sid}' found. Use /sessions to list.[/]")
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
        console.print("[red]Usage: /remember <fact>[/]")
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
        console.print("[red]Usage: /forget <keyword>[/]")
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
        console.print("[dim]MEMORY.md is empty. Use /remember <fact> to save knowledge.[/]")
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
        console.print("[red]Usage: /mcp-call <server> <tool> [json_args][/]")
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
            console.print("[dim]No scheduled jobs. Use /cron add <cron> <prompt>[/]")
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
            console.print("[red]Usage: /cron add <schedule> <prompt>[/]")
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
            console.print("[red]Usage: /cron remove <job_id>[/]")
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


# ── /model-router — display auto-routing configuration ─────────────


def _cmd_model_router(args: str) -> None:
    """Show model auto-routing tiers (P2 #14)."""
    from rich.table import Table

    from runtime.router.model_router import (
        MODEL_TIERS,
        get_current_provider,
    )

    current = get_current_provider()
    table = Table(title="Model Auto-Router · P2 #14", show_header=True)
    table.add_column("Provider", style="cyan")
    table.add_column("Light (routing)", style="dim")
    table.add_column("Heavy (execution)", style="bold")

    for prov, tier in MODEL_TIERS.items():
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
    console.print("[dim]Override via /model <provider> [model] or TAGENT_LLM_MODEL env[/]")


# ── /search — full-text conversation search (P3 #16) ───────────────


def _cmd_search(args: str) -> None:
    """Search conversation history with FTS5."""
    query = args.strip()
    if not query:
        console.print("[red]Usage: /search <query>[/]")
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
    Usage: /distill [name] — name is auto-generated if omitted.
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
    """Manage tasks: add, list, done, cancel. Usage: /task <action> [args]."""
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
            console.print("[dim]Usage: /task add <title> [--criteria <cond1>,<cond2>][/]")
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
            console.print("[dim]No tasks. Use /task add <title> to create one.[/]")
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
            console.print("[dim]Usage: /task done <id>[/]")
            return
        t = update_task(tid, status="done")
        if t:
            console.print(f"[green]Task #{tid} marked done:[/] {t.title}")
        else:
            console.print(f"[red]Task #{tid} not found.[/]")

    elif action == "start":
        tid = rest.strip()
        if not tid:
            console.print("[dim]Usage: /task start <id>[/]")
            return
        t = update_task(tid, status="in_progress")
        if t:
            console.print(f"[cyan]Task #{tid} started:[/] {t.title}")
        else:
            console.print(f"[red]Task #{tid} not found.[/]")

    elif action == "cancel":
        tid = rest.strip()
        if not tid:
            console.print("[dim]Usage: /task cancel <id>[/]")
            return
        t = update_task(tid, status="cancelled")
        if t:
            console.print(f"[dim]Task #{tid} cancelled.[/]")
        else:
            console.print(f"[red]Task #{tid} not found.[/]")

    elif action == "delete":
        tid = rest.strip()
        if not tid:
            console.print("[dim]Usage: /task delete <id>[/]")
            return
        if delete_task(tid):
            console.print(f"[dim]Task #{tid} deleted.[/]")
        else:
            console.print(f"[red]Task #{tid} not found.[/]")

    else:
        console.print(f"[red]Unknown action: {action}[/]")
        console.print("[dim]Use: add, list, done, start, cancel, delete[/]")


# ── /insights — cross-session analytics ─────────────────────────────


def _cmd_insights(args: str) -> None:
    """Show usage analytics across saved sessions.

    Scans workspace/gateway/*.json for session data.
    Usage: /insights [days] — default 30 days.
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


# ── /doctor — comprehensive environment health check ────────────────


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
    console.print(f"\n[bold]{ok_count} checks passed[/]   [dim]Run /help for next steps.[/]")


# ── /nudge — suggest facts worth remembering ───────────────────────


def _cmd_nudge(args: str) -> None:
    """Scan recent conversation for facts worth persisting to MEMORY.md.

    Detects patterns: config changes, preferences, decisions.
    Use /remember <fact> to save suggestions, /memory to review.
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
        console.print("[dim]No notable facts detected. Use /remember <fact> manually.[/]")
        return
    console.print("[bold]Suggestions from this session:[/]")
    for i, s in enumerate(suggestions[:5], 1):
        preview = s[:100] + ("..." if len(s) > 100 else "")
        console.print(f"  {i}. {preview}")
    if existing:
        console.print(f"\n[dim]MEMORY.md has {len(existing)} chars. /forget <keyword> to clean.[/]")


# ── Slash Dispatch (after all cmd fns) ────────────────────────────


_BUILTIN_MAP = {
    "help": lambda a: _print_help(), "h": lambda a: _print_help(), "?": lambda a: _print_help(),
    "quit": lambda a: _do_quit(), "q": lambda a: _do_quit(), "exit": lambda a: _do_quit(),
    "status": _cmd_status, "model": _cmd_model,
    "lang": _cmd_lang,
    "skin": _cmd_skin,
    "update": _cmd_update,
    "ready": _cmd_ready,
    "personality": _cmd_personality,
    "tools": _cmd_tools,
    "cost": _cmd_cost, "usage": _cmd_cost,
    "sessions": _cmd_sessions,
    "resume": _cmd_resume,
    "export": _cmd_export,
    "compact": _cmd_compact,
    "context": _cmd_context, "clear": _cmd_clear,
    "undo": _cmd_undo, "retry": _cmd_retry,
    "session": _cmd_status,
    "remember": _cmd_remember, "forget": _cmd_forget, "memory": _cmd_memory,
    "nudge": _cmd_nudge,
    "mcp": _cmd_mcp_tools, "mcp-call": _cmd_mcp_call,
    "cron": _cmd_cron, "cron-health": _cmd_cron_health,
    "model-router": _cmd_model_router,
    "search": _cmd_search,
    "skill-score": _cmd_skill_score,
    "speak": _cmd_speak,
    "plugins": _cmd_plugins_list,
    "distill": _cmd_distill,
    "cache": _cmd_cache,
    "fc": _cmd_fc, "fuck": _cmd_fc,
    "doctor": _cmd_doctor,
    "insights": _cmd_insights,
    "task": _cmd_task,
    "gateway": _cmd_gateway,
    "ml": lambda a: None, "multiline": lambda a: None,  # handled by REPL loop
}


def _handle_slash(text: str) -> None:
    parts = text.lstrip("/").strip().split(maxsplit=1)
    name = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    # Trust check — warn on first use of non-builtin commands (P3 #21)
    from runtime.cli.user_profile import is_trusted, trust_command
    if not is_trusted(name) and name not in {"quit", "q", "exit", "help", "h", "?", "status"}:
        console.print(f"[dim]First use of /{name} — trusted for future.[/]")
        trust_command(name)

    if name in _BUILTIN_MAP:
        try:
            _BUILTIN_MAP[name](args)
        except SystemExit:
            raise
        except Exception as _exc:
            _hint = _diagnose_error(_exc)
            if _hint:
                console.print(f"[red]✗ {type(_exc).__name__}[/]")
                console.print(f"[yellow]💡 {_hint}[/]")
            else:
                _err_msg = str(_exc)[:200]
                console.print(f"[red]✗ {type(_exc).__name__}: {_err_msg}[/]")
                console.print("[dim]/help for commands, /doctor for health check.[/]")
        return

    cmd = resolve_command(name)
    if cmd is None:
        global _last_fix
        suggestion = _closest_command(name)
        if suggestion:
            _last_fix = suggestion
            console.print(
                f"[red]Unknown: /{name}[/]  "
                f"[dim]Did you mean [/][cyan]/{suggestion}[/][dim]? Run [/][cyan]/fc[/][cyan][/][dim] to fix.[/]"
            )
        else:
            console.print(f"[red]Unknown: /{name}[/]  [dim](/help for commands)[/]")
        return

    try:
        cmd.handler(args)
    except SystemExit as e:
        if e.code and e.code != 0:
            console.print(f"[red]Command failed (exit {e.code})[/]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/]")
    except Exception as _exc:
        _hint = _diagnose_error(_exc)
        if _hint:
            console.print(f"[red]✗ {type(_exc).__name__}[/]")
            console.print(f"[yellow]💡 {_hint}[/]")
        else:
            _err_msg = str(_exc)[:200]
            console.print(f"[red]✗ {type(_exc).__name__}: {_err_msg}[/]")
            console.print("[dim]/help for commands, /doctor for health check.[/]")


# ── Persistence ───────────────────────────────────────────────────


def _save_session() -> None:
    mem = _get_memory()
    if mem.messages:
        mem.dump(_SESSION_FILE)
        # Memory nudge: after substantial session, suggest remembering key facts
        exchanges = len([m for m in mem.messages if m.role == "user"])
        if exchanges >= 5:
            console.print(f"\n[dim]💾 Session saved ({exchanges} exchanges). [/][cyan]/remember <fact>[/][dim] to persist key learnings.[/]")


# ── REPL Entry ────────────────────────────────────────────────────


def _create_session() -> PromptSession | None:
    """Create prompt_toolkit session. Returns None if TTY unsupported."""
    try:
        _SESSION_DIR.mkdir(parents=True, exist_ok=True)
        return PromptSession(
            history=FileHistory(str(_HISTORY_FILE)),
            completer=SlashCompleter(),
            style=_PROMPT_STYLE,
            key_bindings=_kb,
            message=[("class:prompt", "> ")],
        )
    except Exception:
        return None


def _read_input(session: PromptSession | None) -> str | None:
    """Read user input. Uses prompt_toolkit if available, falls back to Rich."""
    if session is not None:
        try:
            return session.prompt().strip()
        except Exception:
            pass  # fall through to fallback
    try:
        return console.input("[bold cyan]> [/]").strip()
    except (EOFError, KeyboardInterrupt):
        return None


def _check_first_run() -> None:
    """Detect unconfigured state and show a friendly onboarding guide."""
    provider = _current_provider()
    if provider in ("ollama", "stub"):
        return  # local/stub — no API key needed

    api_key = os.environ.get("TAGENT_LLM_API_KEY", "")
    has_env_file = (_Path(__file__).resolve().parents[2] / ".env").exists()

    if not api_key and not has_env_file:
        console.print(
            "\n[yellow]👋 欢迎！看起来这是你第一次使用 Test-Agent。[/]\n"
            "[bold]快速上手 (3 步):[/]\n"
            "  1. [cyan]tagent setup --preset minimal[/]  → 生成 .env 模板\n"
            "  2. 编辑 [cyan].env[/] → 填入你的 LLM API key\n"
            "  3. [cyan]tagent demo -y[/]  → 一键验证 (0 费用, stub 模式)\n"
            "\n[dim]现在可以先跑 demo 看看效果: /check --e2e[/]\n"
        )
    elif not api_key:
        console.print(
            f"\n[yellow]⚠️  当前 provider [cyan]{provider}[/] 未配置 API key。[/]\n"
            f"  [dim]设置: set TAGENT_LLM_API_KEY=你的key[/]\n"
            f"  [dim]或在 .env 文件中添加: TAGENT_LLM_API_KEY=你的key[/]\n"
        )


def start() -> None:
    global _start_time
    _start_time = time.time()

    _print_banner()
    _check_first_run()

    # Version check (non-blocking, 24h rate-limited by check_version.py)
    try:
        import subprocess
        import threading
        def _check_version():
            checker = _Path(__file__).resolve().parents[2] / "config" / "check_version.py"
            if checker.is_file():
                r = subprocess.run([sys.executable, str(checker)], capture_output=True, text=True, timeout=8)
                if r.stdout.strip():
                    console.print(r.stdout.strip())
        t = threading.Thread(target=_check_version, daemon=True)
        t.start()
    except Exception:
        pass

    # Auto-learn user preferences (P3 #20)
    try:
        from runtime.cli.user_profile import learn_from_usage
        prefs = learn_from_usage()
        if prefs:
            console.print(f"[dim]👤 Profile: {', '.join(f'{k}={v}' for k,v in prefs.items())}[/]")
    except Exception:
        pass

    # Load plugins (P3 #22)
    try:
        from runtime.plugins import discover_plugins
        plugins = discover_plugins()
        if plugins:
            for pname, pmod in plugins.items():
                try:
                    info = pmod.register()
                    run_fn = info.get("run")
                    if callable(run_fn):
                        _BUILTIN_MAP[pname] = lambda a, fn=run_fn: (
                            console.print(f"[green]Plugin {pname}:[/] {fn(a)}")
                        )
                except Exception:
                    pass
            console.print(f"[dim]🔌 {len(plugins)} plugin(s) loaded[/]")
    except Exception:
        pass

    # Load project context (CLAUDE.md / AGENTS.md auto-discovered)
    try:
        from runtime.cli.conversation import _discover_project_context
        proj_ctx = _discover_project_context()
        if proj_ctx:
            console.print("[dim]📋 Project context loaded[/]")
    except Exception:
        pass

    # Start background scheduler for cron jobs
    try:
        from runtime.scheduler.scheduler import start_background
        thread, stop = start_background()
        console.print(f"[dim]⏰ Scheduler started (tick={60}s)[/]")
    except Exception:
        pass  # scheduler is optional — croniter may not be installed

    # Show cross-session memory status
    from runtime.cli.conversation import load_memory_md
    mem_md = load_memory_md()
    if mem_md:
        facts = mem_md.count("\n") + 1
        console.print(f"[dim]🧠 {facts} fact(s) loaded from MEMORY.md[/]\n")

    mem = _get_memory()
    if mem.messages:
        console.print(f"[dim]Resumed {mem.session_id} ({len(mem.messages)} turns)[/]\n")

    session = _create_session()
    if session is None:
        console.print(
            "[dim](Tab completion not available in Git Bash / mintty. "
            "Use cmd.exe, Windows Terminal, or PowerShell for full features.)[/]\n"
        )

    while True:
        try:
            result = _read_input(session)
            if result is None:
                _save_session()
                console.print("\n[dim]Session saved. Goodbye.[/]")
                break
            user_input = result
        except (EOFError, KeyboardInterrupt):
            _save_session()
            console.print("\n[dim]Session saved. Goodbye.[/]")
            break

        if not user_input:
            continue

        # Multi-line detection: code blocks + /ml command
        if user_input.strip() == "/ml" or user_input.strip() == "/multiline":
            user_input = _read_multiline(session)
            if not user_input:
                continue
        elif _is_multiline_candidate(user_input):
            # Already contains newlines from paste — process as-is
            pass

        try:
            if user_input.startswith("/"):
                _handle_slash(user_input)
            else:
                _handle_natural_language(user_input)
        except SystemExit:
            break
        except Exception as exc:
            console.print(f"[red]Error: {exc}[/]")
            console.print("[dim]REPL continuing — /help for commands.[/]")
