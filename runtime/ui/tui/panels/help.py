"""Help panel — tutorial, command reference, shortcuts."""

from textual.widgets import Static
from textual.containers import Vertical


class HelpPanel(Vertical):
    """Interactive help and tutorial."""

    def compose(self):
        yield Static("Help & Tutorial", classes="title")
        yield Static("  F1 — Dashboard")
        yield Static("  F2 — Skill Browser")
        yield Static("  F3 — Agent Status")
        yield Static("  F4 — Log Viewer")
        yield Static("  F5 — Configuration")
        yield Static("  F6 — Help")
        yield Static("  Ctrl+Q — Quit")
