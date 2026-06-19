"""Typer CLI: `tagent run|plan|catalog|doctor`."""

from __future__ import annotations

import sys as _sys

import typer

import runtime
from runtime.cli._shared import console, set_no_color
from runtime.cli.config import config_app

app = typer.Typer(add_completion=True, help="Test-Agent Runtime CLI")
app.add_typer(config_app, name="config")


@app.callback(invoke_without_command=True)
def _version_callback(
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable colored output"),
    debug: bool = typer.Option(False, "--debug", help="Enable DEBUG log level"),
):
    if no_color:
        set_no_color()
    if debug:
        import os as _os
        _os.environ["TAGENT_LOG_LEVEL"] = "DEBUG"
    if version:
        console.print(f"Test-Agent Runtime v{runtime.__version__}")
        raise typer.Exit(0)
    # bare `tagent` (no subcommand, no --version) → interactive REPL
    if len(_sys.argv) == 1:
        from runtime.config.settings import get_settings
        issues = get_settings().validate_startup()
        critical = [i for i in issues if i["level"] == "error"]
        if critical:
            for i in critical:
                console.print(f"[red]FATAL:[/] {i['message']}")
            raise typer.Exit(1)
        from runtime.cli.interactive import start
        start()
        raise typer.Exit(0)


# Auto-discover CLI commands from slash command registry.
# Commands with cli_module set are exposed as typer CLI commands.
from runtime.cli.slash_commands import COMMAND_REGISTRY as _REG  # noqa: E402

_seen: set[str] = set()
for _cmd in _REG:
    if not _cmd.cli_module:
        continue
    if _cmd.cli_module in _seen:
        continue
    _seen.add(_cmd.cli_module)
    _mod = __import__(f"runtime.cli.commands.{_cmd.cli_module}", fromlist=["register"])  # noqa: E402
    _mod.register(app)

# Manual registrations — modules that register multiple commands or sub-apps
# Manual registrations — CLI-only or name-collision commands
import runtime.cli.commands.bootstrap as _reg_bootstrap  # noqa: E402
import runtime.cli.commands.export as _reg_export  # noqa: E402
_reg_bootstrap.register(app)
_reg_export.register(app)
import runtime.cli.commands.impact as _reg_impact  # noqa: E402
import runtime.cli.commands.market as _reg_market  # noqa: E402
_reg_impact.register(app)
_reg_market.register(app)
import runtime.cli.commands.plugin as _reg_plugin  # noqa: E402
_reg_plugin.register(app)

# P3 #19 daemon mode (inline — simple enough)
@app.command(name="serve", help="Start 7x24 daemon (FastAPI + scheduler)")
def _serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host"),
    port: int = typer.Option(8800, "--port", "-p", help="Bind port"),
):
    from runtime.cli.commands.serve import serve
    serve(host, port)

if __name__ == "__main__":
    app()
