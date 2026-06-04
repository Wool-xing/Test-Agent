"""Gate enforcement for test-coordinator pipeline.

Pure functions. Each gate inspects test result metrics and returns PASS/WARN/BLOCK.
Thresholds from skills/test-coordinator.md.
"""

from __future__ import annotations

from enum import Enum


class GateResult(str, Enum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


def check_smoke_gate(
    p0_total: int = 0,
    p0_passed: int = 0,
    new_p0_bugs: int = 0,
    threshold: float = 0.95,
) -> GateResult:
    """Smoke gate: P0 pass rate >= threshold AND 0 new P0 bugs.

    Args:
        p0_total: Total P0 test cases run
        p0_passed: Number of P0 tests that passed
        new_p0_bugs: New P0 bugs found during smoke
        threshold: Minimum pass rate (default 0.95 = 95%)
    """
    if new_p0_bugs > 0:
        return GateResult.BLOCK
    if p0_total == 0:
        return GateResult.BLOCK  # nothing tested
    rate = p0_passed / p0_total
    if rate >= threshold:
        return GateResult.PASS
    return GateResult.BLOCK


def check_regression_gate(
    total: int = 0,
    passed: int = 0,
    failed: int = 0,
    threshold: float = 0.90,
) -> GateResult:
    """Regression gate: overall pass rate >= threshold.

    Args:
        total: Total test cases
        passed: Passed test cases
        failed: Failed test cases
        threshold: Minimum pass rate (default 0.90)
    """
    if total == 0:
        return GateResult.BLOCK
    rate = passed / total
    if rate >= threshold:
        return GateResult.PASS
    return GateResult.BLOCK


def check_perf_gate(
    avg_response_ms: float = 0,
    p95_response_ms: float = 0,
    mode: str = "ci_quick",
) -> GateResult:
    """Performance gate: thresholds differ by mode.

    ci_quick: avg < 500ms, p95 < 1000ms
    full:     avg < 2000ms, p95 < 5000ms
    """
    if mode == "full":
        avg_ok = avg_response_ms <= 2000
        p95_ok = p95_response_ms <= 5000
    else:
        avg_ok = avg_response_ms <= 500
        p95_ok = p95_response_ms <= 1000

    if avg_ok and p95_ok:
        return GateResult.PASS
    return GateResult.BLOCK
