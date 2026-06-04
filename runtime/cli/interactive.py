"""Interactive REPL — Claude Code / Hermes Agent style terminal session.

Bare `tagent` (no subcommand) enters this interactive loop:
  - Natural language → LLM routing → agent orchestration → streaming output
  - /command  → slash command dispatch (tab-completion via Rich)
  - Ctrl+C    → interrupt current operation (REPL stays alive)
  - Ctrl+D    → quit
"""

from __future__ import annotations

from pathlib import Path as _Path

from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from runtime.cli._shared import console
from runtime.cli.slash_commands import COMMAND_REGISTRY, resolve as resolve_command

_SHEEP = r"""
    ✧  ▗▛ 🐏 ▜▖  ✧
         ▀▀▀▀▀
         ▐▌ ▐▌

  ૮₍˶ᵔ ᗜ ᵔ˶₎ა  Test-Agent v{version}
  AI Router · {experts} Experts · {skills} Skills
  Type /help for commands, or describe your test task."""


def _count_md_files(dirname: str) -> int:
    d = _Path(__file__).resolve().parents[2] / dirname
    if not d.is_dir():
        return 0
    return len([f for f in d.glob("*.md") if f.name.upper() != "README.MD"])


def _print_banner() -> None:
    import runtime

    n_experts = _count_md_files("agents")
    n_skills = _count_md_files("skills")
    console.print(
        _SHEEP.format(version=runtime.__version__, experts=n_experts, skills=n_skills)
    )
    console.print()


def _print_help() -> None:
    from rich.table import Table

    table = Table(title="Slash Commands", show_header=True, header_style="bold")
    table.add_column("Command", style="cyan")
    table.add_column("Args", style="dim")
    table.add_column("Description")

    for cmd in sorted(COMMAND_REGISTRY, key=lambda c: c.name):
        table.add_row(f"/{cmd.name}", cmd.args_hint, cmd.description)

    console.print(table)
    console.print("[dim]Bare text (no /) → LLM routing → agent execution[/]")


def _handle_natural_language(text: str) -> None:
    """Route free-form text through LLM → orchestrator with spinner."""
    if not text.strip():
        return

    summary = text[:80] + ("..." if len(text) > 80 else "")
    console.print(f"[dim]Analyzing: \"{summary}\"[/]")

    try:
        import sys as _sys

        _sys.argv = ["tagent", "run", text]

        with console.status(
            "[bold green]Routing via LLM...", spinner="dots"
        ) as status:
            from runtime.cli.commands.run import run as _run

            _run()
    except SystemExit:
        pass
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/]")
    except Exception as exc:
        console.print(f"[red]Error: {exc}[/]")


def _handle_slash(text: str) -> None:
    """Dispatch /command."""
    parts = text.lstrip("/").strip().split(maxsplit=1)
    name = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if name in ("help", "h", "?"):
        _print_help()
        return
    if name in ("quit", "q", "exit"):
        console.print("[dim]Goodbye.[/]")
        raise SystemExit(0)

    cmd = resolve_command(name)
    if cmd is None:
        console.print(f"[red]Unknown command: /{name}[/]")
        console.print("[dim]Type /help to see available commands.[/]")
        return

    try:
        cmd.handler(args)
    except SystemExit:
        pass
    except KeyboardInterrupt:
        console.print("\n[yellow]Command cancelled.[/]")
    except Exception as exc:
        console.print(f"[red]Command /{name} failed: {exc}[/]")


def start() -> None:
    """Enter interactive REPL loop. Stays alive on errors; Ctrl+D quits."""
    _print_banner()

    while True:
        try:
            user_input = console.input("[bold cyan]> [/]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/]")
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
            console.print(f"[red]Unexpected error: {exc}[/]")
            console.print("[dim]REPL continuing — type /help for commands.[/]")
