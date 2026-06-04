"""Interactive REPL — Claude Code / Hermes Agent style terminal session.

Bare `tagent` (no subcommand) enters this interactive loop:
  - Bare text → LLM routing → agent orchestration → streaming output
  - /command  → slash command dispatch
  - Ctrl+C    → interrupt current operation
  - Ctrl+D    → quit
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

from runtime.cli._shared import console
from runtime.cli.slash_commands import COMMAND_REGISTRY, resolve as resolve_command

# Banner — same sheep as main.py
_SHEEP = r"""
    ✧  ▗▛ 🐏 ▜▖  ✧
         ▀▀▀▀▀
         ▐▌ ▐▌

  ૮₍˶ᵔ ᗜ ᵔ˶₎ა  Test-Agent v{version}
  AI Router · {experts} Experts · {skills} Skills
  Type /help for commands, or just describe your test task."""


def _count_md_files(dirname: str) -> int:
    d = _Path(__file__).resolve().parents[2] / dirname
    if not d.is_dir():
        return 0
    return len([f for f in d.glob("*.md") if f.name.upper() != "README.MD"])


def _print_banner() -> None:
    import runtime
    n_experts = _count_md_files("agents")
    n_skills = _count_md_files("skills")
    console.print(_SHEEP.format(
        version=runtime.__version__,
        experts=n_experts,
        skills=n_skills,
    ))
    console.print()


def _handle_natural_language(text: str) -> None:
    """Route free-form text through LLM → orchestrator."""
    if not text.strip():
        return

    console.print(f"[dim]Routing: \"{text[:80]}{'...' if len(text) > 80 else ''}\"[/]")

    try:
        import sys as _sys
        _sys.argv = ["tagent", "run", text]
        from runtime.cli.commands.run import run
        run()
    except SystemExit:
        pass  # typer.Exit caught
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/]")


def _handle_slash(text: str) -> None:
    """Dispatch /command."""
    parts = text.lstrip("/").strip().split(maxsplit=1)
    name = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    cmd = resolve_command(name)
    if cmd is None:
        console.print(f"[red]Unknown command: /{name}[/]")
        console.print("[dim]Type /help to see available commands.[/]")
        return

    try:
        cmd.handler(args)
    except SystemExit:
        pass
    except Exception as exc:
        console.print(f"[red]Command /{name} failed: {exc}[/]")


def start() -> None:
    """Enter interactive REPL loop."""
    _print_banner()

    while True:
        try:
            user_input = console.input("[bold cyan]> [/]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/]")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            _handle_slash(user_input)
        else:
            _handle_natural_language(user_input)
