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
        from runtime.cli.interactive import start
        start()
        raise typer.Exit(0)


# Register command modules
from runtime.cli.commands.bootstrap import register as _reg_bootstrap  # noqa: E402
from runtime.cli.commands.catalog import register as _reg_catalog  # noqa: E402
from runtime.cli.commands.demo import register as _reg_demo  # noqa: E402
from runtime.cli.commands.doctor import register as _reg_doctor  # noqa: E402
from runtime.cli.commands.export import register as _reg_export  # noqa: E402
from runtime.cli.commands.init import register as _reg_init  # noqa: E402
from runtime.cli.commands.market import register as _reg_market  # noqa: E402
from runtime.cli.commands.readiness import register as _reg_readiness  # noqa: E402
from runtime.cli.commands.run import register_run as _reg_run  # noqa: E402
from runtime.cli.commands.selftest import register as _reg_selftest  # noqa: E402
from runtime.cli.commands.gateway import register as _reg_gateway  # noqa: E402
from runtime.cli.commands.test_coordinator import register as _reg_test_coordinator  # noqa: E402
# P3 #19 daemon mode (inline — simple enough)
@app.command(name="serve", help="Start 7x24 daemon (FastAPI + scheduler)")
def _serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host"),
    port: int = typer.Option(8800, "--port", "-p", help="Bind port"),
):
    from runtime.cli.commands.serve import serve
    serve(host, port)

_reg_bootstrap(app)
_reg_catalog(app)
_reg_demo(app)
_reg_doctor(app)
_reg_export(app)
_reg_init(app)
_reg_market(app)
_reg_readiness(app)
_reg_run(app)
_reg_selftest(app)
_reg_gateway(app)
_reg_test_coordinator(app)

if __name__ == "__main__":
    app()
