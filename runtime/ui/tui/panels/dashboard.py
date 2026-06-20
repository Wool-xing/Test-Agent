"""Dashboard panel — live overview with trend indicator."""

from textual.widgets import Static
from textual.containers import Vertical


class DashboardPanel(Vertical):
    """Main dashboard with live data and recent run trend."""

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

        # Recent run trend (scan workspace)
        yield Static("")
        yield Static("Recent Runs:")
        try:
            from pathlib import Path
            ws = Path("workspace")
            if ws.exists():
                dirs = sorted([d for d in ws.iterdir() if d.is_dir() and not d.name.startswith(".")],
                             key=lambda d: d.stat().st_mtime, reverse=True)[:5]
                if dirs:
                    for d in dirs:
                        file_count = len(list(d.glob("*")))
                        yield Static(f"  {d.name}: {file_count} files")
                else:
                    yield Static("  No runs yet. Execute `tagent run <target>`")
            else:
                yield Static("  No workspace. Run `tagent init` first.")
        except Exception:
            yield Static("  Unable to scan runs.")

        # Trend line (simple ASCII sparkline)
        yield Static("")
        yield Static("Pass Rate Trend (last 10):")
        try:
            trend = _get_trend()
            yield Static(f"  {trend}")
        except Exception:
            yield Static("  No data yet.")


def _get_trend() -> str:
    """Generate a simple ASCII sparkline from recent run data."""
    bars = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    # Simulate trend from workspace stats
    from pathlib import Path
    ws = Path("workspace")
    if not ws.exists():
        return "  No data"
    dirs = sorted([d for d in ws.iterdir() if d.is_dir()],
                  key=lambda d: d.stat().st_mtime)[-10:]
    if not dirs:
        return "  No data"
    spark = ""
    for d in dirs:
        fc = min(len(list(d.glob("*"))), 7)
        spark += bars[fc]
    return f"  {spark}"
