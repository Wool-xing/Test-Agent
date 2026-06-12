"""Interactive REPL — terminal-based testing agent.

Bare `tagent` enters interactive session:
  - Natural language → LLM routing → streaming activity feed
  - !command → command dispatch with Tab completion + history
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




_SHEEP = r"""
    ✧  ▗▛ 🐏 ▜▖  ✧
         ▀▀▀▀▀
         ▐▌ ▐▌

  ૮₍˶ᵔ ᗜ ᵔ˶₎ა  Test-Agent v{version}
  AI Router · {experts} Experts · {skills} Skills
  Type !help for commands, or describe your test task."""

_SESSION_DIR = _Path(__file__).resolve().parents[2] / "workspace" / "gateway"
_SESSION_FILE = _SESSION_DIR / "active_session.json"
_HISTORY_FILE = _SESSION_DIR / "history.txt"

_memory: ConversationMemory | None = None
_last_trace: tuple | None = None  # (user_text, decision_dict) for /distill
_last_fix: str | None = None  # last suggested command correction
_start_time: float = 0.0
_cmd_history: list[str] = []  # last 10 user commands for /N quick re-run

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
    from runtime.config.settings import get_settings
    d = get_settings().project_root / dirname
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

    # Animated typewriter reveal — speed from skin config
    try:
        from runtime.cli.skins import get_skin, get_current_skin_name
        skin = get_skin(get_current_skin_name())
        animation_speed = skin.get("animation_speed", 0.0005)
        text_style = skin.get("panel_style", {}).get("text", "bold white")
    except Exception:
        animation_speed = 0.0005
        text_style = "bold white"
    try:
        from rich.markup import render as _render_markup
        accumulated = Text("")
        with Live(accumulated, console=console, refresh_per_second=120, transient=False) as live:
            for ch in banner:
                accumulated.append(ch)
                # Re-render with markup so colors appear inline
                live.update(Text.from_markup(str(accumulated)))
                time.sleep(animation_speed)
    except Exception:
        # Fallback: plain print if terminal doesn't support Live
        console.print(banner)

    console.print()


def _print_help() -> None:
    from rich.panel import Panel

    groups = [
        ("Run", [
            ("!task add|list|done|start", "Manage task list with criteria"),
            ("!test  <target>", "Full 11-step test pipeline"),
            ("!run   <target>", "Plan + execute (quick)"),
            ("!plan  <target>", "Plan only, no execution"),
        ]),
        ("Data & API", [
            ("!data users|related <N>", "Generate test data"),
            ("!api gen|test", "OpenAPI contract testing"),
            ("!cross env <e1> <e2>", "Cross-environment test run"),
        ]),
        ("Quality", [
            ("!regression", "Regression detection vs baseline"),
            ("!flaky list|quarantine", "Flaky test management"),
            ("!prioritize", "Prioritize by git changes"),
            ("!clean", "Clean temp data (preserves deliverables)"),
        ]),
        ("Info", [
            ("!update", "Check for newer version"),
            ("!progress", "Test coverage matrix"),
            ("!status", "Session, model, conversation stats"),
            ("!tools", "List agents + skills with status"),
            ("!ls", "Quick list experts + skills"),
            ("!doctor [--agents]", "Environment health check"),
            ("!ready", "Release readiness score"),
        ]),
        ("Control", [
            ("!model [provider] [model]", "Switch LLM (Tab to complete)"),
            ("!lang [zh|en|zh-en]", "Switch UI language"),
            ("!skin [name]", "Switch CLI theme (4 skins)"),
            ("!fc", "Fix last typo (like thefuck)"),
            ("!1..9", "Command history / re-run"),
            ("!alias add|list", "Command shortcuts"),
            ("!personality [name]", "Set agent persona (loads expert)"),
            ("!clear", "Reset conversation memory"),
            ("!undo", "Remove last exchange from memory"),
            ("!retry", "Re-run last prompt after undo"),
            ("!setup [--preset]", "Generate config files"),
            ("!check [--e2e]", "Framework self-test"),
        ]),
        ("Automation", [
            ("!hook add|list|prebuilt", "Lifecycle hooks (before/after/error)"),
        ]),
        ("Learning", [
            ("!distill", "Save last execution as reusable skill"),
        ]),
        ("Memory", [
            ("!remember <fact>", "Save fact to MEMORY.md"),
            ("!forget <keyword>", "Remove facts by keyword"),
            ("!nudge", "Scan session for facts worth remembering"),
            ("!memory", "Show MEMORY.md contents"),
        ]),
        ("Workspace", [
            ("!ws add|list|switch|auto", "Manage project workspaces"),
        ]),
        ("Gateway", [
            ("!gateway", "IM platform connection status"),
        ]),
        ("Session", [
            ("!cost", "Token usage and cost estimate"),
            ("!cache [clear]", "LLM response cache stats/clear"),
            ("!insights [days]", "Cross-session usage analytics"),
            ("!sessions", "List saved sessions"),
            ("!resume <id>", "Load a saved session"),
            ("!save", "Export conversation to markdown"),
            ("!compact", "Summarize and compress context"),
            ("!context", "Full conversation history"),
            ("!help", "This help"),
            ("!quit  (Ctrl+D)", "Save session and exit"),
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
        return f"{provider} service returned a server error. The provider may be down — try again or switch with [cyan]!model[/]."

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

    # Natural language → command trigger matching (fast path, no LLM)
    from runtime.cli.slash_commands import resolve_nl
    nl_cmd = resolve_nl(text)
    if nl_cmd:
        console.print(f"[dim]→ /{nl_cmd.name}[/]")
        nl_cmd.handler(text)
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
                # Stash trace for !distill command
                _last_trace = (text, ds)
                console.print("  [dim]💡 Multi-agent pattern detected. Run [cyan]/distill[/] to save as reusable skill.[/]")

        # Regression detection: compare against previous baseline
        if total >= 3 and rate >= 0.5:
            try:
                from runtime.cli.regression_tracker import RunResult, save_baseline, compare_with_baseline, is_regression
                current = RunResult(
                    run_id=run_id, total=total, succeeded=succ,
                    failed=summary.get("failed", 0), skipped=summary.get("skipped", 0),
                    duration_ms=int(elapsed),
                    node_results=summary.get("results", {}),
                    coverage_pct=rate * 100,
                )
                report = compare_with_baseline(current)
                save_baseline(current)
                if is_regression(report):
                    color = "red" if report.new_failures else "yellow"
                    console.print(f"  [{color}]⚠ Regression: {report.summary}[/] [dim](/regression for details)[/]")
                else:
                    console.print(f"  [dim]📈 {report.summary}[/]")

                # Flaky detection
                from runtime.cli.flaky_manager import record_run, get_flaky_list
                record_run(summary.get("results", {}), run_id)
            except Exception:
                pass
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
            console.print("  [dim]Run [cyan]!help[/] for commands, [cyan]!doctor[/] for health check.[/]")
        else:
            console.print("  [dim]Run [cyan]!doctor[/] to check environment, [cyan]!help[/] for commands.[/]")

        mem.add("assistant", f"[Error: {type(_exc).__name__}]")


# ── Fuzzy matching (thefuck-style) ─────────────────────────────────


# ── Slash Dispatch ─────────────────────────────────────────────

def _handle_slash(text: str) -> None:
    parts = text.lstrip("!").strip().split(maxsplit=1)
    name = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    # Trust check — warn on first use of non-builtin commands
    from runtime.cli.user_profile import is_trusted, trust_command
    if not is_trusted(name) and name not in {"quit", "q", "exit", "help", "h", "?", "status"}:
        console.print(f"[dim]First use of /{name} — trusted for future.[/]")
        trust_command(name)

    from runtime.cli.slash_commands import resolve, closest

    cmd = resolve(name)
    if cmd is None:
        suggestion = closest(name)
        if suggestion:
            from runtime.cli.slash_commands import resolve as _r
            _sugg = _r(suggestion)
            console.print(
                f"[red]Unknown: /{name}[/]  "
                f"[dim]Did you mean [/][cyan]/{suggestion}[/][dim]? Run [/][cyan]/fc[/][cyan][/][dim] to fix.[/]"
            )
        else:
            console.print(f"[red]Unknown: /{name}[/]  [dim](!help for commands)[/]")
        return

    try:
        cmd.handler(args)
    except SystemExit as e:
        if e.code and e.code != 0:
            console.print(f"[red]Command failed (exit {e.code})[/]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/]")
    except Exception as _exc:
        hint = _diagnose_error(_exc)
        if hint:
            console.print(f"[red]✗ {type(_exc).__name__}[/]")
            console.print(f"[yellow]💡 {hint}[/]")
        else:
            err_msg = str(_exc)[:200]
            console.print(f"[red]✗ {type(_exc).__name__}: {err_msg}[/]")
            console.print("[dim]!help for commands, !doctor for health check.[/]")


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
            from runtime.config.settings import get_settings
            checker = get_settings().config_dir / "check_version.py"
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

        # Multi-line detection: code blocks + !ml command
        if user_input.strip() == "!ml" or user_input.strip() == "!multiline":
            user_input = _read_multiline(session)
            if not user_input:
                continue
        elif _is_multiline_candidate(user_input):
            # Already contains newlines from paste — process as-is
            pass

        # Alias expansion: check non-slash input against aliases
        if not user_input.startswith("!"):
            from runtime.cli.aliases import expand_alias
            expanded = expand_alias(user_input)
            if expanded:
                console.print(f"[dim]→ {expanded}[/]")
                user_input = expanded

        # Record in command history (non-slash only)
        if not user_input.startswith("!"):
            _cmd_history.append(user_input)
            if len(_cmd_history) > 10:
                _cmd_history.pop(0)

        try:
            if user_input.startswith("!"):
                _handle_slash(user_input)
            else:
                _handle_natural_language(user_input)
        except SystemExit:
            break
        except Exception as exc:
            console.print(f"[red]Error: {exc}[/]")
            console.print("[dim]REPL continuing — !help for commands.[/]")
