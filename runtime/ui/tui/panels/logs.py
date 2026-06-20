"""Log Viewer panel — real-time log stream with filtering."""

from textual.widgets import Static
from textual.containers import Vertical


class LogViewerPanel(Vertical):
    """View and filter runtime logs."""

    def compose(self):
        yield Static("Log Viewer", classes="title")
        yield Static("Log stream display — coming soon.")
