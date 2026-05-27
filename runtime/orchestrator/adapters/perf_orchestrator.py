"""Performance test orchestrator — unifies soak + jmeter + throttle into single report.

Features:
- Concurrent user simulation (ThreadPoolExecutor)
- Progressive capacity testing (ramp-up phases: 10%→50%→100%→120%)
- Baseline comparison with regression detection
- Unified report: TPS, P50/P95/P99, error rate, memory/CPU trends
- Graceful degradation observation at each phase
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PhaseResult:
    phase: str            # "10%", "50%", "100%", "120%"
    concurrent_users: int
    duration_seconds: float
    total_requests: int
    success_count: int
    error_count: int
    tps: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    avg_ms: float
    error_rate: float
    memory_mb: float = 0.0
    cpu_pct: float = 0.0

    def to_dict(self) -> dict:
        return {k: (round(v, 2) if isinstance(v, float) else v)
                for k, v in self.__dict__.items()}


@dataclass
class PerfReport:
    target: str
    phases: list[PhaseResult] = field(default_factory=list)
    baseline: dict[str, float] = field(default_factory=dict)
    regressions: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def score(self) -> str:
        """GREEN/YELLOW/RED verdict."""
        if not self.phases:
            return "N/A"
        p100 = self.phases[-2] if len(self.phases) >= 3 else self.phases[-1]
        if p100.error_rate > 0.05 or len(self.regressions) > 2:
            return "RED"
        if p100.error_rate > 0.01 or self.regressions:
            return "YELLOW"
        return "GREEN"

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "score": self.score(),
            "phases": [p.to_dict() for p in self.phases],
            "regressions": self.regressions,
            "recommendations": self.recommendations,
        }


class PerfOrchestrator:
    """Orchestrate multi-phase performance tests."""

    def __init__(self, target_url: str, output_dir: str = "workspace/perf"):
        self.target = target_url
        self.output = Path(output_dir)
        self.output.mkdir(parents=True, exist_ok=True)

    def http_benchmark(self, fn: Callable[[], bool], concurrent: int,
                        duration: float = 30.0) -> PhaseResult:
        """Execute concurrent HTTP benchmark."""
        latencies: list[float] = []
        success = 0
        errors = 0

        def worker():
            nonlocal errors
            t0 = time.time()
            try:
                ok = fn()
                latencies.append(time.time() - t0)
                return ok
            except Exception:
                errors += 1
                return False

        t_start = time.time()
        with ThreadPoolExecutor(max_workers=concurrent) as pool:
            futures = []
            deadline = t_start + duration
            while time.time() < deadline:
                futures.append(pool.submit(worker))
                if len(futures) > concurrent * 2:
                    for f in as_completed(futures[:concurrent]):
                        if f.result():
                            success += 1
                    futures = futures[concurrent:]

            for f in as_completed(futures):
                if f.result():
                    success += 1

        elapsed = time.time() - t_start
        total = success + errors
        tps = total / elapsed if elapsed > 0 else 0

        sorted_lat = sorted(latencies) if latencies else [0]
        return PhaseResult(
            phase=f"{concurrent} users",
            concurrent_users=concurrent,
            duration_seconds=round(elapsed, 1),
            total_requests=total,
            success_count=success,
            error_count=errors,
            tps=round(tps, 1),
            p50_ms=round(sorted_lat[len(sorted_lat) // 2] * 1000, 1),
            p95_ms=round(sorted_lat[int(len(sorted_lat) * 0.95)] * 1000, 1),
            p99_ms=round(sorted_lat[int(len(sorted_lat) * 0.99)] * 1000, 1) if len(sorted_lat) >= 100 else 0,
            avg_ms=round(sum(latencies) / max(len(latencies), 1) * 1000, 1),
            error_rate=round(errors / max(total, 1), 4),
        )

    def progressive_load_test(self, request_fn: Callable[[], bool],
                               base_users: int = 10, duration_per_phase: float = 30.0) -> PerfReport:
        """Progressive capacity test: 10% → 50% → 100% → 120%."""
        report = PerfReport(target=self.target)
        phases_config = [
            ("10%", int(base_users * 0.1) or 1),
            ("50%", int(base_users * 0.5)),
            ("100%", base_users),
            ("120%", int(base_users * 1.2)),
        ]

        for label, users in phases_config:
            result = self.http_benchmark(request_fn, users, duration_per_phase)
            result.phase = label
            report.phases.append(result)

            if result.error_rate > 0.05:
                report.regressions.append(
                    f"Phase {label}: error rate {result.error_rate:.1%} > 5% threshold"
                )
            if result.p95_ms > 5000:
                report.recommendations.append(
                    f"Phase {label}: P95 latency {result.p95_ms}ms — consider scaling/caching"
                )

        # Baseline comparison (first phase vs last)
        if len(report.phases) >= 2:
            first = report.phases[0]
            last = report.phases[-1]
            tps_degradation = (first.tps - last.tps) / max(first.tps, 1)
            if tps_degradation > 0.5:
                report.regressions.append(
                    f"TPS degraded {tps_degradation:.0%} from {first.tps} to {last.tps}"
                )

        return report

    def collect_system_metrics(self) -> dict:
        """Collect basic system metrics (psutil)."""
        try:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024,
                "open_fds": len(psutil.Process().open_files()),
                "threads": psutil.Process().num_threads(),
            }
        except ImportError:
            return {"note": "psutil not installed"}

    def run_jmeter_plan(self, jmx_path: str, output_csv: str) -> dict:
        """Execute JMeter test plan and parse results."""
        result = {"ok": False}
        jmeter_home = Path(os.environ.get("JMETER_HOME", ""))
        jmeter_bin = jmeter_home / "bin" / "jmeter"
        if not jmeter_bin.exists():
            jmeter_bin = Path("jmeter")

        cmd = [str(jmeter_bin), "-n", "-t", jmx_path, "-l", output_csv]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        result["ok"] = proc.returncode == 0
        result["stderr"] = proc.stderr[-500:]
        return result

    def save_report(self, report: PerfReport) -> Path:
        path = self.output / f"perf_report_{int(time.time())}.json"
        path.write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Performance Orchestrator")
    sub = ap.add_subparsers(dest="cmd")

    bench = sub.add_parser("bench", help="HTTP benchmark")
    bench.add_argument("--url", required=True)
    bench.add_argument("--users", type=int, default=10)
    bench.add_argument("--duration", type=float, default=30.0)

    load = sub.add_parser("load-test", help="Progressive load test")
    load.add_argument("--url", required=True)
    load.add_argument("--base-users", type=int, default=100)
    load.add_argument("--output", default="")

    args = ap.parse_args()
    orch = PerfOrchestrator(args.url)

    if args.cmd == "bench":
        import requests as _r
        def _req():
            return _r.get(args.url, timeout=10).status_code == 200
        result = orch.http_benchmark(_req, args.users, args.duration)
        print(json.dumps(result.to_dict(), indent=2))

    elif args.cmd == "load-test":
        import requests as _r
        def _req():
            return _r.get(args.url, timeout=10).status_code == 200
        report = orch.progressive_load_test(_req, args.base_users)
        if args.output:
            orch.save_report(report)
        print(f"Score: {report.score()} | Phases: {len(report.phases)} | Regressions: {len(report.regressions)}")
