"""Interactive REPL — Claude Code / Hermes Agent / OpenClaw style terminal session.

Bare `tagent` (no subcommand) enters this interactive loop:
  - Natural language → LLM routing → agent orchestration
  - /command  → slash command dispatch
  - Ctrl+C    → interrupt (REPL stays alive)
  - Ctrl+D    → quit (auto-saves)
"""

from __future__ import annotations

import os
import time
from pathlib import Path as _Path

from runtime.cli._shared import console
from runtime.cli.conversation import ConversationMemory
from runtime.cli.slash_commands import COMMAND_REGISTRY, resolve as resolve_command

_SHEEP = r"""
    ✧  ▗▛ 🐏 ▜▖  ✧
         ▀▀▀▀▀
         ▐▌ ▐▌

  ૮₍˶ᵔ ᗜ ᵔ˶₎ა  Test-Agent v{version}
  AI Router · {experts} Experts · {skills} Skills
  Type /help for commands, or describe your test task."""

_SESSION_DIR = _Path(__file__).resolve().parents[2] / "workspace" / "gateway"
_SESSION_FILE = _SESSION_DIR / "active_session.json"

_memory: ConversationMemory | None = None
_start_time: float = 0.0

# Available LLM providers (from config/llm-providers.md)
_PROVIDERS = ["claude", "openai", "gemini", "deepseek", "qwen", "ollama"]


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
    provider = _current_provider()
    models = {
        "claude": "claude-sonnet-4-6",
        "openai": "gpt-4o",
        "gemini": "gemini-1.5-pro",
        "deepseek": "deepseek-chat",
        "qwen": "qwen-plus",
        "ollama": "qwen2.5:7b",
    }
    return os.environ.get("TAGENT_LLM_MODEL", models.get(provider, "unknown"))


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
            ("/ls", "List experts + skills"),
            ("/doctor [--agents]", "Environment health check"),
            ("/ready", "Release readiness score"),
        ]),
        ("Control", [
            ("/model [name]", "Switch LLM provider"),
            ("/clear", "Reset conversation memory"),
            ("/setup [--preset]", "Generate config files"),
            ("/check [--e2e]", "Framework self-test"),
        ]),
        ("Session", [
            ("/help", "This help"),
            ("/demo [--real-llm]", "Quick demo"),
            ("/quit  (Ctrl+D)", "Save session and exit"),
        ]),
    ]

    console.print()
    for title, items in groups:
        body = "\n".join(f"  {cmd:22s} {desc}" for cmd, desc in items)
        console.print(Panel(body, title=title, title_align="left"))
    console.print("[dim]Bare text → LLM routing → agent execution (with context)[/]")
    console.print()


# ── Natural Language ──────────────────────────────────────────────


def _handle_natural_language(text: str) -> None:
    if not text.strip():
        return

    mem = _get_memory()
    mem.add("user", text)
    context_input = mem.build_context(text)
    has_history = len(mem.messages) > 1
    summary = text[:80] + ("..." if len(text) > 80 else "")

    if has_history:
        console.print(f"[dim]Turn {len(mem.messages)//2 + 1}: \"{summary}\"[/]")
    else:
        console.print(f"[dim]Analyzing: \"{summary}\"[/]")

    try:
        import sys as _sys
        _sys.argv = ["tagent", "run", context_input]
        with console.status("[bold green]Routing via LLM...", spinner="dots"):
            from runtime.cli.commands.run import run as _run
            _run()
        mem.add("assistant", f"[Run completed: {text}]")
    except SystemExit:
        pass
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/]")
        mem.add("assistant", "[Cancelled]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/]")
        mem.add("assistant", f"[Error: {exc}]")


# ── Slash Command Dispatch ────────────────────────────────────────


