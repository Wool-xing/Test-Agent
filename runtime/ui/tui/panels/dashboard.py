"""Dashboard panel — live overview of test system."""

from textual.widgets import Static
from textual.containers import Vertical


class DashboardPanel(Vertical):
    """Main dashboard showing test run overview with live data."""

    def compose(self):
        yield Static("Test-Agent V2.0.0", classes="title")
        yield Static("")
        try:
            from runtime.registry.registry import get_catalog
            cat = get_catalog()
            yield Static(f"  Experts: {len(cat.experts)} registered")
            yield Static(f"  Skills:  {len(cat.skills)} registered")
        except Exception:
            yield Static("  Catalog: unavailable")
        try:
            from runtime.config.settings import get_settings
            s = get_settings()
            yield Static(f"  Provider: {s.llm_provider}")
        except Exception:
            yield Static("  Provider: unknown")
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
