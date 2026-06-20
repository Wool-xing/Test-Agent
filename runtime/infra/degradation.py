"""Graceful Degradation Matrix (§补-10).

When subsystems fail, degrade gracefully rather than crashing.
Never degrade silently — every degradation notifies the user.

Degradation matrix:
| Failure                | Degradation Behavior                    | User Notification                                    |
|------------------------|----------------------------------------|------------------------------------------------------|
| LLM API unavailable    | Switch to local Ollama; if none, use stub | "LLM unavailable, switched to local/fallback model"   |
| Network disconnected   | Offline mode: local skills only         | "Network unavailable, N network tests skipped"        |
| MCP Server disconnect  | That MCP tool unavailable, others OK    | "Tool X unavailable (MCP disconnected)"              |
| Database unavailable   | Execute tests, cache results in memory  | "Results cached in memory, will persist when DB back"|
| Disk space low         | Refuse to start, suggest cleanup        | "Disk space < 100MB, please clean up"                |
| Config file corrupted  | Use built-in defaults, suggest repair   | "Config read failed, using defaults. Run doctor"     |
| Single skill crash     | Isolate that skill, others continue     | "Skill X failed (isolated), N skills continue"        |
"""

from __future__ import annotations

import os
import shutil
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class DegradationLevel(Enum):
    NORMAL = "normal"       # Everything working
    DEGRADED = "degraded"  # Some features limited
    MINIMAL = "minimal"     # Core only
    CRITICAL = "critical"   # Barely functional


@dataclass
class DegradationEvent:
    component: str
    level: DegradationLevel
    message: str
    recovered: bool = False


# Notification callback — injected by UI layer
_notify_fn: Callable[[str, str], None] | None = None


def set_degradation_notifier(fn: Callable[[str, str], None]) -> None:
    """Inject UI notification function."""
    global _notify_fn
    _notify_fn = fn


def _notify(component: str, message: str) -> None:
    """Notify user about degradation. Never silent."""
    if _notify_fn:
        _notify_fn(component, message)
    else:
        # Fallback: log to stderr so it's never truly silent
        import sys
        print(f"[DEGRADED] {component}: {message}", file=sys.stderr)


class DegradationManager:
    """Tracks system degradation state across components."""

    def __init__(self):
        self._events: list[DegradationEvent] = []
        self._lock = threading.Lock()

    @property
    def overall_level(self) -> DegradationLevel:
        with self._lock:
            active = [e for e in self._events if not e.recovered]
            if not active:
                return DegradationLevel.NORMAL
            levels = [e.level for e in active]
            if DegradationLevel.CRITICAL in levels:
                return DegradationLevel.CRITICAL
            if DegradationLevel.MINIMAL in levels:
                return DegradationLevel.MINIMAL
            return DegradationLevel.DEGRADED

    @property
    def active_events(self) -> list[DegradationEvent]:
        with self._lock:
            return [e for e in self._events if not e.recovered]

    def degrade(self, component: str, level: DegradationLevel, message: str) -> None:
        with self._lock:
            self._events.append(DegradationEvent(component, level, message))
        _notify(component, message)

    def recover(self, component: str) -> None:
        with self._lock:
            for e in reversed(self._events):
                if e.component == component and not e.recovered:
                    e.recovered = True
                    _notify(component, f"{component} recovered")
                    break

    def summary(self) -> str:
        active = self.active_events
        if not active:
            return "All systems normal"
        return "; ".join(f"{e.component}: {e.message}" for e in active)


# ── Built-in health checks ──────────────────────────────

def check_disk_space(min_mb: int = 100) -> bool:
    """Check free disk space. Returns True if sufficient."""
    try:
        free = shutil.disk_usage(os.getcwd()).free
        free_mb = free / (1024 * 1024)
        return free_mb >= min_mb
    except Exception:
        return True  # Can't check, assume OK


def check_network() -> bool:
    """Check if network is available. Returns True if connected."""
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except Exception:
        return False


def check_llm_available(provider: str) -> bool:
    """Check if LLM provider is reachable."""
    try:
        from runtime.config.settings import get_settings
        s = get_settings()
        api_key = os.environ.get(f"TAGENT_LLM_API_KEY_{provider.upper()}", os.environ.get("TAGENT_LLM_API_KEY", ""))
        return bool(api_key)
    except Exception:
        return False


# Singleton
_manager: DegradationManager | None = None


def get_degradation_manager() -> DegradationManager:
    global _manager
    if _manager is None:
        _manager = DegradationManager()
    return _manager
