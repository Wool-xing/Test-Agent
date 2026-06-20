"""Tests for GateRegistry — validates all gate YAML files load correctly."""

from __future__ import annotations

from pathlib import Path

import pytest

from specs.gates.registry import Gate, GateCheck, GateRegistry

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def registry() -> GateRegistry:
    """Load the real specs/gates directory once per test module."""
    gates_dir = Path(__file__).resolve().parent.parent / "gates"
    return GateRegistry(gates_dir)


# ── Test: all gates load ──────────────────────────────────────────────────────


def test_all_gates_loaded(registry: GateRegistry):
    """Every .yaml file in specs/gates/ produces a Gate in the registry."""
    gates_dir = Path(__file__).resolve().parent.parent / "gates"
    yaml_count = len(list(gates_dir.glob("*.yaml")))
    assert yaml_count > 0, "No gate YAML files found"
    assert len(registry.gates) == yaml_count, (
        f"Expected {yaml_count} gates loaded, got {len(registry.gates)}"
    )


def test_registry_has_expected_gates(registry: GateRegistry):
    """The six canonical gates are present."""
    expected = {
        "smoke-gate",
        "regression-gate",
        "performance-gate",
        "security-gate",
        "release-gate",
        "ci-gate",
    }
    actual = set(registry.gates.keys())
    missing = expected - actual
    assert not missing, f"Missing gates: {missing}"


def test_smoke_gate_checks(registry: GateRegistry):
    """Smoke gate has the expected 3 checks."""
    gate = registry.get("smoke-gate")
    assert gate is not None
    assert len(gate.checks) == 3
    metrics = {c.metric for c in gate.checks}
    assert metrics == {"p0_pass_rate", "new_p0_bugs", "core_api_response_time"}
    assert gate.severity == "blocker"
    assert gate.auto_apply is True
    assert gate.timeout_minutes == 10


def test_regression_gate_checks(registry: GateRegistry):
    """Regression gate has 8 checks."""
    gate = registry.get("regression-gate")
    assert gate is not None
    assert len(gate.checks) == 8


def test_performance_gate_checks(registry: GateRegistry):
    """Performance gate has 5 checks."""
    gate = registry.get("performance-gate")
    assert gate is not None
    assert len(gate.checks) == 5


def test_security_gate_checks(registry: GateRegistry):
    """Security gate has 4 checks."""
    gate = registry.get("security-gate")
    assert gate is not None
    assert len(gate.checks) == 4


def test_release_gate_checks(registry: GateRegistry):
    """Release gate has 4 checks (one per sub-gate)."""
    gate = registry.get("release-gate")
    assert gate is not None
    assert len(gate.checks) == 4


def test_ci_gate_checks(registry: GateRegistry):
    """CI gate has 2 checks (smoke-only fast-feedback)."""
    gate = registry.get("ci-gate")
    assert gate is not None
    assert len(gate.checks) == 2
    assert gate.timeout_minutes == 10
    assert gate.auto_apply is True


# ── Test: get() and list_all() ────────────────────────────────────────────────


def test_get_existing(registry: GateRegistry):
    """get() returns a Gate for a known name."""
    gate = registry.get("smoke-gate")
    assert isinstance(gate, Gate)
    assert gate.name == "smoke-gate"


def test_get_nonexistent(registry: GateRegistry):
    """get() returns None for an unknown gate name."""
    assert registry.get("no-such-gate") is None


def test_list_all(registry: GateRegistry):
    """list_all() returns all gates."""
    gates = registry.list_all()
    assert len(gates) == len(registry.gates)
    names = {g.name for g in gates}
    assert "smoke-gate" in names


# ── Test: evaluate() ──────────────────────────────────────────────────────────


class TestEvaluateSmokeGate:
    """Evaluate the smoke-gate against various metric sets."""

    def test_smoke_all_pass(self, registry: GateRegistry):
        """All metrics at passing values."""
        passed, msgs = registry.evaluate(
            "smoke-gate",
            {"p0_pass_rate": 98, "new_p0_bugs": 0, "core_api_response_time": 1500},
        )
        assert passed is True
        assert len(msgs) == 3
        assert all("PASS" in m for m in msgs)

    def test_smoke_fail_pass_rate(self, registry: GateRegistry):
        """P0 pass rate below 95% fails."""
        passed, msgs = registry.evaluate(
            "smoke-gate",
            {"p0_pass_rate": 92, "new_p0_bugs": 0, "core_api_response_time": 1500},
        )
        assert passed is False
        assert any("FAIL" in m and "p0_pass_rate" in m for m in msgs)

    def test_smoke_fail_new_bug(self, registry: GateRegistry):
        """New P0 bug present fails."""
        passed, msgs = registry.evaluate(
            "smoke-gate",
            {"p0_pass_rate": 98, "new_p0_bugs": 1, "core_api_response_time": 1500},
        )
        assert passed is False
        assert any("FAIL" in m and "new_p0_bugs" in m for m in msgs)

    def test_smoke_fail_api_latency(self, registry: GateRegistry):
        """API latency above 3000ms fails."""
        passed, msgs = registry.evaluate(
            "smoke-gate",
            {"p0_pass_rate": 98, "new_p0_bugs": 0, "core_api_response_time": 3500},
        )
        assert passed is False
        assert any("FAIL" in m and "core_api_response_time" in m for m in msgs)

    def test_smoke_missing_metric(self, registry: GateRegistry):
        """Missing metric produces a FAIL."""
        passed, msgs = registry.evaluate(
            "smoke-gate",
            {"p0_pass_rate": 98, "new_p0_bugs": 0},
        )
        assert passed is False
        assert any("MISSING" in m for m in msgs)


