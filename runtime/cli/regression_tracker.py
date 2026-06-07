"""Regression detection — compare current test run against previous baseline.

Flags:
  - New failures (passed last time, failed this time)
  - Fixed tests (failed last time, passed this time)
  - Performance degradation (duration increase > threshold)
  - Coverage drop

Baselines stored in workspace/测试报告/{project}/baselines/regression_{run_id}.json
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REGRESSION_THRESHOLD_PCT = 20  # duration increase >20% = regression
COVERAGE_DROP_THRESHOLD = 5    # coverage drop >5% = regression


@dataclass
class RunResult:
    run_id: str
    timestamp: float = field(default_factory=time.time)
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: int = 0
    node_results: dict[str, dict] = field(default_factory=dict)
    detected_platform: str = ""
    coverage_pct: float = 0.0


@dataclass
class RegressionReport:
    new_failures: list[str] = field(default_factory=list)
    fixed: list[str] = field(default_factory=list)
    perf_regressions: list[dict] = field(default_factory=list)
    coverage_change: float = 0.0
    summary: str = ""


def _baseline_dir() -> Path:
    from runtime.config.settings import get_settings
    s = get_settings()
    d = s.resolve(s.workspace_dir) / "测试报告" / "baselines"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _latest_baseline() -> Path | None:
    """Find most recent regression baseline."""
    d = _baseline_dir()
    files = sorted(d.glob("regression_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    return files[0] if files else None


def save_baseline(result: RunResult) -> Path:
    """Save current run as regression baseline."""
    d = _baseline_dir()
    path = d / f"regression_{result.run_id}.json"
    path.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def compare_with_baseline(current: RunResult) -> RegressionReport:
    """Compare current run against previous baseline. Returns regression report."""
    prev_path = _latest_baseline()
    if prev_path is None:
        return RegressionReport(summary="No previous baseline — first run.")

    try:
        prev_data = json.loads(prev_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return RegressionReport(summary="Could not read baseline.")

    report = RegressionReport()
    prev_nodes = prev_data.get("node_results", {})
    curr_nodes = current.node_results

    # Detect new failures and fixes
    for nid, cr in curr_nodes.items():
        pr = prev_nodes.get(nid, {})
        if cr.get("ok") and not pr.get("ok", True):
            report.fixed.append(cr.get("name", nid))
        elif not cr.get("ok") and pr.get("ok", True):
            report.new_failures.append(cr.get("name", nid))

    # Detect perf regressions
    for nid, cr in curr_nodes.items():
        pr = prev_nodes.get(nid, {})
        curr_dur = cr.get("duration_ms", 0)
        prev_dur = pr.get("duration_ms", 0)
        if prev_dur > 0 and curr_dur > prev_dur * (1 + REGRESSION_THRESHOLD_PCT / 100):
            report.perf_regressions.append({
                "node": cr.get("name", nid),
                "prev_ms": prev_dur,
                "curr_ms": curr_dur,
                "increase_pct": round((curr_dur - prev_dur) / prev_dur * 100, 1),
            })

    # Coverage change
    prev_cov = prev_data.get("coverage_pct", 0)
    curr_cov = current.coverage_pct
    report.coverage_change = round(curr_cov - prev_cov, 1)

    # Summary
    parts = []
    if report.new_failures:
        parts.append(f"{len(report.new_failures)} new failure(s)")
    if report.fixed:
        parts.append(f"{len(report.fixed)} fixed")
    if report.perf_regressions:
        parts.append(f"{len(report.perf_regressions)} perf regression(s)")
    if report.coverage_change < -COVERAGE_DROP_THRESHOLD:
        parts.append(f"coverage dropped {abs(report.coverage_change):.1f}%")
    parts.append(f"{report.coverage_change:+.1f}% coverage")
    report.summary = " | ".join(parts) if parts else "No regressions detected"

    return report


def is_regression(report: RegressionReport) -> bool:
    """Check if report indicates any regression."""
    return bool(report.new_failures or report.perf_regressions or
                report.coverage_change < -COVERAGE_DROP_THRESHOLD)
