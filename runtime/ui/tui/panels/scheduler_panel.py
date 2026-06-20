"""Task Scheduler panel — cron jobs, countdown, manual trigger."""

from textual.widgets import Static
from textual.containers import Vertical


class SchedulerPanel(Vertical):
    """Display scheduled tasks with cron examples and status."""

    def compose(self):
        yield Static("Task Scheduler", classes="title")
        yield Static("")
        try:
            from runtime.scheduler.nl_cron import parse, examples
            # Active cron jobs
            yield Static("  Active Jobs:")
            yield Static("  (none scheduled — use !cron add)")
            yield Static("")
            yield Static("  Cron Parser Examples:")
            for ex in examples()[:6]:
                yield Static(f"    {ex}")
            yield Static("")
            yield Static("  Quick Add:")
            yield Static('    !cron add "every morning" --task http-check')
            yield Static('    !cron add "every 30 min" --task ping-check')
            yield Static("")
            yield Static("  Manage: !cron list | !cron remove <id> | !cron health")
        except Exception as e:
            yield Static(f"  Scheduler unavailable: {e}")
