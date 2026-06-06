"""tagent gateway — IM platform status and management.

Use: tagent gateway status   — show configured platforms
     tagent gateway start    — start messaging gateway (same as tagent serve)
"""

from __future__ import annotations

import os

import typer
from rich.table import Table

from runtime.cli._shared import console

PLATFORMS = [
    ("Telegram", "TELEGRAM_BOT_TOKEN"),
    ("Discord", "DISCORD_WEBHOOK_URL"),
    ("Slack", "SLACK_WEBHOOK_URL"),
    ("飞书", "FEISHU_WEBHOOK_URL"),
    ("企微", "WECHAT_WEBHOOK_URL"),
    ("钉钉", "DINGTALK_WEBHOOK_URL"),
    ("QQ Bot", "QQBOT_APP_ID"),
    ("Email", "SMTP_HOST"),
    ("Webhook", "GENERIC_WEBHOOK_URL"),
]


def register(parent: typer.Typer) -> None:
    """Register gateway subcommands on the parent Typer app."""
    gw = typer.Typer(help="IM messaging gateway management", no_args_is_help=True)

    @gw.command(name="status", help="Show configured IM platforms")
    def _status():
        table = Table(title="Gateway Platforms")
        table.add_column("Platform")
        table.add_column("Status")
        table.add_column("Env Var")

        active = 0
        for name, env_var in PLATFORMS:
            configured = bool(os.getenv(env_var))
            if configured:
                active += 1
            status = "[green]✓ configured[/]" if configured else "[dim]—[/]"
            table.add_row(name, status, env_var)

        console.print(table)
        console.print(f"\n{active}/{len(PLATFORMS)} configured")
        if active == 0:
            console.print("[dim]Hint: set env vars then run [cyan]tagent serve[/] to start.[/]")

    @gw.command(name="start", help="Start gateway daemon (FastAPI + webhooks)")
    def _start(
        host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host"),
        port: int = typer.Option(8800, "--port", "-p", help="Bind port"),
    ):
        console.print("[bold]Starting Test-Agent Gateway...[/]")
        console.print(f"[dim]→ http://{host}:{port}[/]")
        console.print("[dim]Webhooks: /webhooks/telegram /webhooks/wechat /webhooks/dingtalk /webhooks/qqbot[/]")
        _status()
        from runtime.cli.commands.serve import serve
        serve(host, port)

    parent.add_typer(gw, name="gateway")
