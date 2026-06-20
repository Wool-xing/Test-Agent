"""Dashboard panel — overview of recent test runs."""

from textual.widgets import Static
from textual.containers import Vertical


class DashboardPanel(Vertical):
    """Main dashboard showing test run overview."""

    def compose(self):
        yield Static("Test-Agent V2.0.0 Dashboard", classes="title")
        yield Static("Recent test runs and statistics appear here.")
