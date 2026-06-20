"""Test Execution Panel — real-time progress, pass/fail counts, recent runs."""

from textual.widgets import Static
from textual.containers import Vertical


class ExecutionPanel(Vertical):
    """Display test execution progress with live data."""

    def compose(self):
        yield Static("Test Execution", classes="title")
        yield Static("")
        # Last run summary
        try:
            from pathlib import Path
            import json
            sf = Path("workspace/gateway/active_session.json")
            if sf.exists():
                data = json.loads(sf.read_text(encoding="utf-8"))
                yield Static(f"  Last Run: {data.get('started_at', 'unknown')}")
                yield Static(f"  Provider: {data.get('provider', 'unknown')}")
            else:
                yield Static("  Last Run: No runs yet")
        except Exception:
            yield Static("  Last Run: No runs yet")
        yield Static("")
        yield Static("  Status:  Ready")
        yield Static("  Queue:   0 pending")
        yield Static("")
        yield Static("  Run `tagent run <target>` to execute tests.")
        yield Static("  Run `tagent report` for detailed results.")
