<<<<<<< HEAD
"""Dashboard panel — live overview of test system."""
=======
"""Dashboard panel — overview of recent test runs."""
>>>>>>> 6814523518fcfd06fd81ea6a0fc72be97fd00b08

from textual.widgets import Static
from textual.containers import Vertical


class DashboardPanel(Vertical):
<<<<<<< HEAD
    """Main dashboard showing test run overview with live data."""

    def compose(self):
        yield Static("Test-Agent V2.0.0", classes="title")
        yield Static("")

        # Agent catalog stats
        try:
            from runtime.registry.registry import get_catalog
            cat = get_catalog()
            yield Static(f"  Experts: {len(cat.experts)} registered")
            yield Static(f"  Skills:  {len(cat.skills)} registered")
        except Exception:
            yield Static("  Catalog: unavailable")

        # LLM provider
        try:
            from runtime.config.settings import get_settings
            s = get_settings()
            yield Static(f"  Provider: {s.llm_provider}")
        except Exception:
            yield Static("  Provider: unknown")

        # Last run info
        try:
            import json
            session_file = __import__("runtime.config.settings", fromlist=["get_settings"])\
                .get_settings().gateway_dir / "active_session.json"
            if session_file.exists():
                data = json.loads(session_file.read_text(encoding="utf-8"))
                yield Static("")
                yield Static("Last Session:")
                yield Static(f"  Started: {data.get('started_at', 'unknown')}")
                yield Static(f"  Provider: {data.get('provider', 'unknown')}")
                yield Static(f"  Model: {data.get('model', 'unknown')}")
        except Exception:
            pass
=======
    """Main dashboard showing test run overview."""

    def compose(self):
        yield Static("Test-Agent V2.0.0 Dashboard", classes="title")
        yield Static("Recent test runs and statistics appear here.")
>>>>>>> 6814523518fcfd06fd81ea6a0fc72be97fd00b08