class TestEvaluateCiGate:
    """Evaluate the ci-gate (fast-feedback, smoke-only)."""

    def test_ci_pass(self, registry: GateRegistry):
        passed, msgs = registry.evaluate(
            "ci-gate",
            {"p0_pass_rate": 96, "new_p0_bugs": 0},
        )
        assert passed is True

    def test_ci_fail(self, registry: GateRegistry):
        passed, msgs = registry.evaluate(
            "ci-gate",
            {"p0_pass_rate": 90, "new_p0_bugs": 0},
        )
        assert passed is False


class TestEvaluateEdgeCases:
    """Edge case tests for evaluate()."""

    def test_unknown_gate(self, registry: GateRegistry):
        """Evaluating a nonexistent gate returns False with a message."""
        passed, msgs = registry.evaluate("nonexistent", {})
        assert passed is False
        assert len(msgs) == 1
        assert "not found" in msgs[0]

    def test_empty_metrics(self, registry: GateRegistry):
        """All checks missing — all produce MISSING messages."""
        passed, msgs = registry.evaluate("smoke-gate", {})
        assert passed is False
        assert len(msgs) == 3
        assert all("MISSING" in m for m in msgs)


# ── Test: GateCheck operators ─────────────────────────────────────────────────


class TestGateCheckOperators:
    """Verify each operator evaluates correctly."""

    def test_gte(self):
        check = GateCheck(metric="x", operator="gte", threshold=95)
        assert check.evaluate(95) is True
        assert check.evaluate(100) is True
        assert check.evaluate(94) is False

    def test_lte(self):
        check = GateCheck(metric="x", operator="lte", threshold=500)
        assert check.evaluate(500) is True
        assert check.evaluate(400) is True
        assert check.evaluate(501) is False

    def test_eq(self):
        check = GateCheck(metric="x", operator="eq", threshold=0)
        assert check.evaluate(0) is True
        assert check.evaluate(1) is False

    def test_eq_float(self):
        check = GateCheck(metric="x", operator="eq", threshold=1.0)
        assert check.evaluate(1.0) is True
        assert check.evaluate(0.0) is False
        # The value in registry loads as float via yaml.safe_load, so
        # eq with int threshold loaded as float works
        check2 = GateCheck(metric="x", operator="eq", threshold=0.0)
        assert check2.evaluate(0.0) is True
        assert check2.evaluate(1.0) is False

    def test_lt(self):
        check = GateCheck(metric="x", operator="lt", threshold=3000)
        assert check.evaluate(1500) is True
        assert check.evaluate(3000) is False
        assert check.evaluate(3001) is False

    def test_gt(self):
        check = GateCheck(metric="x", operator="gt", threshold=100)
        assert check.evaluate(200) is True
        assert check.evaluate(100) is False
        assert check.evaluate(99) is False

    def test_unknown_operator_raises(self):
        check = GateCheck(metric="x", operator="bogus", threshold=0)
        with pytest.raises(ValueError, match="Unknown operator"):
            check.evaluate(0)


# ── Test: GateCheck threshold type is always float ────────────────────────────


def test_threshold_is_float(registry: GateRegistry):
    """All thresholds loaded from YAML are float, regardless of YAML type."""
    for gate in registry.list_all():
        for check in gate.checks:
            assert isinstance(check.threshold, float), (
                f"{gate.name}.{check.metric} threshold={check.threshold!r} "
                f"is {type(check.threshold).__name__}, expected float"
            )


# ── Test: list_all returns a copy-safe list ───────────────────────────────────


def test_list_all_is_copy(registry: GateRegistry):
    """list_all() returns a list that can be mutated without affecting registry."""
    gates = registry.list_all()
    gates.clear()
    assert len(registry.list_all()) > 0
