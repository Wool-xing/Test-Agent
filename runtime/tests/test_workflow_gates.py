"""TDD: Workflow gate enforcement unit tests — RED phase."""

from __future__ import annotations

import pytest

from runtime.orchestrator.workflows.gates import (
    GateResult,
    check_smoke_gate,
    check_regression_gate,
    check_perf_gate,
)


class TestGateResult:
    def test_pass_warn_block_values(self):
        assert GateResult.PASS.value == "pass"
        assert GateResult.WARN.value == "warn"
        assert GateResult.BLOCK.value == "block"


class TestSmokeGate:
    def test_pass_when_p0_above_threshold(self):
        result = check_smoke_gate(p0_total=100, p0_passed=97)
        assert result == GateResult.PASS

    def test_pass_at_exact_threshold(self):
        result = check_smoke_gate(p0_total=100, p0_passed=95)
        assert result == GateResult.PASS

    def test_block_when_p0_below_threshold(self):
        result = check_smoke_gate(p0_total=100, p0_passed=94)
        assert result == GateResult.BLOCK

    def test_block_when_new_p0_bugs_found(self):
        result = check_smoke_gate(p0_total=100, p0_passed=98, new_p0_bugs=1)
        assert result == GateResult.BLOCK

    def test_pass_when_zero_tests_run(self):
        """Edge: 0 tests run → treat as BLOCK (nothing was tested)."""
        result = check_smoke_gate(p0_total=0, p0_passed=0)
        assert result == GateResult.BLOCK

    def test_threshold_override(self):
        """Custom threshold via parameter."""
        result = check_smoke_gate(p0_total=100, p0_passed=80, threshold=0.80)
        assert result == GateResult.PASS


class TestRegressionGate:
    def test_pass_when_above_threshold(self):
        result = check_regression_gate(total=200, passed=185)
        assert result == GateResult.PASS

    def test_block_when_below_threshold(self):
        result = check_regression_gate(total=200, passed=179)
        assert result == GateResult.BLOCK

    def test_pass_with_zero_skipped(self):
        """Edge: all tests pass, none skipped."""
        result = check_regression_gate(total=50, passed=50, failed=0)
        assert result == GateResult.PASS


class TestPerfGate:
    def test_ci_quick_mode_thresholds(self):
        """ci_quick: avg response < 500ms, p95 < 1000ms."""
        result = check_perf_gate(
            avg_response_ms=300, p95_response_ms=700, mode="ci_quick"
        )
        assert result == GateResult.PASS

    def test_ci_quick_blocks_when_over(self):
        result = check_perf_gate(
            avg_response_ms=600, p95_response_ms=700, mode="ci_quick"
        )
        assert result == GateResult.BLOCK

    def test_full_mode_thresholds(self):
        """full: avg < 2000ms, p95 < 5000ms."""
        result = check_perf_gate(
            avg_response_ms=1500, p95_response_ms=3000, mode="full"
        )
        assert result == GateResult.PASS

    def test_full_mode_blocks_when_over(self):
        result = check_perf_gate(
            avg_response_ms=2500, p95_response_ms=3000, mode="full"
        )
        assert result == GateResult.BLOCK

    def test_default_mode_is_ci_quick(self):
        """No mode → ci_quick thresholds."""
        result = check_perf_gate(avg_response_ms=300, p95_response_ms=700)
        assert result == GateResult.PASS
