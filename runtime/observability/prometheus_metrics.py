"""Prometheus-compatible /metrics endpoint (plain text, zero dependencies).

Exposes:
- tagent_runs_total (counter)
- tagent_run_duration_seconds (histogram buckets)
- tagent_test_pass_rate (gauge)
- tagent_agent_errors_total (counter, by agent name)
- tagent_llm_call_duration_seconds (histogram)
- tagent_active_runs (gauge)
- tagent_circuit_breaker (gauge, 0=closed 1=open)
"""

from __future__ import annotations

import threading
from collections import defaultdict, deque


class MetricsRegistry:
    """Thread-safe in-process metrics store."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Counters
        self.runs_total: int = 0
        self.agent_errors: dict[str, int] = defaultdict(int)
        # Gauges
        self.active_runs: int = 0
        self.circuit_broken: int = 0
        self.last_pass_rate: float = 0.0
        # Histogram buckets (seconds): 0.1, 0.5, 1, 5, 10, 30, 60, 120, 300, 600
        self._MAX_HISTOGRAM_SAMPLES = 1000
        self.run_durations: deque[float] = deque(maxlen=self._MAX_HISTOGRAM_SAMPLES)
        self.llm_call_durations: deque[float] = deque(maxlen=self._MAX_HISTOGRAM_SAMPLES)
        self.HISTOGRAM_BUCKETS = [0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0]

    def inc_runs(self) -> None:
        with self._lock:
            self.runs_total += 1
            self.active_runs += 1

    def dec_active(self) -> None:
        with self._lock:
            self.active_runs = max(0, self.active_runs - 1)

    def record_run_duration(self, seconds: float) -> None:
        with self._lock:
            self.run_durations.append(seconds)

    def record_llm_duration(self, seconds: float) -> None:
        with self._lock:
            self.llm_call_durations.append(seconds)

    def inc_agent_error(self, agent_name: str) -> None:
        with self._lock:
            self.agent_errors[agent_name] += 1

    def set_pass_rate(self, rate: float) -> None:
        with self._lock:
            self.last_pass_rate = rate

    def set_circuit(self, broken: bool) -> None:
        with self._lock:
            self.circuit_broken = 1 if broken else 0

    def _bucket_counts(self, values: deque[float]) -> dict[float, int]:
        counts: dict[float, int] = {}
        for b in self.HISTOGRAM_BUCKETS:
            counts[b] = sum(1 for v in values if v <= b)
        return counts

    def render(self) -> str:
        """Render all metrics in Prometheus text format."""
        with self._lock:
            lines = [
                "# HELP tagent_runs_total Total number of test runs.",
                "# TYPE tagent_runs_total counter",
                f"tagent_runs_total {self.runs_total}",
                "",
                "# HELP tagent_active_runs Currently running tests.",
                "# TYPE tagent_active_runs gauge",
                f"tagent_active_runs {self.active_runs}",
                "",
                "# HELP tagent_test_pass_rate Last run test pass rate (0-1).",
                "# TYPE tagent_test_pass_rate gauge",
                f"tagent_test_pass_rate {self.last_pass_rate:.4f}",
                "",
                "# HELP tagent_circuit_breaker Circuit breaker status (0=closed 1=open).",
                "# TYPE tagent_circuit_breaker gauge",
                f"tagent_circuit_breaker {self.circuit_broken}",
                "",
                "# HELP tagent_run_duration_seconds Test run duration histogram.",
                "# TYPE tagent_run_duration_seconds histogram",
            ]
            for b, c in self._bucket_counts(self.run_durations).items():
                lines.append(f"tagent_run_duration_seconds_bucket{{le=\"{b}\"}} {c}")
            lines.append(f"tagent_run_duration_seconds_count {len(self.run_durations)}")
            lines.append("")

            lines += [
                "# HELP tagent_llm_call_duration_seconds LLM call duration histogram.",
                "# TYPE tagent_llm_call_duration_seconds histogram",
            ]
            for b, c in self._bucket_counts(self.llm_call_durations).items():
                lines.append(f"tagent_llm_call_duration_seconds_bucket{{le=\"{b}\"}} {c}")
            lines.append(f"tagent_llm_call_duration_seconds_count {len(self.llm_call_durations)}")
            lines.append("")

            lines += [
                "# HELP tagent_agent_errors_total Errors per agent.",
                "# TYPE tagent_agent_errors_total counter",
            ]
            for name, count in sorted(self.agent_errors.items()):
                lines.append(f'tagent_agent_errors_total{{agent="{name}"}} {count}')

            lines.append("")
            return "\n".join(lines)


# Global singleton
_registry: MetricsRegistry | None = None


def get_metrics() -> MetricsRegistry:
    global _registry
    if _registry is None:
        _registry = MetricsRegistry()
    return _registry


# ═══════════════════════════════════════════════════════════════
# FastAPI integration (optional — only if FastAPI installed)
# ═══════════════════════════════════════════════════════════════

def create_metrics_router():
    """Create a FastAPI router for /metrics. Caller mounts with app.include_router()."""
    try:
        from fastapi import APIRouter
        from fastapi.responses import PlainTextResponse
    except ImportError:
        return None

    router = APIRouter(tags=["observability"])

    @router.get("/metrics", response_class=PlainTextResponse)
    async def metrics():
        return get_metrics().render()

    @router.get("/metrics/json")
    async def metrics_json():
        m = get_metrics()
        return {
            "runs_total": m.runs_total,
            "active_runs": m.active_runs,
            "pass_rate": m.last_pass_rate,
            "circuit_broken": m.circuit_broken,
            "agent_errors": dict(m.agent_errors),
            "run_durations_count": len(m.run_durations),
            "llm_durations_count": len(m.llm_call_durations),
        }

    return router
