"""Typer CLI: `tagent run|status|report|catalog|doctor`."""

from __future__ import annotations

import typer

import runtime
from runtime.cli._shared import console
from runtime.cli.config import config_app

app = typer.Typer(add_completion=False, help="Test-Agent Runtime CLI")
app.add_typer(config_app, name="config")


@app.callback(invoke_without_command=True)
def _version_callback(
    version: bool = typer.Option(False, "--version", help="Show version and exit"),
):
    if version:
        console.print(f"Test-Agent Runtime v{runtime.__version__}")
        raise typer.Exit(0)


# Register command modules
from runtime.cli.commands.catalog import register as _reg_catalog
from runtime.cli.commands.demo import register as _reg_demo
from runtime.cli.commands.doctor import register as _reg_doctor
from runtime.cli.commands.export import register as _reg_export
from runtime.cli.commands.init import register as _reg_init
from runtime.cli.commands.market import register as _reg_market
from runtime.cli.commands.readiness import register as _reg_readiness
from runtime.cli.commands.run import register_run as _reg_run
from runtime.cli.commands.selftest import register as _reg_selftest

_reg_catalog(app)
_reg_demo(app)
_reg_doctor(app)
_reg_export(app)
_reg_init(app)
_reg_market(app)
_reg_readiness(app)
_reg_run(app)
_reg_selftest(app)

if __name__ == "__main__":
    app()
