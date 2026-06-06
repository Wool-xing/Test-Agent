"""tagent serve — 7x24 daemon mode (P3 #19).

Starts FastAPI server + background scheduler in a single process.
Use: tagent serve [--port PORT] [--host HOST]
"""

from __future__ import annotations

import signal
import sys
import threading
from pathlib import Path


def _signal_handler(stop_event: threading.Event):
    """Handle SIGINT/SIGTERM for graceful shutdown."""
    def handler(signum, frame):
        print("\nShutting down daemon...")
        stop_event.set()
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def serve(host: str = "127.0.0.1", port: int = 8800) -> None:
    """Start daemon: FastAPI + scheduler."""
    import uvicorn

    from runtime.cli._shared import console

    stop = threading.Event()
    _signal_handler(stop)

    # Start background scheduler
    try:
        from runtime.scheduler.scheduler import start_background
        thread, sched_stop = start_background()
        console.print("[dim]Scheduler started (tick=60s)[/]")
    except Exception as e:
        sched_stop = None
        logger.debug(f"Scheduler unavailable: {e}")
        console.print("[dim]Scheduler unavailable (croniter not installed)[/]")

    console.print(f"[green]Test-Agent daemon → http://{host}:{port}[/]")
    console.print("[dim]Endpoints: /health /catalog /run/text /webhooks/* /dashboard[/]")
    console.print("[dim]Ctrl+C to stop[/]")

    try:
        uvicorn.run(
            "runtime.api.main:app",
            host=host, port=port,
            log_level="info",
        )
    except KeyboardInterrupt:
        pass
    finally:
        if sched_stop:
            sched_stop.set()
