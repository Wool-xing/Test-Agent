# SPDX-License-Identifier: MIT
"""
FlakyGuard — pytest plugin for statistical flaky test detection + auto-quarantine.

Drop-in: add to conftest.py or install as pytest plugin.
Features:
- Chi-squared statistical test (not just threshold)
- Rolling window analysis (weighted toward recent runs)
- Auto-quarantine with 14-day time-box expiry
- Failure correlation clustering (shared root cause detection)
- P-F-P / F-P-F pattern detection with confidence scoring

Usage:
  pytest --flaky-guard  # enables plugin
  pytest --flaky-history workspace/flaky_history.json
"""

from __future__ import annotations

import json
import math
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

# ═══════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════

DEFAULT_HISTORY_FILE = "workspace/flaky_history.json"
DEFAULT_WINDOW_SIZE = 10          # Rolling window of recent runs
DEFAULT_QUARANTINE_DAYS = 14      # Time-box before auto-escalation
DEFAULT_CHISQ_THRESHOLD = 3.841   # p < 0.05, 1 degree of freedom
DEFAULT_FAIL_RATE_THRESHOLD = 0.3 # Minimum fail rate for quarantine
MAX_AUTO_RERUNS = 1               # Only 1 auto-rerun for classification


@dataclass
class TestHistory:
    """Per-test execution history."""
    nodeid: str
    runs: list[bool] = field(default_factory=list)  # True=pass, False=fail
    last_quarantined: float = 0.0
    quarantine_count: int = 0

    @property
    def fail_rate(self) -> float:
        if not self.runs:
            return 0.0
        return 1 - (sum(1 for r in self.runs if r) / len(self.runs))

    @property
    def is_quarantined(self) -> bool:
        if self.last_quarantined == 0:
            return False
        return (time.time() - self.last_quarantined) < DEFAULT_QUARANTINE_DAYS * 86400

    @property
    def quarantine_expired(self) -> bool:
        if self.last_quarantined == 0:
            return False
        return (time.time() - self.last_quarantined) >= DEFAULT_QUARANTINE_DAYS * 86400


# ═══════════════════════════════════════════════════════════════
# Statistical tests
# ═══════════════════════════════════════════════════════════════

def chi_squared_flaky(runs: list[bool]) -> tuple[float, bool]:
    """Chi-squared test: is the pass/fail pattern significantly non-random?
    Returns (statistic, is_flaky).
    """
    if len(runs) < 6:
        return 0.0, False

    # Count transitions
    pass_to_fail = 0
    fail_to_pass = 0
    total_pass = sum(1 for r in runs if r)
    total_fail = len(runs) - total_pass

    for i in range(len(runs) - 1):
        if runs[i] and not runs[i + 1]:
            pass_to_fail += 1
        elif not runs[i] and runs[i + 1]:
            fail_to_pass += 1

    transitions = pass_to_fail + fail_to_pass
    # Expected transitions if pattern is random
    expected_pf = total_pass * total_fail / len(runs) if len(runs) > 0 else 0
    expected_fp = total_fail * total_pass / len(runs) if len(runs) > 0 else 0
    expected_total = expected_pf + expected_fp

    if expected_total < 0.5:
        return 0.0, False

    chi2 = ((pass_to_fail - expected_pf) ** 2 / expected_pf +
            (fail_to_pass - expected_fp) ** 2 / expected_fp) if expected_pf > 0 and expected_fp > 0 else 0.0

    return chi2, chi2 > DEFAULT_CHISQ_THRESHOLD


def rolling_fail_rate(runs: list[bool], window: int = 5) -> float:
    """Weighted fail rate — recent runs weighted higher."""
    if not runs:
        return 0.0
    recent = runs[-window:]
    weights = [i + 1 for i in range(len(recent))]  # Linear ramp
    weighted_fails = sum(w for r, w in zip(recent, weights) if not r)
    return weighted_fails / sum(weights) if weights else 0.0


