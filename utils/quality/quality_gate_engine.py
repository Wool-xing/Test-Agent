# SPDX-License-Identifier: MIT
"""Quality Gate Engine — YAML-driven gate checker.

Replaces hardcoded GATES dict in ci_quality_gate.py with YAML-configurable
thresholds. Users edit the YAML, not the code.

默认配置文件: config/quality_gates.yaml
可通过 QUALITY_GATE_CONFIG 环境变量覆盖路径。
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

try:
    import defusedxml.ElementTree as ET  # type: ignore[import-untyped]
except ImportError:
    raise ImportError(
        "defusedxml is required for secure XML parsing. Install with: pip install defusedxml"
    )

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "quality_gates.yaml"


def _load_yaml_config(path: str | Path) -> dict[str, Any]:
    """Load YAML config. Requires PyYAML."""
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML 未安装，使用内置默认门禁阈值。pip install pyyaml")
        return _builtin_defaults()

    p = Path(path)
    if not p.exists():
        logger.warning("质量门禁配置文件不存在: %s，使用内置默认值", p)
        return _builtin_defaults()

    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f) or _builtin_defaults()


def _builtin_defaults() -> dict[str, Any]:
    return {
        "smoke": {"min_pass_rate_pct": 95},
        "regression": {"min_pass_rate_pct": 90, "min_coverage_pct": 80, "max_flaky_pct": 5},
        "performance_ci_quick": {"min_tps": 20, "max_p95_ms": 800, "max_avg_ms": 400, "max_error_pct": 1.0},
        "performance_full": {"min_tps": 100, "max_p95_ms": 500, "max_avg_ms": 200, "max_error_pct": 1.0, "max_baseline_regression_pct": 20},
        "release": {"require_smoke": True, "require_regression": True, "require_perf_full": False, "require_bug_review": True},
    }


class QualityGateEngine:
    """Load thresholds from YAML, evaluate gates, emit JSON/console results."""

    def __init__(self, config_path: str | Path | None = None):
        path = config_path or os.getenv("QUALITY_GATE_CONFIG", str(DEFAULT_CONFIG))
        self.config = _load_yaml_config(path)
        self.results: dict[str, dict[str, Any]] = {}

    # -- JUnit helpers --

    @staticmethod
    def parse_junit(xml_path: str) -> dict[str, Any] | None:
        p = Path(xml_path)
        if not p.exists():
            return None
        try:
            root = ET.parse(p).getroot()
        except Exception as e:
            logger.error("junit-xml 解析失败 %s: %s", xml_path, e)
            return None
        suites = [root] if root.tag == "testsuite" else root.findall(".//testsuite")
        total = failures = errors = skipped = 0
        for s in suites:
            total += int(s.attrib.get("tests", 0))
            failures += int(s.attrib.get("failures", 0))
            errors += int(s.attrib.get("errors", 0))
            skipped += int(s.attrib.get("skipped", 0))
        fail_total = failures + errors
        passed = total - fail_total - skipped
        return {
            "total": total,
            "passed": passed,
            "failed": fail_total,
            "skipped": skipped,
            "pass_rate_pct": round(passed / total * 100, 2) if total > 0 else 0,
        }

    # -- Coverage helper --

    @staticmethod
    def parse_coverage(coverage_xml: str) -> float | None:
        p = Path(coverage_xml)
        if not p.exists():
            return None
        try:
            root = ET.parse(p).getroot()
            return float(root.attrib.get("line-rate", 0)) * 100
        except Exception as e:
            logger.error("coverage 解析失败 %s: %s", coverage_xml, e)
            return None

    # -- Gate checks --

    def check_smoke(self, junit_xml: str) -> tuple[bool, str]:
        cfg = self.config.get("smoke", {})
        threshold = cfg.get("min_pass_rate_pct", 95)
        res = self.parse_junit(junit_xml)
        if res is None:
            return self._record("smoke", False, f"junit 文件不存在: {junit_xml}")
        rate = res["pass_rate_pct"]
        ok = rate >= threshold
        return self._record("smoke", ok, f"冒烟通过率 {rate}% ≥{threshold}%? {'✅' if ok else '❌'}")

    def check_regression(self, junit_xml: str) -> tuple[bool, str]:
        cfg = self.config.get("regression", {})
        threshold = cfg.get("min_pass_rate_pct", 90)
        res = self.parse_junit(junit_xml)
        if res is None:
            return self._record("regression", False, f"junit 文件不存在: {junit_xml}")
        rate = res["pass_rate_pct"]
        ok = rate >= threshold
        return self._record("regression", ok, f"回归通过率 {rate}% ≥{threshold}%? {'✅' if ok else '❌'}")

    def check_coverage(self, coverage_xml: str) -> tuple[bool, str]:
        cfg = self.config.get("regression", {})
        threshold = cfg.get("min_coverage_pct", 80)
        cov = self.parse_coverage(coverage_xml)
        if cov is None:
            return self._record("coverage", False, f"coverage.xml 不存在: {coverage_xml}")
        ok = cov >= threshold
        return self._record("coverage", ok, f"覆盖率 {cov:.1f}% ≥{threshold}%? {'✅' if ok else '❌'}")

    def check_performance(
        self, jmeter_json: str, mode: str = "ci_quick"
    ) -> tuple[bool, str]:
        """Parse JMeter result JSON and check against performance gates."""
        key = f"performance_{mode}"
        cfg = self.config.get(key, {})
        min_tps = cfg.get("min_tps", 20)
        max_p95 = cfg.get("max_p95_ms", 800)
        max_avg = cfg.get("max_avg_ms", 400)
        max_err = cfg.get("max_error_pct", 1.0)

        p = Path(jmeter_json)
        if not p.exists():
            return self._record(key, False, f"JMeter result 不存在: {jmeter_json}")

        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            return self._record(key, False, f"JMeter JSON 解析失败: {e}")

        tps = data.get("tps", 0)
        p95 = data.get("p95_ms", 9999)
        avg = data.get("avg_ms", 9999)
        err = data.get("error_pct", 100)

        checks = [
            tps >= min_tps,
            p95 <= max_p95,
            avg <= max_avg,
            err <= max_err,
        ]
        ok = all(checks)
        detail = (
            f"TPS={tps}(≥{min_tps}) "
            f"P95={p95}ms(≤{max_p95}) "
            f"AVG={avg}ms(≤{max_avg}) "
            f"ERR={err}%(≤{max_err})"
        )
        return self._record(key, ok, f"性能({mode}) {detail}? {'✅' if ok else '❌'}")

    def check_release(self) -> tuple[bool, str]:
        cfg = self.config.get("release", {})
        required = [
            ("smoke", cfg.get("require_smoke", True)),
            ("regression", cfg.get("require_regression", True)),
            ("performance_full", cfg.get("require_perf_full", False)),
        ]
        missing = [
            name for name, req in required if req and name not in self.results
        ]
        if missing:
            msg = f"Release 门禁缺少: {', '.join(missing)}"
            return self._record("release", False, msg)
        failed = [
            name for name, _ in required
            if name in self.results and not self.results[name].get("pass", True)
        ]
        if failed:
            msg = f"Release 门禁未通过: {', '.join(failed)}"
            return self._record("release", False, msg)
        return self._record("release", True, "Release 门禁全部通过 ✅")

    # -- Internal --

    def _record(self, name: str, ok: bool, message: str) -> tuple[bool, str]:
        self.results[name] = {"pass": ok, "message": message}
        return ok, message

    # -- Output --

    @property
    def all_pass(self) -> bool:
        if not self.results:
            return False
        return all(v.get("pass", False) for v in self.results.values())

    def summary_json(self, path: str | None = None) -> dict[str, Any]:
        data = {"overall_pass": self.all_pass, "details": self.results}
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        return data

    def print_summary(self) -> None:
        for name, detail in self.results.items():
            flag = "✅" if detail["pass"] else "❌"
            print(f"{flag} [{name}] {detail['message']}")
        print(f"\n{'✅ 全部门禁通过' if self.all_pass else '❌ 质量门禁未通过'}")


def main() -> None:
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Quality Gate Engine (YAML-driven)")
    parser.add_argument("--config", help="YAML 配置文件路径 (默认: config/quality_gates.yaml)")
    parser.add_argument("--smoke-xml", help="冒烟 junit xml 路径")
    parser.add_argument("--regression-xml", help="回归 junit xml 路径")
    parser.add_argument("--coverage-xml", help="coverage.xml 路径")
    parser.add_argument("--jmeter-json", help="JMeter result JSON 路径")
    parser.add_argument("--perf-mode", choices=["ci_quick", "full"], default="ci_quick")
    parser.add_argument("--release", action="store_true", help="执行 release 门禁检查")
    parser.add_argument("--output-json", help="结果写入 JSON")
    args = parser.parse_args()

    engine = QualityGateEngine(args.config)

    if args.smoke_xml:
        engine.check_smoke(args.smoke_xml)
    if args.regression_xml:
        engine.check_regression(args.regression_xml)
    if args.coverage_xml:
        engine.check_coverage(args.coverage_xml)
    if args.jmeter_json:
        engine.check_performance(args.jmeter_json, args.perf_mode)
    if args.release:
        engine.check_release()

    engine.print_summary()

    if args.output_json:
        engine.summary_json(args.output_json)

    if not engine.all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
