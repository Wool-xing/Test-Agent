# SPDX-License-Identifier: MIT
"""Unit tests for absentee_scenario_injector.py — Phase 3.3 缺席者场景注入."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_utils_dir = Path(__file__).resolve().parents[2] / "utils"
if str(_utils_dir) not in sys.path:
    sys.path.insert(0, str(_utils_dir))


# ═══════════════════════════════════════════════════════════════
# Group listing tests
# ═══════════════════════════════════════════════════════════════

class TestListGroups:
    def test_all_9_groups_present(self):
        from absentee_scenario_injector import list_groups
        groups = list_groups()
        assert len(groups) == 9

    def test_each_group_has_label(self):
        from absentee_scenario_injector import list_groups
        for g in list_groups():
            assert g["id"]
            assert g["label"]
            assert g["scenario_count"] > 0


# ═══════════════════════════════════════════════════════════════
# Scenario query tests
# ═══════════════════════════════════════════════════════════════

class TestQueryScenarios:
    def test_query_all_returns_all(self):
        from absentee_scenario_injector import SCENARIOS, query_scenarios
        assert len(query_scenarios()) == len(SCENARIOS)

    def test_query_by_group(self):
        from absentee_scenario_injector import query_scenarios
        results = query_scenarios(groups=["visual_impairment"])
        assert len(results) >= 3
        assert all(s.group == "visual_impairment" for s in results)

    def test_query_by_severity(self):
        from absentee_scenario_injector import query_scenarios
        results = query_scenarios(severity="P0")
        assert len(results) > 0
        assert all(s.severity == "P0" for s in results)

    def test_query_by_tags(self):
        from absentee_scenario_injector import query_scenarios
        results = query_scenarios(tags=["screen-reader"])
        assert len(results) >= 1
        assert any("screen-reader" in s.tags for s in results)

    def test_query_combined(self):
        from absentee_scenario_injector import query_scenarios
        results = query_scenarios(groups=["visual_impairment"], severity="P0")
        assert all(s.group == "visual_impairment" and s.severity == "P0" for s in results)

    def test_query_empty_group(self):
        from absentee_scenario_injector import query_scenarios
        results = query_scenarios(groups=["nonexistent_group"])
        assert len(results) == 0


# ═══════════════════════════════════════════════════════════════
# Scenario injection tests
# ═══════════════════════════════════════════════════════════════

class TestInjectScenarios:
    def test_inject_all(self):
        from absentee_scenario_injector import SCENARIOS, inject_scenarios
        results = inject_scenarios()
        # Default min_severity=P2 includes all
        assert len(results) == len(SCENARIOS)

    def test_inject_p0_only(self):
        from absentee_scenario_injector import inject_scenarios
        results = inject_scenarios(min_severity="P0")
        assert all(s["severity"] == "P0" for s in results)

    def test_inject_with_count_limit(self):
        from absentee_scenario_injector import inject_scenarios
        results = inject_scenarios(count=5)
        assert len(results) == 5

    def test_inject_specific_group(self):
        from absentee_scenario_injector import inject_scenarios
        results = inject_scenarios(groups=["mental_crisis"])
        assert len(results) >= 3
        assert all(s["group"] == "mental_crisis" for s in results)

    def test_injected_has_required_fields(self):
        from absentee_scenario_injector import inject_scenarios
        results = inject_scenarios(count=1)
        s = results[0]
        for field in ["id", "group", "severity", "title", "description", "test_steps", "expected"]:
            assert field in s, f"Missing field: {field}"
        assert isinstance(s["test_steps"], list)
        assert len(s["test_steps"]) > 0


# ═══════════════════════════════════════════════════════════════
# Charter generation tests
# ═══════════════════════════════════════════════════════════════

class TestGenerateCharter:
    def test_generates_markdown(self):
        from absentee_scenario_injector import generate_charter, query_scenarios
        scenarios = query_scenarios(groups=["visual_impairment"], severity="P0")
        charter = generate_charter(scenarios[0], module="login", duration_min=45)
        assert "# Charter:" in charter
        assert "login" in charter
        assert "视觉障碍" in charter
        assert "## 测试步骤" in charter
        assert "## 预期结果" in charter

    def test_batch_generates_files(self, tmp_path):
        from absentee_scenario_injector import generate_batch_charters
        paths = generate_batch_charters(
            groups=["mental_crisis"], severity="P0",
            output_dir=str(tmp_path),
        )
        assert len(paths) >= 3
        for p in paths:
            assert Path(p).exists()
            content = Path(p).read_text(encoding="utf-8")
            assert "mental_crisis" in content.lower() or "MC-" in content


# ═══════════════════════════════════════════════════════════════
# Coverage report tests
# ═══════════════════════════════════════════════════════════════

class TestCoverageReport:
    def test_full_coverage(self):
        from absentee_scenario_injector import coverage_report, inject_scenarios
        scenarios = inject_scenarios()
        report = coverage_report(scenarios)
        assert report["total_absentee_groups"] == 9
        assert report["coverage_pct"] == 100.0
        assert len(report["groups_missing"]) == 0

    def test_partial_coverage(self):
        from absentee_scenario_injector import coverage_report, inject_scenarios
        scenarios = inject_scenarios(groups=["visual_impairment", "elderly"])
        report = coverage_report(scenarios)
        assert report["groups_covered"] == 2
        assert report["coverage_pct"] < 100.0
        assert len(report["groups_missing"]) == 7

    def test_empty_coverage(self):
        from absentee_scenario_injector import coverage_report
        report = coverage_report([])
        assert report["groups_covered"] == 0
        assert report["coverage_pct"] == 0.0


# ═══════════════════════════════════════════════════════════════
# Export tests
# ═══════════════════════════════════════════════════════════════

class TestExport:
    def test_export_json(self, tmp_path):
        from absentee_scenario_injector import export_injection_plan, inject_scenarios
        scenarios = inject_scenarios(groups=["elderly"])
        path = export_injection_plan(scenarios, output_dir=str(tmp_path))
        assert Path(path).exists()
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert data["total_scenarios"] > 0
        assert "coverage" in data

    def test_ci_summary(self):
        from absentee_scenario_injector import ci_summary, inject_scenarios
        scenarios = inject_scenarios(groups=["visual_impairment", "mental_crisis"])
        text = ci_summary(scenarios)
        assert "visual_impairment" in text or "视觉" in text
        assert "mental_crisis" in text or "精神" in text
