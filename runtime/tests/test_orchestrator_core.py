"""TDD tests for runtime/orchestrator/ pure-logic modules:
hooks, context, release_readiness, workflow/gates, metrics/parser.

Target: boost runtime/orchestrator/ coverage from 50% toward 65%.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ═══════════════════════════════════════════════════════════════════════════
# hooks.py — HookRegistry
# ═══════════════════════════════════════════════════════════════════════════

class TestHookRegistry:
    def test_registry_creation(self):
        """HookRegistry should create with empty lists."""
        from runtime.orchestrator.hooks import HookRegistry
        reg = HookRegistry()
        assert reg.before == []
        assert reg.after == []
        assert reg.on_error == []

    def test_register_before(self):
        """register_before should add hook to before list."""
        from runtime.orchestrator.hooks import HookRegistry
        reg = HookRegistry()
        calls = []
        reg.register_before(lambda nid, ctx: calls.append(("before", nid)))
        assert len(reg.before) == 1

    def test_register_after(self):
        """register_after should add hook to after list."""
        from runtime.orchestrator.hooks import HookRegistry
        reg = HookRegistry()
        calls = []
        reg.register_after(lambda nid, ctx: calls.append(("after", nid)))
        assert len(reg.after) == 1

    def test_register_error(self):
        """register_error should add hook to on_error list."""
        from runtime.orchestrator.hooks import HookRegistry
        reg = HookRegistry()
        calls = []
        reg.register_error(lambda nid, ctx: calls.append(("error", nid)))
        assert len(reg.on_error) == 1

    def test_fire_before_calls_all(self):
        """fire_before should invoke all registered before hooks."""
        from runtime.orchestrator.hooks import HookRegistry
        reg = HookRegistry()
        calls = []
        reg.register_before(lambda nid, ctx: calls.append(nid))
        reg.register_before(lambda nid, ctx: calls.append(nid + "_2"))
        reg.fire_before("n0", {"name": "test"})
        assert calls == ["n0", "n0_2"]

    def test_fire_after_calls_all(self):
        """fire_after should invoke all registered after hooks."""
        from runtime.orchestrator.hooks import HookRegistry
        reg = HookRegistry()
        calls = []
        reg.register_after(lambda nid, ctx: calls.append(nid))
        reg.fire_after("n1", {"name": "test", "results": {}})
        assert calls == ["n1"]

    def test_fire_error_calls_all(self):
        """fire_error should invoke all registered error hooks."""
        from runtime.orchestrator.hooks import HookRegistry
        reg = HookRegistry()
        calls = []
        reg.register_error(lambda nid, ctx: calls.append(ctx.get("error")))
        reg.fire_error("n2", {"name": "test", "error": "timeout"})
        assert calls == ["timeout"]

    def test_fire_before_survives_exceptions(self):
        """fire_before should not crash if a hook raises an exception."""
        from runtime.orchestrator.hooks import HookRegistry
        reg = HookRegistry()
        calls = []

        def bad_hook(nid, ctx):
            raise RuntimeError("boom")

        reg.register_before(bad_hook)
        reg.register_before(lambda nid, ctx: calls.append("ok"))

        reg.fire_before("n0", {})
        assert calls == ["ok"]  # second hook should still fire

    def test_fire_after_survives_exceptions(self):
        """fire_after should not crash if a hook raises."""
        from runtime.orchestrator.hooks import HookRegistry
        reg = HookRegistry()

        def bad_hook(nid, ctx):
            raise ValueError("fail")

        reg.register_after(bad_hook)
        reg.fire_after("n0", {})  # no exception

    def test_global_registry_singleton(self):
        """get_hook_registry should return same instance."""
        from runtime.orchestrator.hooks import get_hook_registry, reset_hook_registry
        reset_hook_registry()
        r1 = get_hook_registry()
        r2 = get_hook_registry()
        assert r1 is r2

    def test_reset_hook_registry(self):
        """reset_hook_registry should create fresh instance."""
        from runtime.orchestrator.hooks import get_hook_registry, reset_hook_registry
        r1 = get_hook_registry()
        r1.register_before(lambda n, c: None)
        reset_hook_registry()
        r2 = get_hook_registry()
        assert r1 is not r2
        assert r2.before == []


# ═══════════════════════════════════════════════════════════════════════════
# context.py — ExecutionContext
# ═══════════════════════════════════════════════════════════════════════════

class TestExecutionContext:
    def test_context_creation(self):
        """ExecutionContext should create with empty outputs."""
        from runtime.orchestrator.context import ExecutionContext
        ctx = ExecutionContext(run_id="run-001")
        assert ctx.run_id == "run-001"
        assert ctx.upstream_outputs == {}
        assert ctx.upstream_meta == {}

    def test_set_and_get_output(self):
        """set_output + get_output round trip."""
        from runtime.orchestrator.context import ExecutionContext
        ctx = ExecutionContext(run_id="r1")
        ctx.set_output("n0", {"ok": True, "result": "pass"})
        out = ctx.get_output("n0")
        assert out is not None
        assert out["ok"] is True
        assert out["result"] == "pass"

    def test_get_output_missing(self):
        """get_output for unknown node returns None."""
        from runtime.orchestrator.context import ExecutionContext
        ctx = ExecutionContext(run_id="r1")
        assert ctx.get_output("nonexistent") is None

    def test_set_output_with_meta(self):
        """set_output should optionally store metadata."""
        from runtime.orchestrator.context import ExecutionContext
        ctx = ExecutionContext(run_id="r1")
        ctx.set_output("n0", {"ok": True}, meta={"degraded": True, "latency_ms": 150})
        assert ctx.get_meta("n0") == {"degraded": True, "latency_ms": 150}

    def test_get_meta_missing(self):
        """get_meta for unknown node returns None."""
        from runtime.orchestrator.context import ExecutionContext
        ctx = ExecutionContext(run_id="r1")
        assert ctx.get_meta("nonexistent") is None

    def test_is_degraded_true(self):
        """is_degraded should return True when node ran degraded."""
        from runtime.orchestrator.context import ExecutionContext
        ctx = ExecutionContext(run_id="r1")
        ctx.set_output("n0", {"ok": True}, meta={"degraded": True})
        assert ctx.is_degraded("n0") is True

    def test_is_degraded_false(self):
        """is_degraded should return False for healthy node."""
        from runtime.orchestrator.context import ExecutionContext
        ctx = ExecutionContext(run_id="r1")
        ctx.set_output("n0", {"ok": True}, meta={"degraded": False})
        assert ctx.is_degraded("n0") is False

    def test_is_degraded_no_meta(self):
        """is_degraded should return False when no meta."""
        from runtime.orchestrator.context import ExecutionContext
        ctx = ExecutionContext(run_id="r1")
        ctx.set_output("n0", {"ok": True})
        assert ctx.is_degraded("n0") is False

    def test_has_any_degraded(self):
        """has_any_degraded should detect any degraded node."""
        from runtime.orchestrator.context import ExecutionContext
        ctx = ExecutionContext(run_id="r1")
        ctx.set_output("n0", {"ok": True})
        ctx.set_output("n1", {"ok": True}, meta={"degraded": True})
        assert ctx.has_any_degraded() is True

    def test_has_any_degraded_none(self):
        """has_any_degraded should return False when all healthy."""
        from runtime.orchestrator.context import ExecutionContext
        ctx = ExecutionContext(run_id="r1")
        ctx.set_output("n0", {"ok": True}, meta={"degraded": False})
        assert ctx.has_any_degraded() is False

    def test_snapshot(self):
        """snapshot should return consistent (outputs, meta) copy."""
        from runtime.orchestrator.context import ExecutionContext
        ctx = ExecutionContext(run_id="r1")
        ctx.set_output("n0", {"ok": True}, meta={"latency": 100})
        ctx.set_output("n1", {"ok": False}, meta={"error": "timeout"})
        out, meta = ctx.snapshot()
        assert out["n0"]["ok"] is True
        assert meta["n1"]["error"] == "timeout"
        # snapshot returns shallow copy of outer dict; inner dicts share refs
        assert out["n0"]["ok"] is True
        assert out["n1"]["ok"] is False

    def test_concurrent_writes(self):
        """ExecutionContext should be thread-safe under concurrent writes."""
        import threading

        from runtime.orchestrator.context import ExecutionContext
        ctx = ExecutionContext(run_id="r1")

        def writer(node_id):
            for i in range(50):
                ctx.set_output(node_id, {"count": i})

        threads = [threading.Thread(target=writer, args=(f"n{i}",)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All nodes should have been written without corruption
        for i in range(4):
            out = ctx.get_output(f"n{i}")
            assert out is not None
            assert "count" in out


# ═══════════════════════════════════════════════════════════════════════════
# workflows/gates.py — smoke/regression/perf gate functions
# ═══════════════════════════════════════════════════════════════════════════

class TestGates:
    def test_smoke_gate_all_pass(self):
        """Smoke gate with 100% pass rate should PASS."""
        from runtime.orchestrator.workflows.gates import GateResult, check_smoke_gate
        result = check_smoke_gate(p0_total=10, p0_passed=10)
        assert result == GateResult.PASS

    def test_smoke_gate_below_threshold(self):
        """Smoke gate below 95% should BLOCK."""
        from runtime.orchestrator.workflows.gates import GateResult, check_smoke_gate
        result = check_smoke_gate(p0_total=10, p0_passed=9)
        assert result == GateResult.BLOCK

    def test_smoke_gate_custom_threshold(self):
        """Smoke gate with custom threshold."""
        from runtime.orchestrator.workflows.gates import GateResult, check_smoke_gate
        result = check_smoke_gate(p0_total=10, p0_passed=7, threshold=0.70)
        assert result == GateResult.PASS

    def test_smoke_gate_new_p0_bug_blocks(self):
        """Smoke gate with new P0 bugs should BLOCK regardless of rate."""
        from runtime.orchestrator.workflows.gates import GateResult, check_smoke_gate
        result = check_smoke_gate(p0_total=10, p0_passed=10, new_p0_bugs=1)
        assert result == GateResult.BLOCK

    def test_smoke_gate_zero_total_blocks(self):
        """Smoke gate with zero tests should BLOCK."""
        from runtime.orchestrator.workflows.gates import GateResult, check_smoke_gate
        result = check_smoke_gate(p0_total=0)
        assert result == GateResult.BLOCK

    def test_regression_gate_pass(self):
        """Regression gate at 90% should PASS."""
        from runtime.orchestrator.workflows.gates import GateResult, check_regression_gate
        result = check_regression_gate(total=100, passed=90, failed=10)
        assert result == GateResult.PASS

    def test_regression_gate_below_threshold(self):
        """Regression gate below 90% should BLOCK."""
        from runtime.orchestrator.workflows.gates import GateResult, check_regression_gate
        result = check_regression_gate(total=100, passed=89, failed=11)
        assert result == GateResult.BLOCK

    def test_regression_gate_zero_total(self):
        """Regression gate with zero tests should BLOCK."""
        from runtime.orchestrator.workflows.gates import GateResult, check_regression_gate
        result = check_regression_gate(total=0)
        assert result == GateResult.BLOCK

    def test_perf_gate_ci_quick_pass(self):
        """Perf gate in ci_quick mode should PASS at 200ms avg."""
        from runtime.orchestrator.workflows.gates import GateResult, check_perf_gate
        result = check_perf_gate(avg_response_ms=200, p95_response_ms=500)
        assert result == GateResult.PASS

    def test_perf_gate_ci_quick_block_avg(self):
        """Perf gate should BLOCK when avg exceeds ci_quick threshold."""
        from runtime.orchestrator.workflows.gates import GateResult, check_perf_gate
        result = check_perf_gate(avg_response_ms=600, p95_response_ms=500)
        assert result == GateResult.BLOCK

    def test_perf_gate_ci_quick_block_p95(self):
        """Perf gate should BLOCK when p95 exceeds ci_quick threshold."""
        from runtime.orchestrator.workflows.gates import GateResult, check_perf_gate
        result = check_perf_gate(avg_response_ms=200, p95_response_ms=1100)
        assert result == GateResult.BLOCK

    def test_perf_gate_full_mode_pass(self):
        """Perf gate in full mode should allow higher thresholds."""
        from runtime.orchestrator.workflows.gates import GateResult, check_perf_gate
        result = check_perf_gate(avg_response_ms=1500, p95_response_ms=4000, mode="full")
        assert result == GateResult.PASS

    def test_perf_gate_full_mode_block_avg(self):
        """Perf gate in full mode should BLOCK above 2000ms avg."""
        from runtime.orchestrator.workflows.gates import GateResult, check_perf_gate
        result = check_perf_gate(avg_response_ms=2500, p95_response_ms=1000, mode="full")
        assert result == GateResult.BLOCK

    def test_gate_result_enum(self):
        """GateResult should have three values."""
        from runtime.orchestrator.workflows.gates import GateResult
        assert GateResult.PASS.value == "pass"
        assert GateResult.WARN.value == "warn"
        assert GateResult.BLOCK.value == "block"


# ═══════════════════════════════════════════════════════════════════════════
# release_readiness.py — score_readiness
# ═══════════════════════════════════════════════════════════════════════════

class TestReleaseReadiness:
    def test_all_gates_green(self):
        """All gates passing with no P0 bugs should be GREEN."""
        from runtime.orchestrator.release_readiness import score_readiness
        result = score_readiness(
            smoke_pass_rate=1.0,
            regression_pass_rate=1.0,
            perf_gate_ok=True,
            security_ok=True,
            p0_bug_count=0,
        )
        assert result.verdict == "GREEN"
        assert result.score >= 0.85

    def test_p0_bug_yellow_even_with_good_score(self):
        """P0 bug should force YELLOW even with good score."""
        from runtime.orchestrator.release_readiness import score_readiness
        result = score_readiness(
            smoke_pass_rate=1.0,
            regression_pass_rate=1.0,
            perf_gate_ok=True,
            security_ok=True,
            p0_bug_count=1,
        )
        assert result.verdict == "YELLOW"

    def test_p0_bug_low_score_red(self):
        """P0 bug + low score should be RED."""
        from runtime.orchestrator.release_readiness import score_readiness
        result = score_readiness(
            smoke_pass_rate=0.5,
            regression_pass_rate=0.3,
            perf_gate_ok=False,
            security_ok=False,
            p0_bug_count=3,
        )
        assert result.verdict == "RED"

    def test_score_below_60_red(self):
        """Score below 0.6 should be RED."""
        from runtime.orchestrator.release_readiness import score_readiness
        result = score_readiness(
            smoke_pass_rate=0.0,
            regression_pass_rate=0.0,
            perf_gate_ok=False,
            security_ok=False,
            p0_bug_count=0,
        )
        assert result.verdict == "RED"
        assert result.score == 0.0

    def test_score_mid_yellow(self):
        """Score between 0.6-0.85 with no P0 bugs should be YELLOW.
        0.9×0.4 + 0.9×0.3 + 0×0.2 + 0×0.1 = 0.36+0.27 = 0.63."""
        from runtime.orchestrator.release_readiness import score_readiness
        result = score_readiness(
            smoke_pass_rate=0.9,
            regression_pass_rate=0.9,
            perf_gate_ok=False,
            security_ok=False,
            p0_bug_count=0,
        )
        assert result.verdict == "YELLOW"
        assert 0.6 <= result.score < 0.85

    def test_breakdown_keys(self):
        """Breakdown should contain all four dimensions."""
        from runtime.orchestrator.release_readiness import score_readiness
        result = score_readiness(1.0, 1.0, True, True, 0)
        assert set(result.breakdown.keys()) == {"smoke", "regression", "performance", "security"}

    def test_weights_sum_to_one(self):
        """Weighted dimensions should sum to total score."""
        from runtime.orchestrator.release_readiness import score_readiness
        result = score_readiness(1.0, 1.0, True, True, 0)
        breakdown_sum = sum(result.breakdown.values())
        assert abs(breakdown_sum - result.score) < 0.01

    def test_score_from_run_summary(self):
        """score_from_run_summary should extract fields from dict."""
        from runtime.orchestrator.release_readiness import score_from_run_summary
        summary = {
            "total": 100,
            "succeeded": 95,
            "perf_gate": True,
            "security_ok": True,
            "p0_bug_count": 0,
        }
        result = score_from_run_summary(summary)
        assert result.verdict == "GREEN"

    def test_score_from_run_summary_alternate_keys(self):
        """score_from_run_summary should accept alternate key names."""
        from runtime.orchestrator.release_readiness import score_from_run_summary
        summary = {
            "total": 100,
            "passed": 80,
            "performance_ok": True,
            "security_gate": False,
            "p0_bugs": 0,
        }
        result = score_from_run_summary(summary)
        assert 0.7 <= result.score < 0.9


# ═══════════════════════════════════════════════════════════════════════════
# metrics/parser.py — parse_junit, parse_jmeter_jtl, extract_metrics
# ═══════════════════════════════════════════════════════════════════════════

class TestMetricsParser:
    def test_parse_junit_basic(self):
        """parse_junit should extract counts from valid XML."""
        from runtime.orchestrator.metrics.parser import parse_junit
        xml = (
            '<testsuite name="pytest" tests="100" failures="2" errors="1" skipped="5" time="12.3">'
            "</testsuite>"
        )
        result = parse_junit(xml)
        assert result["total"] == 100
        assert result["passed"] == 92  # 100-2-1-5
        assert result["failed"] == 3    # 2+1
        assert result["skipped"] == 5
        assert result["errors"] == 1
        assert abs(result["rate"] - 0.92) < 0.01

    def test_parse_junit_all_passing(self):
        """parse_junit with all passing tests."""
        from runtime.orchestrator.metrics.parser import parse_junit
        xml = '<testsuite tests="50" failures="0" errors="0" skipped="0"/>'
        result = parse_junit(xml)
        assert result["total"] == 50
        assert result["passed"] == 50
        assert result["rate"] == 1.0

    def test_parse_junit_zero_tests(self):
        """parse_junit with zero tests should not divide by zero."""
        from runtime.orchestrator.metrics.parser import parse_junit
        xml = '<testsuite tests="0" failures="0" errors="0" skipped="0"/>'
        result = parse_junit(xml)
        assert result["rate"] == 0.0
        assert result["total"] == 0

    def test_parse_junit_invalid_xml(self):
        """parse_junit with invalid XML should return empty dict."""
        from runtime.orchestrator.metrics.parser import parse_junit
        result = parse_junit("not valid xml <<<")
        assert result == {}

    def test_parse_jmeter_jtl_basic(self):
        """parse_jmeter_jtl should extract latency stats."""
        from runtime.orchestrator.metrics.parser import parse_jmeter_jtl
        csv_text = (
            "timeStamp,elapsed,label,responseCode,responseMessage,success\n"
            "1000,150,Login,200,OK,true\n"
            "1001,200,Login,200,OK,true\n"
            "1002,250,Login,200,OK,true\n"
            "1003,100,Login,200,OK,true\n"
            "1004,300,Login,500,Error,false\n"
        )
        result = parse_jmeter_jtl(csv_text)
        assert result["samples"] == 5
        assert result["failures"] == 1
        assert result["min_ms"] == 100
        assert result["max_ms"] == 300
        assert result["rate"] == 0.8

    def test_parse_jmeter_jtl_empty(self):
        """parse_jmeter_jtl with no data lines should return zeros."""
        from runtime.orchestrator.metrics.parser import parse_jmeter_jtl
        result = parse_jmeter_jtl("timeStamp,elapsed,success\n")
        assert result["samples"] == 0
        assert result["rate"] == 0.0

    def test_parse_jmeter_jtl_missing_columns(self):
        """parse_jmeter_jtl with missing required columns should return empty."""
        from runtime.orchestrator.metrics.parser import parse_jmeter_jtl
        result = parse_jmeter_jtl("label,status\nlogin,ok\n")
        assert result == {}

    def test_parse_jmeter_jtl_corrupt_line(self):
        """parse_jmeter_jtl should handle corrupt elapsed values."""
        from runtime.orchestrator.metrics.parser import parse_jmeter_jtl
        csv_text = (
            "timeStamp,elapsed,success\n"
            "1000,crap,true\n"
            "1001,200,true\n"
        )
        result = parse_jmeter_jtl(csv_text)
        assert result["samples"] == 1  # only the valid line
        assert result["avg_ms"] == 200

    def test_extract_metrics_junit_from_outcome(self):
        """extract_metrics should detect junit by kind or content."""
        from runtime.orchestrator.metrics.parser import extract_metrics
        outcome = {
            "kind": "junit",
            "stdout": '<testsuite tests="10" failures="0" errors="0" skipped="0"/>',
        }
        result = extract_metrics(outcome)
        assert result.get("total") == 10

    def test_extract_metrics_jmeter_from_outcome(self):
        """extract_metrics should detect jmeter by kind or content."""
        from runtime.orchestrator.metrics.parser import extract_metrics
        outcome = {
            "kind": "jmeter",
            "stdout": "timeStamp,elapsed,success\n1000,150,true\n1001,200,true\n",
        }
        result = extract_metrics(outcome)
        assert result.get("samples") == 2

    def test_extract_metrics_empty_stdout(self):
        """extract_metrics with empty stdout should return empty dict."""
        from runtime.orchestrator.metrics.parser import extract_metrics
        result = extract_metrics({"stdout": ""})
        assert result == {}

    def test_extract_metrics_unrecognized(self):
        """extract_metrics with unrecognized format should return empty."""
        from runtime.orchestrator.metrics.parser import extract_metrics
        result = extract_metrics({"stdout": "some random output"})
        assert result == {}

    def test_extract_metrics_auto_detect_junit(self):
        """extract_metrics should auto-detect junit by <testsuite tag."""
        from runtime.orchestrator.metrics.parser import extract_metrics
        outcome = {
            "stdout": '<testsuite tests="5" failures="1" errors="0" skipped="0"/>',
        }
        result = extract_metrics(outcome)
        assert result.get("total") == 5

    def test_extract_metrics_auto_detect_jmeter(self):
        """extract_metrics should auto-detect jmeter by header."""
        from runtime.orchestrator.metrics.parser import extract_metrics
        outcome = {
            "stdout": "timeStamp,elapsed,label,success\n1000,100,test,true\n",
        }
        result = extract_metrics(outcome)
        assert result.get("samples") == 1


# ═══════════════════════════════════════════════════════════════════════════
# flows.py — circuit breaker accounting
# ═══════════════════════════════════════════════════════════════════════════


class TestMarkUnrunNodes:
    def test_unrun_nodes_after_breaker_marked_skipped(self):
        from runtime.orchestrator.flows import _mark_unrun_nodes

        ordered = [
            type("N", (), {"id": "n0"})(),
            type("N", (), {"id": "n1"})(),
            type("N", (), {"id": "n2"})(),
        ]
        results = {"n0": {"ok": True}}
        skipped: list[str] = []
        _mark_unrun_nodes(ordered, results, skipped)
        assert skipped == ["n1", "n2"]

    def test_all_nodes_executed_marks_nothing(self):
        from runtime.orchestrator.flows import _mark_unrun_nodes

        ordered = [type("N", (), {"id": "n0"})()]
        results = {"n0": {"ok": True}}
        skipped: list[str] = ["pre-existing"]
        _mark_unrun_nodes(ordered, results, skipped)
        assert skipped == ["pre-existing"]
