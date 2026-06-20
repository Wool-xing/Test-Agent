"""Help panel — interactive tutorial, command reference, shortcuts."""

from textual.widgets import Static
from textual.containers import Vertical


class HelpPanel(Vertical):
    """Interactive help and getting started guide."""

    def compose(self):
        yield Static("Help & Getting Started", classes="title")
        yield Static("")

        yield Static("[bold]Quick Start[/]")
        yield Static("  1. tagent init --preset minimal    Create project")
        yield Static("  2. tagent run \"check example.com\"    Run first test")
        yield Static("  3. tagent chat                      Chat mode (REPL)")
        yield Static("  4. tagent report                    View results")
        yield Static("")

        yield Static("[bold]Keyboard Shortcuts[/]")
        yield Static("  F1  Dashboard     F4  Logs")
        yield Static("  F2  Skills        F5  Config")
        yield Static("  F3  Status        F6  Help")
        yield Static("  F7  Scheduler     Ctrl+Q  Quit")
        yield Static("")

        yield Static("[bold]REPL Commands[/]")
        yield Static("  !help     This help      !status   System status")
        yield Static("  !doctor   Health check   !model    Switch LLM")
        yield Static("  !cron     Schedule task  !history  Run history")
        yield Static("  !cost     Token usage    !export   Export results")
        yield Static("")

        yield Static("[bold]Built-in Skills[/]")
        try:
            from runtime.orchestrator.skills import SKILL_RUNNERS
            basic = [s for s in sorted(SKILL_RUNNERS.keys()) if any(
                x in s for x in ["ping", "http", "file", "process", "timeout"]
            )]
            for s in basic:
                yield Static(f"  · {s}")
        except Exception:
            yield Static("  (skills catalog unavailable)")
        yield Static("")
        yield Static("[dim]Docs: docs/getting-started/ | GitHub: Wool-xing/Test-Agent[/]")
