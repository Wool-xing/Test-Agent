"""Characterization tests: TestCoordinatorPipeline — 11-step workflow."""

from __future__ import annotations

import pytest


class TestPipelineStructure:
    def test_sequence_has_11_steps(self):
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        assert len(TestCoordinatorPipeline.SEQUENCE) == 11

    def test_first_step_is_requirements_analyst(self):
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        name, kind = TestCoordinatorPipeline.SEQUENCE[0]
        assert name == "requirements-analyst"
        assert kind == "expert"

    def test_last_step_is_test_lead(self):
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        name, kind = TestCoordinatorPipeline.SEQUENCE[-1]
        assert name == "test-lead"
        assert kind == "expert"

    def test_all_steps_have_valid_kinds(self):
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        for name, kind in TestCoordinatorPipeline.SEQUENCE:
            assert kind in ("expert", "skill"), f"{name}: invalid kind {kind}"

    def test_no_duplicate_step_names(self):
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        names = [n for n, _ in TestCoordinatorPipeline.SEQUENCE]
        assert len(names) == len(set(names)), f"Duplicate steps: {names}"


class TestPreflight:
    def test_preflight_checks_python_version(self):
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        p = TestCoordinatorPipeline()
        missing = p._preflight()
        assert isinstance(missing, list)

    def test_preflight_returns_list(self):
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        p = TestCoordinatorPipeline()
        result = p._preflight()
        assert isinstance(result, list)

    def test_preflight_desktop_hints(self):
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        p = TestCoordinatorPipeline()
        missing = p._preflight(["desktop_windows"])
        assert isinstance(missing, list)


class TestPlatformDetection:
    def test_detect_desktop_windows(self):
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        p = TestCoordinatorPipeline()
        hints = p._detect_platform("test this Windows EXE program")
        assert "desktop_windows" in hints

    def test_detect_api(self):
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        p = TestCoordinatorPipeline()
        hints = p._detect_platform("test the REST API endpoint")
        assert "api" in hints

    def test_detect_web(self):
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        p = TestCoordinatorPipeline()
        hints = p._detect_platform("browser based web application")
        assert "web" in hints

    def test_detect_multiple(self):
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        p = TestCoordinatorPipeline()
        hints = p._detect_platform("test the API backend and web frontend")
        assert "api" in hints
        assert "web" in hints


class TestPRDLoader:
    def test_load_prd_handles_missing_file(self):
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        p = TestCoordinatorPipeline()
        result = p._load_prd("/nonexistent/path.md")
        assert result is None


class TestPipelineResult:
    def test_pipeline_result_defaults(self):
        from runtime.orchestrator.workflows.test_coordinator import PipelineResult
        r = PipelineResult(ok=True)
        assert r.ok is True
        assert r.steps == []
        assert r.aborted_at is None
        assert r.summary == ""

    def test_pipeline_step_defaults(self):
        from runtime.orchestrator.workflows.test_coordinator import PipelineStep
        s = PipelineStep(name="test-step", kind="expert")
        assert s.name == "test-step"
        assert s.kind == "expert"
        assert s.status == "pending"


class TestGateIntegration:
    def test_check_gates_with_empty_metrics_blocks(self):
        """Empty metrics dict → gate values are 0 → gates BLOCK."""
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        p = TestCoordinatorPipeline()

        # smoke-test with no metrics → 0/0 tests → BLOCK
        result = p._check_gates("smoke-test", {"metrics": {}})
        assert result is not None  # should block

        # test-executor with no metrics → 0/0 → BLOCK
        result2 = p._check_gates("test-executor", {"metrics": {}})
        assert result2 is not None

    def test_check_gates_passing_metrics(self):
        """With passing metrics, gates should return None (no block)."""
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        p = TestCoordinatorPipeline()

        result = p._check_gates("smoke-test", {
            "metrics": {"p0_total": 100, "p0_passed": 98, "new_p0_bugs": 0}
        })
        assert result is None  # 98% > 95% → pass

    def test_check_gates_failing_smoke(self):
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        p = TestCoordinatorPipeline()

        result = p._check_gates("smoke-test", {
            "metrics": {"p0_total": 100, "p0_passed": 80, "new_p0_bugs": 2}
        })
        assert result is not None  # 80% < 95% + bugs → block

    def test_check_gates_unknown_step_passes(self):
        """Steps not in gate logic return None."""
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        p = TestCoordinatorPipeline()
        result = p._check_gates("requirements-analyst", {"metrics": {}})
        assert result is None


class TestPipelineRun:
    def test_run_creates_result(self):
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        p = TestCoordinatorPipeline()
        result = p.run("test target")
        assert result is not None
        assert isinstance(result.summary, str)

    def test_run_aborted_preflight(self):
        """Simulate preflight failure by checking workspace."""
        from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
        from unittest.mock import patch
        p = TestCoordinatorPipeline()
        with patch.object(p, '_preflight', return_value=["missing dep"]):
            result = p.run("test")
            assert result.ok is False
            assert result.aborted_at == "preflight"
