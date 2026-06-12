# SPDX-License-Identifier: MIT
"""Unit tests for ci_quality_gate.py and quality_gate_engine.py."""

from __future__ import annotations

import json
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

# utils package installed via pip install -e runtime/


# ── ci_quality_gate tests ──────────────────────────────────────────────

class TestParseJunit:
    def make_junit_xml(self, tests: int, failures: int, errors: int, skipped: int) -> str:
        root = ET.Element("testsuite", {
            "tests": str(tests),
            "failures": str(failures),
            "errors": str(errors),
            "skipped": str(skipped),
        })
        return ET.tostring(root, encoding="unicode")

    def test_all_pass(self):
        from utils.quality.ci_quality_gate import parse_junit
        with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
            f.write(self.make_junit_xml(100, 0, 0, 0))
            path = f.name
        try:
            result = parse_junit(path)
            assert result is not None
            assert result["total"] == 100
            assert result["passed"] == 100
            assert result["pass_rate_pct"] == 100.0
        finally:
            Path(path).unlink()

    def test_mixed_failures(self):
        from utils.quality.ci_quality_gate import parse_junit
        with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
            f.write(self.make_junit_xml(50, 5, 2, 3))
            path = f.name
        try:
            result = parse_junit(path)
            assert result is not None
            assert result["total"] == 50
            assert result["failed"] == 7
            assert result["skipped"] == 3
            assert result["passed"] == 40
            assert result["pass_rate_pct"] == 80.0
        finally:
            Path(path).unlink()

    def test_missing_file(self):
        from utils.quality.ci_quality_gate import parse_junit
        assert parse_junit("/nonexistent/path.xml") is None

    def test_empty_file(self):
        from utils.quality.ci_quality_gate import parse_junit
        with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
            f.write("not xml")
            path = f.name
        try:
            result = parse_junit(path)
            assert result is None
        finally:
            Path(path).unlink()


class TestCheckSmoke:
    def test_pass(self):
        import utils.quality.ci_quality_gate as m
        from utils.quality.ci_quality_gate import check_smoke
        m.GATES["smoke"]["min_pass_rate_pct"] = 95

        with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
            root = ET.Element("testsuite", {"tests": "100", "failures": "3", "errors": "1", "skipped": "1"})
            f.write(ET.tostring(root, encoding="unicode"))
            path = f.name
        try:
            ok, msg = check_smoke(path)
            assert ok
            assert "95" in msg
        finally:
            Path(path).unlink()

    def test_fail_below_threshold(self):
        import utils.quality.ci_quality_gate as m
        from utils.quality.ci_quality_gate import check_smoke
        m.GATES["smoke"]["min_pass_rate_pct"] = 95

        with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
            root = ET.Element("testsuite", {"tests": "100", "failures": "10", "errors": "5", "skipped": "0"})
            f.write(ET.tostring(root, encoding="unicode"))
            path = f.name
        try:
            ok, msg = check_smoke(path)
            assert not ok
        finally:
            Path(path).unlink()


class TestCheckCoverage:
    def make_coverage_xml(self, line_rate: float) -> str:
        root = ET.Element("coverage", {"line-rate": str(line_rate)})
        return ET.tostring(root, encoding="unicode")

    def test_pass_above_threshold(self):
        from utils.quality.ci_quality_gate import check_coverage
        with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
            f.write(self.make_coverage_xml(0.85))
            path = f.name
        try:
            ok, msg = check_coverage(path, threshold=80.0)
            assert ok
        finally:
            Path(path).unlink()

    def test_fail_below_threshold(self):
        from utils.quality.ci_quality_gate import check_coverage
        with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
            f.write(self.make_coverage_xml(0.55))
            path = f.name
        try:
            ok, msg = check_coverage(path, threshold=80.0)
            assert not ok
        finally:
            Path(path).unlink()


# ── quality_gate_engine tests ─────────────────────────────────────────

class TestQualityGateEngine:
    def test_builtin_defaults_load(self):
        from utils.quality.quality_gate_engine import _builtin_defaults
        cfg = _builtin_defaults()
        assert "smoke" in cfg
        assert cfg["smoke"]["min_pass_rate_pct"] == 95
        assert cfg["regression"]["min_coverage_pct"] == 80
        assert cfg["performance_full"]["min_tps"] == 100

    def test_engine_init_default(self):
        from utils.quality.quality_gate_engine import QualityGateEngine
        engine = QualityGateEngine(config_path="/nonexistent/config.yaml")
        assert "smoke" in engine.config

    def test_engine_smoke_pass(self):
        from utils.quality.quality_gate_engine import QualityGateEngine
        engine = QualityGateEngine(config_path="/nonexistent/config.yaml")
        engine.config["smoke"]["min_pass_rate_pct"] = 90

        with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
            root = ET.Element("testsuite", {"tests": "100", "failures": "5", "errors": "0", "skipped": "0"})
            f.write(ET.tostring(root, encoding="unicode"))
            path = f.name
        try:
            ok, msg = engine.check_smoke(path)
            assert ok
        finally:
            Path(path).unlink()

    def test_engine_smoke_fail(self):
        from utils.quality.quality_gate_engine import QualityGateEngine
        engine = QualityGateEngine(config_path="/nonexistent/config.yaml")
        engine.config["smoke"]["min_pass_rate_pct"] = 95

        with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
            root = ET.Element("testsuite", {"tests": "100", "failures": "40", "errors": "0", "skipped": "0"})
            f.write(ET.tostring(root, encoding="unicode"))
            path = f.name
        try:
            ok, msg = engine.check_smoke(path)
            assert not ok
        finally:
            Path(path).unlink()

    def test_engine_coverage(self):
        from utils.quality.quality_gate_engine import QualityGateEngine
        engine = QualityGateEngine(config_path="/nonexistent/config.yaml")

        with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
            root = ET.Element("coverage", {"line-rate": "0.92"})
            f.write(ET.tostring(root, encoding="unicode"))
            path = f.name
        try:
            ok, msg = engine.check_coverage(path)
            assert ok
        finally:
            Path(path).unlink()

    def test_engine_release_missing_gates(self):
        from utils.quality.quality_gate_engine import QualityGateEngine
        engine = QualityGateEngine(config_path="/nonexistent/config.yaml")
        ok, msg = engine.check_release()
        assert not ok
        assert "smoke" in msg.lower()

    def test_engine_release_all_pass(self):
        from utils.quality.quality_gate_engine import QualityGateEngine
        engine = QualityGateEngine(config_path="/nonexistent/config.yaml")
        engine.config["release"]["require_smoke"] = False
        engine.config["release"]["require_regression"] = False
        engine.config["release"]["require_perf_full"] = False
        ok, msg = engine.check_release()
        assert ok

    def test_engine_summary_json(self):
        from utils.quality.quality_gate_engine import QualityGateEngine
        engine = QualityGateEngine(config_path="/nonexistent/config.yaml")
        engine._record("smoke", True, "ok")
        data = engine.summary_json()
        assert data["overall_pass"] is True

    def test_engine_performance_parse(self):
        from utils.quality.quality_gate_engine import QualityGateEngine
        engine = QualityGateEngine(config_path="/nonexistent/config.yaml")
        engine.config["performance_ci_quick"] = {
            "min_tps": 20, "max_p95_ms": 800, "max_avg_ms": 400, "max_error_pct": 1.0
        }

        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump({"tps": 30, "p95_ms": 400, "avg_ms": 200, "error_pct": 0.5}, f)
            path = f.name
        try:
            ok, msg = engine.check_performance(path, mode="ci_quick")
            assert ok
        finally:
            Path(path).unlink()
