"""Test Execution Panel — real-time progress, pass/fail counts."""

from textual.widgets import Static
from textual.containers import Vertical


class ExecutionPanel(Vertical):
    """Display real-time test execution progress."""

    def compose(self):
        yield Static("Test Execution", classes="title")
        yield Static("")
        yield Static("  Status:  Idle")
        yield Static("  Passed:  0")
        yield Static("  Failed:  0")
        yield Static("  Skipped: 0")
        yield Static("  Running: 0")
        yield Static("")
        yield Static("  Last run: No runs yet")
        yield Static("")
        yield Static("  Run `tagent run <target>` to execute tests.")
