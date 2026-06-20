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
import shutil
import sys
import time
from pathlib import Path as _Path

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

# Rich Markup → prompt_toolkit FormattedText converter
from rich.text import Text as RichText

from runtime.cli._shared import console
from runtime.cli.completer import _PROVIDERS, SlashCompleter
from runtime.cli.conversation import ConversationMemory
from runtime.config.settings import get_settings


_SHEEP = r"""
    ✧  ▗▛ 🐏 ▜▖  ✧
         ▀▀▀▀▀
         ▐▌ ▐▌

  ૮₍˶ᵔ ᗜ ᵔ˶₎ა  Test-Agent v{version}
  AI Router · {experts} Experts · {skills} Skills"""

_SESSION_DIR = get_settings().gateway_dir
_SESSION_FILE = _SESSION_DIR / "active_session.json"
_HISTORY_FILE = _SESSION_DIR / "history.txt"

_memory: ConversationMemory | None = None
_last_trace: tuple | None = None  # (user_text, decision_dict) for /distill
_last_fix: str | None = None  # last suggested command correction
_start_time: float = 0.0
_cmd_history: list[str] = []  # last 10 user commands for /N quick re-run
_BUILTIN_MAP: dict = {}

def _get_prompt_style() -> Style:
    """Build prompt_toolkit Style from active skin's colors (dynamic, not hardcoded)."""
    try:
        from runtime.cli.colorscheme import get_colorscheme
        return get_colorscheme().pt_style()
    except Exception:
        return Style.from_dict({
            "prompt": "bold cyan",
            "separator": "#888888",
            "bottom-toolbar": "bg:#1a1a2e fg:#a0a0c0",
            "bottom-toolbar.separator": "#444444",
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


@_kb.add("c-l")
def _redraw_screen(event):
    """Ctrl+L: clear and redraw screen (standard terminal behavior)."""
    event.app.renderer.clear()
    event.app.invalidate()


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
            message=[("class:prompt", "❯ "), ("class:prompt.dim", "[…] ")],
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
        first = console.input("[bold cyan]❯ [/]").strip()
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


def _icon(kind: str) -> str:
    """Get icon from active skin via ColorScheme."""
    try:
        from runtime.cli.colorscheme import get_colorscheme
        return get_colorscheme().icon(kind)
    except Exception:
        return {"ok": "✓", "fail": "✗", "warn": "⚠", "info": "💡"}.get(kind, "")


def _current_provider() -> str:
    return os.environ.get("TAGENT_LLM_PROVIDER", "claude")


def _current_model() -> str:
    """Resolve current model via model_router (no hardcoded list)."""
    if os.environ.get("TAGENT_LLM_MODEL"):
        return os.environ["TAGENT_LLM_MODEL"]
    try:
        from runtime.router.model_router import get_model_tier
        tier = get_model_tier()
        return tier.heavy_model
    except Exception:
        return "unknown"


# ── Status Bar & Prompt ──────────────────────────────────────────

_health_cache: tuple[float, list[dict]] = (0.0, [])  # (timestamp, issues)


def _term_width() -> int:
    try:
        return shutil.get_terminal_size().columns
    except Exception:
        return 80


def _cached_health() -> list[dict]:
    """Return cached health issues (refresh every 30s)."""
    global _health_cache
    now = time.time()
    if now - _health_cache[0] > 30:
        try:
            _health_cache = (now, get_settings().validate_startup())
        except Exception:
            _health_cache = (now, [])
    return _health_cache[1]


def _git_branch() -> str:
    """Return current git branch name, or empty string."""
    try:
        import subprocess
        r = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=3,
            cwd=str(get_settings().project_root),
        )
        return r.stdout.strip()
    except Exception:
        return ""


def _estimate_tokens(text: str) -> int:
    """Token count estimate. Uses tiktoken if available, else heuristic."""
    if not text:
        return 0
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        pass
    cjk = sum(1 for c in text if '一' <= c <= '鿿' or '぀' <= c <= 'ヿ')
    ascii_chars = len(text) - cjk
    return max(1, (ascii_chars // 4) + (cjk * 2 // 3))


def _context_pct() -> int:
    """Real token-based context usage percentage."""
    mem = _get_memory()
    if not mem or not mem.messages:
        return 0
    total = "".join(m.content for m in mem.messages if hasattr(m, 'content'))
    tokens = _estimate_tokens(total)
    model = _current_model().lower()
    _LIMITS = {"claude": 200000, "gpt-4": 128000, "deepseek": 128000,
               "gemini": 1000000, "qwen": 131072, "glm": 128000}
    limit = next((v for k, v in _LIMITS.items() if k in model), 200000)
    return min(99, int(tokens * 100 / limit))


def _render_prompt_message() -> list[tuple[str, str]]:
    """Prompt only — separator is in bottom toolbar (CC/DeepSeek pattern)."""
    return [("class:prompt", "❯ ")]


def _render_bottom_toolbar() -> "HTML":
    """Bottom separator + 4-line status bar (CC density). Returns HTML for PromptSession."""
    from prompt_toolkit.formatted_text import HTML
    w = _term_width()
    sep = "─" * w
    p = _current_provider()
    m = _current_model()
    b = _git_branch()
    pct = _context_pct()
    proj = os.environ.get("PROJECT_NAME", get_settings().project_root.name)

    # Health
    issues = _cached_health()
    errs = [i for i in issues if i["level"] == "error"]
    warns = [i for i in issues if i["level"] == "warning"]

    # Line 1: [provider model] · project · git · health
    model_str = f"<b>[{p}]</b>"
    if m and m != p:
        model_str += f" <b>[{m}]</b>"
    p1 = [model_str]
    # Show project folder name when PROJECT_NAME is the default
    proj_display = proj
    if proj == "default":
        proj_display = get_settings().project_root.name
    p1.append(f"<ansicyan>{proj_display}</ansicyan>")
    if b:
        p1.append(f"<ansigreen>git:{b}</ansigreen>")
    if errs:
        p1.append(f"<ansired>{_icon('warn')} {len(errs)}</ansired>")
    elif warns:
        p1.append(f"<ansiyellow>{_icon('warn')} {len(warns)}</ansiyellow>")
    else:
        p1.append(f"<ansigreen>{_icon('ok')}</ansigreen>")
    l1 = "  " + _fit_line(w - 2, p1)

    # Line 2: Context gauge (color-coded) + counts
    bar_len = 10
    filled = min(bar_len, pct * bar_len // 100)
    empty = bar_len - filled
    if pct >= 85:
        gauge = f"<ansired>{'█' * filled}</ansired>{'░' * empty}"
    elif pct >= 60:
        gauge = f"<ansiyellow>{'█' * filled}</ansiyellow>{'░' * empty}"
    else:
        gauge = f"<ansigray>{'█' * filled}</ansigray>{'░' * empty}"
    p2 = [f"Context {gauge} {pct}%"]
    if _count_md_files("agents"):
        p2.append(f"{_count_md_files('agents')} agents")
    if _count_md_files("skills"):
        p2.append(f"{_count_md_files('skills')} skills")
    l2 = "  " + _fit_line(w - 2, p2)

    # Line 3: Config files (dimmed, drops first on narrow terminals)
    root = get_settings().project_root
    p3 = []
    if (root / "CLAUDE.md").is_file():
        p3.append("CLAUDE.md")
    if (root / ".env").is_file():
        p3.append(".env")
    if (root / ".mcp.json").is_file():
        p3.append("MCP")
    l3 = "  <ansigray>" + _fit_line(w - 2, p3) + "</ansigray>" if p3 else ""

    # Line 4: Quick tips (CC-style, dimmed, first to collapse)
    l4 = "  <ansigray>" + _fit_line(w - 2, ["!help", "!doctor", "!model", "!status", "!clear"]) + "</ansigray>"

    return HTML(f"{sep}\n{l1}\n{l2}\n{l3}\n{l4}")


def _fit_line(width: int, parts: list[str]) -> str:
    """Fit as many parts as possible into `width` columns.
    Joins with " · " (DeepSeek/OI pattern). Drops rightmost first."""
    import re
    sep = " · "
    full = sep.join(parts)
    if len(re.sub(r'<[^>]+>', '', full)) <= width:
        return full
    for n in range(len(parts) - 1, 0, -1):
        candidate = sep.join(parts[:n])
        if len(re.sub(r'<[^>]+>', '', candidate)) <= width:
            return candidate
    return parts[0]




# ── Banner & Help ─────────────────────────────────────────────────


def _print_banner() -> None:
    """Compact banner: sheep + version + model + project (CC-style header)."""
    try:
        from runtime.cli.skins import apply_skin_to_banner
        banner = apply_skin_to_banner()
    except Exception:
        banner = _SHEEP
    console.print(banner)
    console.print(f"  [bold cyan]{_current_provider()}[/] · [dim]{_current_model()}[/]")
    console.print(f"  [dim]{get_settings().project_root}[/]")

    issues = _cached_health()
    errors = [i for i in issues if i["level"] == "error"]
    warnings = [i for i in issues if i["level"] == "warning"]
    ico = _icon("warn")
    if errors:
        console.print(f"  [red]{ico} {len(errors)} errors[/] · [dim]!doctor[/]")
    elif warnings:
        console.print(f"  [yellow]{ico} {len(warnings)} warnings[/] · [dim]!doctor[/]")

    console.print()


def _print_banner_transcript(tui: object) -> None:
    """Seed transcript TUI with banner + provider/model/project + health + startup stats."""
    try:
        from runtime.cli.skins import apply_skin_to_banner
        banner = apply_skin_to_banner()
    except Exception:
        banner = _SHEEP
    tui.append_output(banner)
    tui.append_output(f"  [bold cyan]{_current_provider()}[/] · [dim]{_current_model()}[/]")
    tui.append_output(f"  [dim]{get_settings().project_root}[/]")

    issues = _cached_health()
    errors = [i for i in issues if i["level"] == "error"]
    warnings = [i for i in issues if i["level"] == "warning"]
    if errors:
        tui.append_output(f"  [red]⚠ {len(errors)} errors[/] · [dim]!doctor[/]")
    elif warnings:
        tui.append_output(f"  [yellow]⚠ {len(warnings)} warnings[/] · [dim]!doctor[/]")

    # Condensed startup stats
    parts = []
    try:
        from runtime.cli.conversation import _discover_project_context, load_memory_md
        if _discover_project_context():
            parts.append("[dim]📋 CLAUDE.md[/]")
    except Exception:
        pass
    try:
        md = load_memory_md()
        if md:
            parts.append(f"[dim]🧠 {md.count(chr(10)) + 1}f[/]")
    except Exception:
        pass
    mem = _get_memory()
    if mem.messages:
        parts.append(f"[dim]{len(mem.messages)} turns[/]")
    if parts:
        tui.append_output("  " + " · ".join(parts))


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


def _render_rprompt() -> list[tuple[str, str]]:
    """Right-aligned prompt info — model + context % (compact, CC style)."""
    m = _current_model()
    pct = _context_pct()
    short = m[:14] + ".." if len(m) > 14 else m
    return [("class:prompt.dim", f"{short}  ")]


def _set_terminal_title(proj: str, model: str) -> None:
    """Set terminal title via OSC escape (CC/DeepSeek pattern)."""
    try:
        sys.stdout.write(f"\033]0;Test-Agent: {proj} ({model})\007")
        sys.stdout.flush()
    except Exception:
        pass


def _rich_to_pt(markup: str) -> FormattedText:
    """Convert Rich markup string to prompt_toolkit FormattedText.

    This is the bridge that lets us use Rich markup throughout the codebase
    while rendering output through prompt_toolkit's print_formatted_text().
    """
    rt = RichText.from_markup(markup)
    segments = []
    for span in rt.spans:
        start = span.start
        end = span.end
        text = rt.plain[start:end]
        style_str = str(span.style) if span.style else ""
        # Map Rich style names → prompt_toolkit style names
        pt_style = _rich_style_to_pt(style_str)
        segments.append((pt_style, text))
    return FormattedText(segments)


def _rich_style_to_pt(rich_style: str) -> str:
    """Map a Rich style string to a prompt_toolkit style string."""
    mapping = {
        "bold": "bold",
        "dim": "ansigray",
        "italic": "italic",
        "cyan": "ansicyan",
        "bright_cyan": "ansicyan",
        "green": "ansigreen",
        "bright_green": "ansigreen",
        "red": "ansired",
        "bright_red": "ansired",
        "yellow": "ansiyellow",
        "bright_yellow": "ansiyellow",
        "blue": "ansiblue",
        "magenta": "ansimagenta",
        "white": "",
        "bright_white": "bold",
        "black": "ansigray",
        "default": "",
    }
    parts = []
    for token in rich_style.split():
        token = token.strip()
        if not token:
            continue
        # Handle 'bold dim' → ['bold', 'ansigray']
        mapped = mapping.get(token, "")
        if mapped:
            parts.append(mapped)
    return " ".join(parts)


def _repl_print(markup: str = "", **kwargs: object) -> None:
    """Print to TUI via prompt_toolkit — does NOT corrupt terminal layout.

    Converts Rich markup to prompt_toolkit FormattedText, then uses
    print_formatted_text() which inserts output cleanly above the prompt.
    """
    from prompt_toolkit import print_formatted_text as pt_print
    try:
        ft = _rich_to_pt(markup)
        pt_print(ft)
    except Exception:
        # Fallback: print plain text
        import re as _re
        plain = _re.sub(r'\[[^\]]*\]', '', markup)
        pt_print(FormattedText([("", plain)]))


def _create_session() -> PromptSession | None:
    """Create prompt_toolkit session — dynamic style from skin, CC layout."""
    try:
        _SESSION_DIR.mkdir(parents=True, exist_ok=True)
        style = _get_prompt_style()
        return PromptSession(
            history=FileHistory(str(_HISTORY_FILE)),
            completer=SlashCompleter(),
            style=style,
            key_bindings=_kb,
            message=_render_prompt_message,
            rprompt=_render_rprompt,
            bottom_toolbar=_render_bottom_toolbar,
        )
    except Exception:
        return None


def _read_input(session: PromptSession | None) -> str | None:
    """Read user input. Uses prompt_toolkit if available, falls back to Rich."""
    if session is not None:
        try:
            return session.prompt(rprompt=_render_rprompt).strip()
        except Exception:
            pass
    try:
        return console.input("[bold cyan]❯ [/]").strip()
    except (EOFError, KeyboardInterrupt):
        return None


def _check_first_run() -> None:
    """Detect unconfigured state and show a friendly onboarding guide."""
    provider = _current_provider()
    if provider in ("ollama", "stub"):
        return  # local/stub — no API key needed

    # Check any *_API_KEY env var (openai/deepseek/anthropic/zhipu/... all use this convention)
    api_key = os.environ.get("TAGENT_LLM_API_KEY", "")
    if not api_key:
        api_key = next((v for k, v in os.environ.items() if k.endswith("_API_KEY") and v), "")
    has_env_file = (get_settings().project_root / ".env").exists()

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


def _suppress_noise() -> None:
    """Suppress third-party log noise (LiteLLM, Prefect, loguru) in interactive mode."""
    # Must be set BEFORE any litellm import — suppress cost-map fetch + debug
    os.environ["LITELLM_SUPPRESS_DEBUG_INFO"] = "1"
    os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

    # LiteLLM — aggressive suppression
    try:
        import litellm
        litellm.set_verbose = False
        litellm.suppress_debug_info = True
        # Silence litellm's own logger
        import logging as _logging
        for _name in ("litellm", "LiteLLM"):
            _logging.getLogger(_name).setLevel(_logging.ERROR)
    except Exception:
        pass

    # Prefect — silence ALL noise. Prefect 3.x uses stdlib logging, not env vars.
    os.environ.setdefault("PREFECT_LOGGING_LEVEL", "CRITICAL")
    os.environ["PREFECT_API_URL"] = ""  # block Prefect server startup
    try:
        import logging as _logging
        # Nuke every prefect logger to CRITICAL
        for _name in list(_logging.root.manager.loggerDict.keys()):
            if "prefect" in _name.lower():
                _logging.getLogger(_name).setLevel(_logging.CRITICAL)
        _logging.getLogger("prefect").setLevel(_logging.CRITICAL)
    except Exception:
        pass

    # loguru — route to stderr, ERROR only (WARNING during dev)
    try:
        from loguru import logger as _loguru
        _loguru.remove()
        _loguru.add(
            sys.stderr,
            level="ERROR",
            format="<dim>{time:HH:mm:ss}</dim> | <level>{level: <8}</level> | {message}",
            colorize=True,
        )
    except Exception:
        pass


def start() -> None:
    global _start_time
    _start_time = time.time()

    _suppress_noise()

    # ── Load essentials (no stdout — all display goes through transcript TUI) ──
    try:
        from runtime.plugins import discover_plugins
        for pname, pmod in (discover_plugins() or {}).items():
            try:
                info = pmod.register()
                if callable(info.get("run")):
                    _BUILTIN_MAP[pname] = lambda a, fn=info["run"]: None
            except Exception:
                pass
    except Exception:
        pass

    try:
        from runtime.scheduler.scheduler import start_background
        start_background()
    except Exception:
        pass

    # ── PromptSession REPL ──
    _set_terminal_title(
        proj=os.environ.get("PROJECT_NAME", get_settings().project_root.name),
        model=_current_model(),
    )

    _print_banner()
    _check_first_run()

    # Route Rich output → prompt_toolkit (after banner to stdout)
    _original_print = console.print

    def _pt_bridge(markup: str = "", **kwargs: object) -> None:
        try:
            _repl_print(markup, **kwargs)
        except Exception:
            _original_print(markup, **kwargs)

    console.print = _pt_bridge  # type: ignore[method-assign]

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
