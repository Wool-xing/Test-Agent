"""Slash command registry — single source of truth.

Single registry drives CLI autocomplete, help output, command dispatch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class CommandDef:
    name: str
    description: str
    aliases: list[str] = field(default_factory=list)
    args_hint: str = ""
    handler: Callable | None = None


COMMAND_REGISTRY: list[CommandDef] = []


def register(name: str, description: str, aliases: list[str] | None = None, args_hint: str = ""):
    """Decorator: register a slash command handler."""

    def decorator(fn):
        COMMAND_REGISTRY.append(
            CommandDef(
                name=name,
                description=description,
                aliases=aliases or [],
                args_hint=args_hint,
                handler=fn,
            )
        )
        return fn

    return decorator


def resolve(name: str) -> CommandDef | None:
    """Look up command by name or alias."""
    name = name.lstrip("/").strip().lower()
    for cmd in COMMAND_REGISTRY:
        if cmd.name == name or name in cmd.aliases:
            return cmd
    return None


def all_commands() -> list[CommandDef]:
    return list(COMMAND_REGISTRY)


# ── Short, memorable commands ────────────────────────────────────


@register("help", "Show help", aliases=["h", "?"])
def _cmd_help(args: str) -> None:
    from runtime.cli._shared import console
    from rich.table import Table

    table = Table(title="Commands", show_header=True)
    table.add_column("Command", style="cyan")
    table.add_column("Args", style="dim")
    table.add_column("Description")

    for cmd in sorted(COMMAND_REGISTRY, key=lambda c: c.name):
        aliases_str = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
        table.add_row(f"/{cmd.name}{aliases_str}", cmd.args_hint, cmd.description)

    console.print(table)
    console.print("[dim]Bare text (no /) → LLM routing → agent execution[/]")


@register("quit", "Exit", aliases=["q", "exit"])
def _cmd_quit(args: str) -> None:
    from runtime.cli._shared import console
    console.print("[dim]Goodbye.[/]")
    raise SystemExit(0)


@register("test", "Full test pipeline (11-step)", aliases=["tc"], args_hint="<target>")
def _cmd_test(args: str) -> None:
    if not args.strip():
        from runtime.cli._shared import console
        console.print("[red]Usage: /test <path|URL|text>[/]")
        return
    from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
    TestCoordinatorPipeline().run(args.strip())


@register("run", "Plan + execute (quick)", aliases=["r"], args_hint="<target>")
def _cmd_run(args: str) -> None:
    if not args.strip():
        from runtime.cli._shared import console
        console.print("[red]Usage: /run <path|URL|text>[/]")
        return
    import sys as _sys
    _sys.argv = ["tagent", "run"] + args.split()
    from runtime.cli.commands.run import run
    run()


@register("plan", "Plan only", aliases=["p"], args_hint="<target>")
def _cmd_plan(args: str) -> None:
    if not args.strip():
        from runtime.cli._shared import console
        console.print("[red]Usage: /plan <path|URL|text>[/]")
        return
    import sys as _sys
    _sys.argv = ["tagent", "plan"] + args.split()
    from runtime.cli.commands.run import plan
    plan()


@register("doctor", "Health check", aliases=["health"], args_hint="[--agents] [--probe]")
def _cmd_doctor(args: str) -> None:
    import sys as _sys
    _sys.argv = ["tagent", "doctor"] + (args.split() if args.strip() else [])
    from runtime.cli.commands.doctor import doctor
    doctor()


@register("ls", "List experts + skills", aliases=["list", "catalog"])
def _cmd_ls(args: str) -> None:
    import sys as _sys
    _sys.argv = ["tagent", "catalog"]
    from runtime.cli.commands.catalog import catalog
    catalog()


@register("setup", "Generate config", aliases=["init"], args_hint="[--preset ...]")
def _cmd_setup(args: str) -> None:
    import sys as _sys
    _sys.argv = ["tagent", "init"] + (args.split() if args.strip() else [])
    from runtime.cli.commands.init import init_project
    init_project()


@register("ready", "Release readiness", aliases=["readiness"])
def _cmd_ready(args: str) -> None:
    import sys as _sys
    _sys.argv = ["tagent", "readiness"] + (args.split() if args.strip() else [])
    from runtime.cli.commands.readiness import readiness
    readiness()


@register("check", "Framework self-test", aliases=["selftest"], args_hint="[--e2e] [--strict]")
def _cmd_check(args: str) -> None:
    import sys as _sys
    _sys.argv = ["tagent", "selftest"] + (args.split() if args.strip() else [])
    from runtime.cli.commands.selftest import selftest
    selftest()


@register("demo", "Quick demo", args_hint="[--real-llm]")
def _cmd_demo(args: str) -> None:
    import sys as _sys
    _sys.argv = ["tagent", "demo"] + (args.split() if args.strip() else [])
    from runtime.cli.commands.demo import demo
    demo()