def detect_patterns(runs: list[bool]) -> dict[str, bool]:
    """Detect P-F-P and F-P-F patterns with confidence."""
    patterns = {"pfp": False, "fpf": False}
    if len(runs) < 3:
        return patterns

    pfp_count = 0
    fpf_count = 0
    for i in range(len(runs) - 2):
        if runs[i] and not runs[i + 1] and runs[i + 2]:
            pfp_count += 1
        elif not runs[i] and runs[i + 1] and not runs[i + 2]:
            fpf_count += 1

    patterns["pfp"] = pfp_count >= 2  # 2+ P-F-P patterns = inherently flaky
    patterns["fpf"] = fpf_count >= 2
    return patterns


# ═══════════════════════════════════════════════════════════════
# Failure clustering (shared root cause detection)
# ═══════════════════════════════════════════════════════════════

def cluster_failures(failures: list[dict]) -> list[dict]:
    """Cluster failures by exception type + top stack frame.
    Returns clusters with shared root cause candidates."""
    clusters: dict[str, list[dict]] = defaultdict(list)

    for f in failures:
        exc_type = f.get("exception_type", "Unknown")
        stack_top = f.get("stack_top", "unknown")
        key = f"{exc_type}::{stack_top}"
        clusters[key].append(f)

    return [{
        "signature": key,
        "count": len(items),
        "tests": [i.get("nodeid", "") for i in items[:10]],
        "shared_root_cause": len(items) >= 3,  # >3 same pattern = likely shared cause
    } for key, items in sorted(clusters.items(), key=lambda x: -len(x[1]))]


# ═══════════════════════════════════════════════════════════════
# Pytest plugin hooks
# ═══════════════════════════════════════════════════════════════

class FlakyGuardPlugin:
    def __init__(self, history_file: str = DEFAULT_HISTORY_FILE):
        self.history_file = Path(history_file)
        self.histories: dict[str, TestHistory] = {}
        self.current_results: dict[str, bool] = {}
        self.failures_detail: list[dict] = []
        self._load()

    def _load(self) -> None:
        if self.history_file.exists():
            try:
                data = json.loads(self.history_file.read_text(encoding="utf-8"))
                for nodeid, h in data.items():
                    th = TestHistory(nodeid=nodeid, runs=h.get("runs", []),
                                     last_quarantined=h.get("last_quarantined", 0),
                                     quarantine_count=h.get("quarantine_count", 0))
                    self.histories[nodeid] = th
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self) -> None:
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        data = {nid: {"runs": h.runs, "last_quarantined": h.last_quarantined,
                       "quarantine_count": h.quarantine_count}
                for nid, h in self.histories.items()}
        self.history_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def record_result(self, nodeid: str, passed: bool, exception_type: str = "",
                      stack_top: str = "") -> None:
        self.current_results[nodeid] = passed
        if not passed:
            self.failures_detail.append({
                "nodeid": nodeid, "exception_type": exception_type, "stack_top": stack_top,
            })

    def finalize(self) -> dict[str, Any]:
        """Called after test session. Updates history, detects flaky, generates quarantine."""
        # Update history
        for nodeid, passed in self.current_results.items():
            if nodeid not in self.histories:
                self.histories[nodeid] = TestHistory(nodeid=nodeid)
            h = self.histories[nodeid]
            h.runs.append(passed)
            if len(h.runs) > DEFAULT_WINDOW_SIZE * 3:
                h.runs = h.runs[-DEFAULT_WINDOW_SIZE * 3:]

        # Detect flaky tests
        flaky_tests: list[dict] = []
        new_quarantines: list[str] = []
        expired_quarantines: list[str] = []
        still_quarantined: list[str] = []

        for nodeid, h in self.histories.items():
            if len(h.runs) < 4:
                continue

            rolling_rate = rolling_fail_rate(h.runs)
            chi2, significant = chi_squared_flaky(h.runs)
            patterns = detect_patterns(h.runs)
            is_flaky = (rolling_rate >= DEFAULT_FAIL_RATE_THRESHOLD and significant) or patterns["pfp"]

            if is_flaky:
                flaky_tests.append({
                    "nodeid": nodeid,
                    "fail_rate": round(h.fail_rate, 3),
                    "rolling_fail_rate": round(rolling_rate, 3),
                    "chi2": round(chi2, 2),
                    "pfp_pattern": patterns["pfp"],
                    "fpf_pattern": patterns["fpf"],
                    "total_runs": len(h.runs),
                })
                if not h.is_quarantined:
                    h.last_quarantined = time.time()
                    h.quarantine_count += 1
                    new_quarantines.append(nodeid)
                else:
                    still_quarantined.append(nodeid)

            if h.quarantine_expired:
                expired_quarantines.append(nodeid)

        # Failure clustering
        clusters = cluster_failures(self.failures_detail)

        self._save()

        # Generate quarantine file
        quarantine_file = self.history_file.parent / "quarantine.txt"
        quarantined_ids = [n for n, h in self.histories.items() if h.is_quarantined]
        if quarantined_ids:
            quarantine_file.write_text("\n".join(quarantined_ids), encoding="utf-8")
        elif quarantine_file.exists():
            quarantine_file.unlink()

        return {
            "flaky_detected": len(flaky_tests),
            "new_quarantines": len(new_quarantines),
            "expired_quarantines": len(expired_quarantines),
            "still_quarantined": len(still_quarantined),
            "flaky_tests": flaky_tests,
            "failure_clusters": clusters,
        }


