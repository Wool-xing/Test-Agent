"""Help panel — interactive tutorial walkthrough."""

from textual.widgets import Static
from textual.containers import Vertical


class HelpPanel(Vertical):
    """Interactive help and getting started walkthrough."""

    def compose(self):
        yield Static("Help & Walkthrough", classes="title")
        yield Static("")

        yield Static("[bold]Quick Start (5 minutes)[/]")
        yield Static("  1. tagent init --preset minimal")
        yield Static("  2. tagent run 'check example.com'")
        yield Static("  3. tagent report")
        yield Static("")

        yield Static("[bold]Keyboard[/]")
        yield Static("  F1 Dashboard    F6 Execute")
        yield Static("  F2 Skills       F7 Scheduler")
        yield Static("  F3 Status       F8 Help")
        yield Static("  F4 Logs         F9 Skins")
        yield Static("  F5 Config       F10 Theme")
        yield Static("  Ctrl+Q Quit")

        yield Static("")
        yield Static("[bold]REPL Commands[/]")
        yield Static("  /help   /status   /doctor   /model")
        yield Static("  /cron   /cost     /history  /export")
        yield Static("  /run    /report   /memory   /sessions")

        yield Static("")
        yield Static("[bold]Built-in Skills[/]")
        try:
            from runtime.orchestrator.skills import SKILL_RUNNERS
            skills = sorted(SKILL_RUNNERS.keys())
            basic = [s for s in skills if any(x in s for x in ['ping','http','file','process','timeout'])]
            yield Static(f"  Basic ({len(basic)}): {', '.join(basic)}")
            yield Static(f"  Total: {len(skills)} skills available")
        except Exception:
            pass

        yield Static("")
        yield Static("[dim]Docs: docs/getting-started/[/]")
        yield Static("[dim]GitHub: Wool-xing/Test-Agent[/]")
