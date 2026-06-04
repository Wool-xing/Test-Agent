"""Typer CLI: `tagent run|plan|catalog|doctor`."""

from __future__ import annotations

import sys as _sys

import typer

import runtime
from runtime.cli._shared import console, set_no_color
from runtime.cli.config import config_app

app = typer.Typer(add_completion=True, help="Test-Agent Runtime CLI")
app.add_typer(config_app, name="config")

# 🐏 品牌 Logo — Claude Code 风格 · 🐏 + 块字符 + 颜文字 = 萌系
#   ✧  ▗▛ 🐏 ▜▖  ✧  = 闪闪 + 小耳朵 + 羊羊 + 小耳朵 + 闪闪
#        ▀▀▀▀▀       = 软fufu棉花身体
#        ▐▌ ▐▌       = 小蹄子
_SHEEP = r"""
    ✧  ▗▛ 🐏 ▜▖  ✧
         ▀▀▀▀▀
         ▐▌ ▐▌

  ૮₍˶ᵔ ᗜ ᵔ˶₎ა  Test-Agent Runtime v{version}
  AI Router · {experts} Experts · {skills} Skills"""


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
    # bare `tagent` (no subcommand, no --version) → 🐏 品牌 banner + 命令列表
    if len(_sys.argv) == 1:
        _n_experts = _count_md_files("agents")
        _n_skills = _count_md_files("skills")
        console.print(_SHEEP.format(
            version=runtime.__version__,
            experts=_n_experts,
            skills=_n_skills,
        ))
        console.print()
        console.print("[bold]常用命令:[/]")
        console.print("  tagent run <target>        一键执行测试 (PRD / URL / 文本)")
        console.print("  tagent plan <target>       仅规划路由, 不执行")
        console.print("  tagent catalog             列出所有专家 + 技能")
        console.print("  tagent doctor              环境自检")
        console.print()
        console.print("[dim]tagent --help  查看完整命令列表[/]")
        console.print()
        raise typer.Exit(0)


def _count_md_files(dirname: str) -> int:
    """Count *.md files (excluding README) in a project subdirectory."""
    from pathlib import Path as _Path
    d = _Path(__file__).resolve().parents[2] / dirname
    if not d.is_dir():
        return 0
    return len([f for f in d.glob("*.md") if f.name.upper() != "README.MD"])


def _count_py_modules(dirname: str) -> int:
    """Count non-__init__ .py files in utils/."""
    from pathlib import Path as _Path
    d = _Path(__file__).resolve().parents[2] / dirname
    if not d.is_dir():
        return 0
    return len([f for f in d.rglob("*.py") if f.name != "__init__.py"])


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

if __name__ == "__main__":
    app()
