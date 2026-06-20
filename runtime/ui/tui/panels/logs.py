"""Log Viewer panel — real-time log stream with filtering."""

from textual.widgets import Static, RichLog
from textual.containers import Vertical


class LogViewerPanel(Vertical):
    """View and filter runtime logs with live tail."""

    def compose(self):
        yield Static("Log Viewer — recent entries", classes="title")
        log = RichLog(highlight=True, markup=True, max_lines=200)
        try:
            from runtime.config.settings import get_settings
            log_dir = get_settings().workspace_dir / "logs"
            if log_dir.exists():
                recent = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]
                for f in recent:
                    log.write(f"[bold]--- {f.name} ---[/]")
                    content = f.read_text(encoding="utf-8", errors="replace")[-4000:]
                    for line in content.split("\n")[-30:]:
                        if "ERROR" in line:
                            log.write(f"[red]{line}[/]")
                        elif "WARNING" in line:
                            log.write(f"[yellow]{line}[/]")
                        else:
                            log.write(f"[dim]{line}[/]")
            else:
                log.write("[dim]No log files found. Run tagent to generate logs.[/]")
        except Exception as e:
            log.write(f"[red]Unable to load logs: {e}[/]")
        yield log
