"""Task Scheduler panel — cron jobs, next run, history."""

from textual.widgets import Static
from textual.containers import Vertical


class SchedulerPanel(Vertical):
    """Display scheduled tasks and cron jobs."""

    def compose(self):
        yield Static("Task Scheduler", classes="title")
        yield Static("")
        try:
            from runtime.scheduler.nl_cron import parse, examples
            yield Static("  Cron Parser: Ready")
            yield Static("")
            yield Static("  Natural Language Examples:")
            for ex in examples():
                yield Static(f"    {ex}")
            yield Static("")
            yield Static("  Usage: tagent !cron add \"every morning\" --task http-check")
        except Exception as e:
            yield Static(f"  Scheduler unavailable: {e}")
