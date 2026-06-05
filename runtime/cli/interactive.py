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
import time
from pathlib import Path as _Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style

from runtime.cli._shared import console
from runtime.cli.completer import SlashCompleter
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
_start_time: float = 0.0

_PROVIDERS = ["claude", "openai", "gemini", "deepseek", "qwen", "ollama"]
_PROMPT_STYLE = Style.from_dict({
    "prompt": "bold cyan",
})

# Key bindings: Ctrl+D exits, Ctrl+C handled by KeyboardInterrupt
_kb = KeyBindings()


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


def _current_provider() -> str:
    return os.environ.get("TAGENT_LLM_PROVIDER", "claude")


def _current_model() -> str:
    models = {
        "claude": "claude-sonnet-4-6", "openai": "gpt-4o",
        "gemini": "gemini-1.5-pro", "deepseek": "deepseek-chat",
        "qwen": "qwen-plus", "ollama": "qwen2.5:7b",
    }
    return os.environ.get("TAGENT_LLM_MODEL", models.get(_current_provider(), "unknown"))


# ── Banner & Help ─────────────────────────────────────────────────


def _print_banner() -> None:
    import runtime
    console.print(_SHEEP.format(
        version=runtime.__version__,
        experts=_count_md_files("agents"),
        skills=_count_md_files("skills"),
    ))
    console.print()


def _print_help() -> None:
    from rich.panel import Panel

    groups = [
        ("Run", [
            ("/test  <target>", "Full 11-step test pipeline"),
            ("/run   <target>", "Plan + execute (quick)"),
            ("/plan  <target>", "Plan only, no execution"),
        ]),
        ("Info", [
            ("/status", "Session, model, conversation stats"),
            ("/tools", "List agents + skills with status"),
            ("/ls", "Quick list experts + skills"),
            ("/doctor [--agents]", "Environment health check"),
            ("/ready", "Release readiness score"),
        ]),
        ("Control", [
            ("/model [provider] [model]", "Switch LLM (Tab to complete)"),
            ("/clear", "Reset conversation memory"),
            ("/setup [--preset]", "Generate config files"),
            ("/check [--e2e]", "Framework self-test"),
        ]),
        ("Session", [
            ("/cost", "Token usage and cost estimate"),
            ("/sessions", "List saved sessions"),
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


def _handle_natural_language(text: str) -> None:
    """Route through routing kernel with streaming activity output."""
    if not text.strip():
        return

    mem = _get_memory()
    has_history = len(mem.messages) > 0
    context_input = mem.build_context(text)
    mem.add("user", text)  # add AFTER build_context to avoid duplicating current input
    summary = text[:80] + ("..." if len(text) > 80 else "")

    if has_history:
        console.print(f"[dim]Turn {len(mem.messages)//2 + 1} · \"{summary}\"[/]")
    else:
        console.print(f"[dim]\"{summary}\"[/]")

    t0 = time.time()
    try:
        from runtime.cli._shared import _kernel, build_artifact

        with console.status("[bold green]Routing...", spinner="dots"):
            art = build_artifact(context_input, "")
            run_id, decision = _kernel.submit(art, persist=False)

        print_dag = __import__("runtime.cli._shared", fromlist=["print_dag"]).print_dag
        print_dag(decision)

        summary = _kernel.execute_sync(run_id, decision)
        elapsed = (time.time() - t0) * 1000
        total = summary["total"]
        succ = summary["succeeded"]
        rate = succ / total if total else 0.0
        console.print(f"  [green]✓ {succ}/{total} ok ({rate:.0%})[/]  [dim]({elapsed:.0f}ms)[/]")
        mem.add("assistant", f"DAG: {succ}/{total} ok, {summary.get('failed', 0)} failed")
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

    info = [
        f"Model:    [cyan]{_current_model()}[/]",
        f"Provider: [cyan]{_current_provider()}[/]",
        f"Session:  [cyan]{mem.session_id}[/] · {turns} turns · {chars}/{mem.max_chars} chars",
        f"Uptime:   {uptime}",
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

    console.print(f"[green]Switched[/] → provider: [cyan]{name}[/]  model: [cyan]{_current_model()}[/]")


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
    console.print(f"[green]Compacted {removed} turns → summary.[/]")
    console.print(f"[dim]Turns: {len(mem.messages)} · Chars: {sum(len(m.content) for m in mem.messages)}[/]")


# ── Slash Dispatch (after all cmd fns) ────────────────────────────


_BUILTIN_MAP = {
    "help": lambda a: _print_help(), "h": lambda a: _print_help(), "?": lambda a: _print_help(),
    "quit": lambda a: _do_quit(), "q": lambda a: _do_quit(), "exit": lambda a: _do_quit(),
    "status": _cmd_status, "model": _cmd_model,
    "tools": _cmd_tools,
    "cost": _cmd_cost, "usage": _cmd_cost,
    "sessions": _cmd_sessions,
    "export": _cmd_export,
    "compact": _cmd_compact,
    "context": _cmd_context, "clear": _cmd_clear,
    "session": _cmd_status,
}


def _handle_slash(text: str) -> None:
    parts = text.lstrip("/").strip().split(maxsplit=1)
    name = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if name in _BUILTIN_MAP:
        try:
            _BUILTIN_MAP[name](args)
        except SystemExit:
            raise
        return

    cmd = resolve_command(name)
    if cmd is None:
        suggestion = _closest_command(name)
        if suggestion:
            console.print(
                f"[red]Unknown: /{name}[/]  "
                f"[dim]Did you mean [/][cyan]/{suggestion}[/][dim]?[/]"
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
    except Exception:
        console.print("[red]Command failed[/]")


# ── Persistence ───────────────────────────────────────────────────


def _save_session() -> None:
    mem = _get_memory()
    if mem.messages:
        mem.dump(_SESSION_FILE)


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