# ═══════════════════════════════════════════════════════════════
# Pytest hook registration (auto-detected by pytest)
# ═══════════════════════════════════════════════════════════════

_plugin: FlakyGuardPlugin | None = None


def pytest_addoption(parser):
    group = parser.getgroup("flaky-guard")
    group.addoption("--flaky-guard", action="store_true", default=False,
                    help="Enable FlakyGuard statistical flaky detection")
    group.addoption("--flaky-history", default=DEFAULT_HISTORY_FILE,
                    help="Path to flaky history JSON file")


def pytest_configure(config):
    global _plugin
    if config.getoption("--flaky-guard", False):
        _plugin = FlakyGuardPlugin(config.getoption("--flaky-history"))
        config.pluginmanager.register(_plugin, "flaky_guard")


def pytest_collection_modifyitems(config, items):
    """Deselect quarantined tests."""
    if not config.getoption("--flaky-guard", False) or _plugin is None:
        return

    quarantine_file = Path(config.getoption("--flaky-history")).parent / "quarantine.txt"
    if not quarantine_file.exists():
        return

    quarantined = set(quarantine_file.read_text(encoding="utf-8").strip().split("\n"))
    deselected = []
    kept = []
    for item in items:
        if item.nodeid in quarantined:
            deselected.append(item)
        else:
            kept.append(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = kept


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    if _plugin is None:
        return

    if call.when == "call":
        report = outcome.get_result()
        passed = report.passed
        exc_type = ""
        stack_top = ""
        if call.excinfo:
            exc_type = type(call.excinfo.value).__name__
            tb = call.excinfo.traceback
            if tb:
                # Get top stack frame (skip plugin internals)
                frames = []
                while tb is not None:
                    frames.append(tb)
                    tb = tb.tb_next
                for frame in reversed(frames):
                    fname = frame.tb_frame.f_code.co_filename
                    if "flaky_guard" not in fname and "site-packages" not in fname:
                        stack_top = f"{fname}:{frame.tb_lineno}"
                        break

        _plugin.record_result(item.nodeid, passed, exc_type, stack_top)


def pytest_sessionfinish(session):
    if _plugin is None:
        return

    summary = _plugin.finalize()
    if summary["flaky_detected"] > 0:
        print(f"\n--- FlakyGuard: {summary['flaky_detected']} flaky tests detected "
              f"({summary['new_quarantines']} new quarantines) ---")
        for ft in summary["flaky_tests"]:
            print(f"  [{ft['fail_rate']:.1%}] {ft['nodeid']} "
                  f"(chi2={ft['chi2']}, pfp={ft['pfp_pattern']})")

    if summary["failure_clusters"]:
        print(f"\n--- FlakyGuard: {len(summary['failure_clusters'])} failure clusters ---")
        for c in summary["failure_clusters"]:
            if c["shared_root_cause"]:
                print(f"  {c['signature']}: {c['count']} tests — likely shared root cause")
