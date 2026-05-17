"""init: generate .env + tagent.yml + STARTUP.md."""

from __future__ import annotations

from pathlib import Path

import typer

from runtime.cli._shared import console


def register(app: typer.Typer) -> None:
    @app.command()
    def init(
        test_type: str = typer.Option("", "--test-type", help="web/api/mobile/desktop/iot/car/ai_model/security"),
        platform: str = typer.Option("", "--platform", help="linux/windows/mac/android/ios/embedded"),
        llm: str = typer.Option("", "--llm", help="claude/openai/qwen/deepseek/ollama"),
        bug_tracker: str = typer.Option("", "--bug-tracker", help="zentao/jira/github/gitlab/linear/webhook"),
        notifier: str = typer.Option("", "--notifier", help="comma-separated: wechat,feishu,dingtalk,slack,email,teams"),
        preset: str = typer.Option("", "--preset", help="minimal/saas-web/mobile-android/security-pentest"),
        out: str = typer.Option("workspace", "--out", help="output dir"),
        overwrite: bool = typer.Option(False, "--overwrite", help="allow overwriting existing files"),
    ):
        """Generate .env + tagent.yml + STARTUP.md in 5 minutes."""
        from runtime.init.matrix import load_matrix
        from runtime.init.renderer import render_all
        from runtime.init.wizard import from_args, from_preset, run_wizard

        matrix = load_matrix()

        if preset:
            answers = from_preset(preset, matrix=matrix)
            console.print(f"[green]preset[/] {preset}: {answers.test_type}/{answers.platform}/{answers.llm_provider}/{answers.bug_tracker} + {answers.notifiers}")
        elif test_type and platform and llm:
            notifiers = [n.strip() for n in notifier.split(",") if n.strip()] or ["wechat"]
            answers = from_args(test_type=test_type, platform=platform, llm_provider=llm,
                                bug_tracker=bug_tracker or "zentao", notifiers=notifiers, matrix=matrix)
            console.print(f"[green]args[/] {answers.test_type}/{answers.platform}/{answers.llm_provider}/{answers.bug_tracker} + {answers.notifiers}")
        else:
            answers = run_wizard(matrix=matrix)

        try:
            res = render_all(answers, Path(out), matrix=matrix, overwrite=overwrite)
        except FileExistsError as e:
            console.print(f"[red]{e}[/]")
            raise typer.Exit(2)

        console.print("\n[bold green]✓ config generated[/]")
        console.print(f"  .env       → {res.env_path}")
        console.print(f"  tagent.yml → {res.yml_path}")
        console.print(f"  STARTUP.md → {res.startup_path}")
        console.print(f"\n[bold]Next[/]: `cat {res.startup_path}` for startup guide")