def _handle_slash(text: str) -> None:
    parts = text.lstrip("/").strip().split(maxsplit=1)
    name = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    # Built-in REPL commands (not in global registry)
    builtins = {
        "help": lambda a: _print_help(),
        "h": lambda a: _print_help(),
        "?": lambda a: _print_help(),
        "quit": lambda a: _do_quit(),
        "q": lambda a: _do_quit(),
        "exit": lambda a: _do_quit(),
        "status": _cmd_status,
        "model": _cmd_model,
        "context": _cmd_context,
        "clear": _cmd_clear,
        "session": _cmd_status,  # redirect to /status
    }

    if name in builtins:
        try:
            builtins[name](args)
        except SystemExit:
            raise
        return

    cmd = resolve_command(name)
    if cmd is None:
        console.print(f"[red]Unknown: /{name}[/]  [dim](/help for commands)[/]")
        return

    try:
        cmd.handler(args)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/]")
    except Exception as exc:
        console.print(f"[red]Failed: {exc}[/]")


def _do_quit() -> None:
    _save_session()
    console.print("[dim]Session saved. Goodbye.[/]")
    raise SystemExit(0)


# ── /status — session + model + conversation ──────────────────────


def _cmd_status(args: str) -> None:
    """Show current model, provider, session stats, conversation."""
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

    # Show last few conversation turns
    if turns > 0:
        console.print(f"[bold]Recent ({min(turns, 5)} of {turns} turns):[/]")
        for m in mem.messages[-5:]:
            label = "[cyan]You[/]" if m.role == "user" else "[green]Agent[/]"
            text = m.content if len(m.content) <= 120 else m.content[:117] + "..."
            console.print(f"  {label}: {text}")
    else:
        console.print("[dim]No conversation yet.[/]")


# ── /model — switch LLM provider ──────────────────────────────────


def _cmd_model(args: str) -> None:
    """List or switch LLM provider."""
    name = args.strip().lower()

    if not name:
        current = _current_provider()
        console.print(f"Current: [cyan]{current}[/] → {_current_model()}")
        console.print()
        console.print("Available:")
        for p in _PROVIDERS:
            marker = " [bold green]← current[/]" if p == current else ""
            console.print(f"  {p}{marker}")
        console.print()
        console.print("[dim]Usage: /model <name>   (e.g. /model deepseek)[/]")
        return

    if name not in _PROVIDERS:
        console.print(f"[red]Unknown provider: {name}[/]")
        console.print(f"Available: {', '.join(_PROVIDERS)}")
        return

    os.environ["TAGENT_LLM_PROVIDER"] = name
    console.print(f"[green]Switched to {name}[/] → {_current_model()}")
    console.print("[dim]Note: router will use this provider for subsequent requests.[/]")


# ── /context — conversation history ───────────────────────────────


def _cmd_context(args: str) -> None:
    mem = _get_memory()
    if not mem.messages:
        console.print("[dim]No conversation history.[/]")
        return
    console.print(f"[bold]Conversation ({len(mem.messages)} turns):[/]")
    for m in mem.messages:
        label = "[cyan]You[/]" if m.role == "user" else "[green]Agent[/]"
        text = m.content if len(m.content) <= 120 else m.content[:117] + "..."
        console.print(f"  {label}: {text}")


# ── /clear ────────────────────────────────────────────────────────


def _cmd_clear(args: str) -> None:
    _get_memory().clear()
    console.print("[dim]Conversation cleared.[/]")


# ── Persistence ───────────────────────────────────────────────────


def _save_session() -> None:
    mem = _get_memory()
    if mem.messages:
        mem.dump(_SESSION_FILE)


# ── REPL Entry ────────────────────────────────────────────────────


def start() -> None:
    global _start_time
    _start_time = time.time()

    _print_banner()

    mem = _get_memory()
    if mem.messages:
        console.print(f"[dim]Resumed {mem.session_id} ({len(mem.messages)} turns)[/]\n")

    while True:
        try:
            user_input = console.input("[bold cyan]> [/]").strip()
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
