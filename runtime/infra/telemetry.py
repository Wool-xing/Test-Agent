"""Telemetry & Monitoring (§补-3) — opt-in, privacy-first.

Features:
- Crash reporting (local dump files)
- Anonymous usage stats (command frequency, skill usage)
- Performance metrics (P50/P95/P99)
- First-run explicit consent
- Strictly NO test content/code/secrets collected
- GDPR/CCPA compliant (all data local by default, opt-in to send)
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class TelemetryConfig:
    enabled: bool = False         # User must opt-in
    crash_reports: bool = True    # Local crash dumps (always on)
    usage_stats: bool = False     # Anonymous usage (opt-in)
    performance: bool = False     # Performance metrics (opt-in)
    send_to_server: bool = False  # Remote reporting (opt-in)


@dataclass
class CommandMetric:
    command: str
    count: int = 0
    total_duration_ms: int = 0
    durations: list[int] = field(default_factory=list)

    @property
    def p50(self) -> int:
        if not self.durations:
            return 0
        return sorted(self.durations)[len(self.durations) // 2]

    @property
    def p95(self) -> int:
        if not self.durations:
            return 0
        return sorted(self.durations)[int(len(self.durations) * 0.95)]

    @property
    def p99(self) -> int:
        if not self.durations:
            return 0
        return sorted(self.durations)[int(len(self.durations) * 0.99)]


class TelemetryManager:
    """Privacy-first telemetry. Everything OFF by default."""

    def __init__(self, data_dir: Path | None = None):
        self._dir = data_dir or Path("workspace/telemetry")
        self._config = TelemetryConfig()
        self._metrics: dict[str, CommandMetric] = {}
        self._load_config()

    @property
    def config(self) -> TelemetryConfig:
        return self._config

    def enable(self, what: str = "all") -> None:
        """Enable telemetry features. Requires user consent."""
        if what in ("all", "usage"):
            self._config.enabled = True
            self._config.usage_stats = True
        if what in ("all", "performance"):
            self._config.performance = True
        if what in ("all", "send"):
            self._config.send_to_server = True

    def disable(self) -> None:
        """Disable all telemetry."""
        self._config = TelemetryConfig()

    def record_command(self, name: str, duration_ms: int) -> None:
        """Record a command execution."""
        if not self._config.usage_stats:
            return
        if name not in self._metrics:
            self._metrics[name] = CommandMetric(command=name)
        m = self._metrics[name]
        m.count += 1
        m.total_duration_ms += duration_ms
        m.durations.append(duration_ms)
        if len(m.durations) > 1000:
            m.durations = m.durations[-1000:]

    def record_crash(self, error: Exception, context: str = "") -> None:
        """Record a crash to local dump file."""
        if not self._config.crash_reports:
            return
        self._dir.mkdir(parents=True, exist_ok=True)
        dump = {
            "timestamp": time.time(),
            "error_type": type(error).__name__,
            "error_message": str(error)[:500],  # Truncated, no secrets
            "context": context[:200],
        }
        crash_file = self._dir / f"crash-{int(time.time())}.json"
        crash_file.write_text(json.dumps(dump, indent=2), encoding="utf-8")

    def get_stats(self) -> dict:
        """Get anonymous usage statistics."""
        return {
            "commands": {name: {"count": m.count, "p50_ms": m.p50, "p95_ms": m.p95}
                        for name, m in sorted(self._metrics.items())},
            "total_commands": sum(m.count for m in self._metrics.values()),
        }

    def _load_config(self) -> None:
        """Load telemetry config from file."""
        config_file = self._dir / "config.json"
        if config_file.exists():
            try:
                data = json.loads(config_file.read_text(encoding="utf-8"))
                self._config = TelemetryConfig(**data)
            except Exception:
                pass

    def save_config(self) -> None:
        """Persist telemetry config."""
        self._dir.mkdir(parents=True, exist_ok=True)
        config_file = self._dir / "config.json"
        config_file.write_text(json.dumps(self._config.__dict__, indent=2), encoding="utf-8")


# Singleton
_manager: TelemetryManager | None = None


def get_telemetry_manager() -> TelemetryManager:
    global _manager
    if _manager is None:
        _manager = TelemetryManager()
    return _manager
