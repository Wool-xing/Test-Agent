# SPDX-License-Identifier: MIT
"""
Silent Failure Detector — 沉默故障检测 (Phase 3.2).

Detects degradations that stay below alert thresholds: slow latency creep,
error-rate drift, pass-rate erosion, metric baseline shift. Catches what
traditional threshold-based alerting misses.

Integrates with:
  - tracing_validator.py  (Jaeger trace latency/duration trends)
  - web_vitals_collector.py (LCP/FID/CLS drift over releases)
  - prometheus_metrics.py   (run duration, error rate, pass rate trends)
  - dora_tracker.py         (rework rate, MTTR drift)

Referenced by: 07-测试执行 expert + 02-coverage-matrix Phase 3.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════════

@dataclass
class MetricPoint:
    timestamp: float
    value: float
    label: str = ""

@dataclass
class DriftResult:
    metric_name: str
    source: str                    # "tracing" | "web_vitals" | "prometheus" | "custom"
    window_size: int               # number of data points analyzed
    current_mean: float
    baseline_mean: float
    mean_shift_pct: float          # % change from baseline
    trend_slope: float             # linear regression slope (per-point)
    trend_pvalue: float | None     # Mann-Kendall trend test p-value
    severity: str                  # "silent" | "impending" | "breached"
    threshold: float
    threshold_margin_pct: float    # how close to threshold (%)
    recommendation: str
    detail: dict[str, Any] = field(default_factory=dict)

@dataclass
class SilentFailureReport:
    source: str
    checked_at: str                # ISO 8601
    n_metrics: int
    results: list[DriftResult]
    silent_count: int = 0
    impending_count: int = 0
    breached_count: int = 0
    overall_severity: str = "pass"  # "pass" | "warning" | "fail"
    summary_lines: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# Core: threshold drift detection
# ═══════════════════════════════════════════════════════════════

def _linear_trend(values: np.ndarray) -> float:
    """Ordinary least squares slope. Returns slope per index step."""
    if len(values) < 3:
        return 0.0
    x = np.arange(len(values), dtype=float)
    x_mean = x.mean()
    y_mean = values.mean()
    num = ((x - x_mean) * (values - y_mean)).sum()
    den = ((x - x_mean) ** 2).sum()
    return float(num / den) if den > 0 else 0.0


def _mann_kendall(values: np.ndarray) -> float:
    """Mann-Kendall trend test. Returns approximate two-sided p-value."""
    n = len(values)
    if n < 4:
        return 1.0
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            s += int(np.sign(values[j] - values[i]))
    # Variance
    var_s = (n * (n - 1) * (2 * n + 5)) / 18.0
    if var_s == 0:
        return 1.0
    z = (s - np.sign(s)) / np.sqrt(var_s)
    # Approximate two-sided p-value from standard normal
    from math import erf, sqrt
    p = 2 * (1.0 - 0.5 * (1.0 + erf(abs(z) / sqrt(2))))
    return p


def detect_threshold_drift(
    metric_name: str,
    points: list[float],
    threshold: float,
    *,
    source: str = "custom",
    direction: str = "above",     # "above" = bad when > threshold, "below" = bad when < threshold
    baseline_points: list[float] | None = None,
    drift_pct_threshold: float = 0.15,   # 15% shift from baseline = warning
    margin_pct: float = 0.2,             # within 20% of threshold = impending
) -> DriftResult:
    """
    Detect silent threshold drift from a time series.

    Args:
      metric_name: human-readable name (e.g. "API P95 latency")
      points: most recent metric values (time-ordered, oldest→newest)
      threshold: alert threshold value
      direction: "above" (bad if above threshold, e.g. latency/errors)
                 or "below" (bad if below threshold, e.g. pass rate/coverage)
      baseline_points: historical baseline (optional; if None, uses first half of points)
      drift_pct_threshold: mean shift % that triggers warning
      margin_pct: % of threshold considered "impending" zone
    """
    arr = np.asarray(points, dtype=float)
    n = len(arr)
    if n < 3:
        return DriftResult(
            metric_name=metric_name, source=source, window_size=n,
            current_mean=float(arr.mean()) if n > 0 else 0.0,
            baseline_mean=0.0, mean_shift_pct=0.0,
            trend_slope=0.0, trend_pvalue=None,
            severity="silent", threshold=threshold,
            threshold_margin_pct=1.0,
            recommendation="Insufficient data points (<3); collect more metrics.",
        )

    if baseline_points:
        baseline_arr = np.asarray(baseline_points, dtype=float)
    else:
        split = max(n // 2, 1)
        baseline_arr = arr[:split]

    current_mean = float(arr.mean())
    baseline_mean = float(baseline_arr.mean()) if len(baseline_arr) > 0 else current_mean
    mean_shift = abs(current_mean - baseline_mean) / max(abs(baseline_mean), 1e-9)

    slope = _linear_trend(arr)
    mk_pvalue = _mann_kendall(arr)

    # Severity classification
    if direction == "above":
        margin = (threshold - current_mean) / max(threshold, 1e-9)
        breached = current_mean >= threshold
    else:
        margin = (current_mean - threshold) / max(threshold, 1e-9)
        breached = current_mean <= threshold

    if breached:
        severity = "breached"
        recommendation = (
            f"{metric_name} has breached threshold ({current_mean:.3f} vs {threshold}). "
            "Immediate investigation required."
        )
    elif mean_shift >= drift_pct_threshold or (mk_pvalue is not None and mk_pvalue < 0.05):
        if margin <= margin_pct:
            severity = "impending"
            recommendation = (
                f"{metric_name} trending toward threshold (margin={margin:.1%}, "
                f"shift={mean_shift:.1%}). Schedule investigation this sprint."
            )
        else:
            severity = "silent"
            recommendation = (
                f"{metric_name} shows statistically significant drift "
                f"(shift={mean_shift:.1%}, p={mk_pvalue:.4f}) but remains "
                f"well within threshold. Monitor weekly."
            )
    else:
        severity = "silent"
        recommendation = f"{metric_name} is stable. No drift detected."

    return DriftResult(
        metric_name=metric_name,
        source=source,
        window_size=n,
        current_mean=round(current_mean, 4),
        baseline_mean=round(baseline_mean, 4),
        mean_shift_pct=round(mean_shift, 4),
        trend_slope=round(slope, 6),
        trend_pvalue=round(mk_pvalue, 4) if mk_pvalue is not None else None,
        severity=severity,
        threshold=threshold,
        threshold_margin_pct=round(abs(margin), 4),
        recommendation=recommendation,
        detail={
            "direction": direction,
            "latest_value": float(arr[-1]),
            "min": float(arr.min()),
            "max": float(arr.max()),
            "std": float(arr.std()),
        },
    )


# ═══════════════════════════════════════════════════════════════
# Multi-metric batch detection
# ═══════════════════════════════════════════════════════════════

@dataclass
class MetricConfig:
    name: str
    source: str
    points: list[float]
    threshold: float
    direction: str = "above"
    baseline_points: list[float] | None = None


def batch_detect(configs: list[MetricConfig]) -> SilentFailureReport:
    """Run drift detection across multiple metrics and produce a unified report."""
    results: list[DriftResult] = []
    for cfg in configs:
        r = detect_threshold_drift(
            metric_name=cfg.name,
            points=cfg.points,
            threshold=cfg.threshold,
            source=cfg.source,
            direction=cfg.direction,
            baseline_points=cfg.baseline_points,
        )
        results.append(r)

    silent = sum(1 for r in results if r.severity == "silent")
    impending = sum(1 for r in results if r.severity == "impending")
    breached = sum(1 for r in results if r.severity == "breached")

    severity = "pass"
    if breached > 0:
        severity = "fail"
    elif impending > 0:
        severity = "warning"

    summary = [
        f"Silent Failure Scan: {len(results)} metrics checked",
        f"  Silent (stable):    {silent}",
        f"  Impending (drift):  {impending}",
        f"  Breached (alert):   {breached}",
        f"  Overall: {severity.upper()}",
    ]
    for r in results:
        if r.severity != "silent":
            summary.append(f"  ! {r.metric_name}: {r.severity} — {r.recommendation}")

    return SilentFailureReport(
        source="batch",
        checked_at=datetime.now(timezone.utc).isoformat(),
        n_metrics=len(results),
        results=results,
        silent_count=silent,
        impending_count=impending,
        breached_count=breached,
        overall_severity=severity,
        summary_lines=summary,
    )


# ═══════════════════════════════════════════════════════════════
# Source-specific collectors
# ═══════════════════════════════════════════════════════════════

def collect_from_tracing(
    trace_durations_ms: list[float],
    threshold_ms: float = 500.0,
    baseline_ms: list[float] | None = None,
) -> DriftResult:
    """Detect latency drift from trace durations (feed from Jaeger/Zipkin)."""
    return detect_threshold_drift(
        metric_name="trace_duration_p95_ms",
        points=trace_durations_ms,
        threshold=threshold_ms,
        source="tracing",
        direction="above",
        baseline_points=baseline_ms,
    )


def collect_from_web_vitals(
    metric_name: str,
    values: list[float],
    threshold: float,
    baseline: list[float] | None = None,
) -> DriftResult:
    """
    Detect web vitals drift (LCP/FID/CLS/FCP/TTFB/INP).
    threshold: "poor" boundary from web_vitals_collector.WEB_VITALS_THRESHOLDS.
    """
    return detect_threshold_drift(
        metric_name=f"web_vital_{metric_name}",
        points=values,
        threshold=threshold,
        source="web_vitals",
        direction="above",
        baseline_points=baseline,
    )


def collect_from_prometheus_counter(
    metric_name: str,
    values: list[float],
    threshold: float = 10.0,
    baseline: list[float] | None = None,
) -> DriftResult:
    """Detect error rate drift from Prometheus counter metrics."""
    return detect_threshold_drift(
        metric_name=f"prom_{metric_name}",
        points=values,
        threshold=threshold,
        source="prometheus",
        direction="above",
        baseline_points=baseline,
    )


def collect_from_prometheus_gauge(
    metric_name: str,
    values: list[float],
    threshold: float,
    direction: str = "below",
    baseline: list[float] | None = None,
) -> DriftResult:
    """
    Detect gauge drift (pass rate, active runs, circuit breaker).
    direction: "below" for pass rate (bad when below), "above" for others.
    """
    return detect_threshold_drift(
        metric_name=f"prom_{metric_name}",
        points=values,
        threshold=threshold,
        source="prometheus",
        direction=direction,
        baseline_points=baseline,
    )


# ═══════════════════════════════════════════════════════════════
# Time-window utilities
# ═══════════════════════════════════════════════════════════════

class SlidingWindowStore:
    """Store metric points in rolling windows for trend analysis."""

    def __init__(self, max_points: int = 200):
        self._windows: dict[str, deque[float]] = {}
        self._max = max_points

    def push(self, name: str, value: float) -> None:
        if name not in self._windows:
            self._windows[name] = deque(maxlen=self._max)
        self._windows[name].append(value)

    def get(self, name: str) -> list[float]:
        return list(self._windows.get(name, []))

    def get_all(self) -> dict[str, list[float]]:
        return {k: list(v) for k, v in self._windows.items()}

    def clear(self, name: str | None = None) -> None:
        if name:
            self._windows.pop(name, None)
        else:
            self._windows.clear()

    def __len__(self) -> int:
        return sum(len(v) for v in self._windows.values())


# ═══════════════════════════════════════════════════════════════
# Report export
# ═══════════════════════════════════════════════════════════════

def export_report(report: SilentFailureReport,
                  output_dir: str = "workspace/测试报告/silent-failures") -> str:
    """Export SilentFailureReport as JSON."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(output_dir) / f"silent_failure_{ts}.json"

    data = {
        "source": report.source,
        "checked_at": report.checked_at,
        "n_metrics": report.n_metrics,
        "overall_severity": report.overall_severity,
        "counts": {
            "silent": report.silent_count,
            "impending": report.impending_count,
            "breached": report.breached_count,
        },
        "results": [
            {
                "metric_name": r.metric_name,
                "source": r.source,
                "severity": r.severity,
                "current_mean": r.current_mean,
                "baseline_mean": r.baseline_mean,
                "mean_shift_pct": r.mean_shift_pct,
                "trend_slope": r.trend_slope,
                "trend_pvalue": r.trend_pvalue,
                "threshold": r.threshold,
                "threshold_margin_pct": r.threshold_margin_pct,
                "recommendation": r.recommendation,
                "detail": r.detail,
            }
            for r in report.results
        ],
        "summary_lines": report.summary_lines,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Silent failure report → %s (severity=%s)", path, report.overall_severity)
    return str(path)


def ci_summary(report: SilentFailureReport) -> str:
    """One-line CI-friendly summary."""
    status = {"pass": "PASS", "warning": "WARN", "fail": "FAIL"}
    lines = [
        f" Silent Failures [{status.get(report.overall_severity, report.overall_severity)}] "
        f"{report.n_metrics} metrics scanned"
    ]
    for r in report.results:
        if r.severity != "silent":
            lines.append(f"   {r.severity.upper()}: {r.metric_name} — {r.recommendation}")
    if report.overall_severity == "pass":
        lines.append("   No silent failures detected.")
    return "\n".join(lines)
