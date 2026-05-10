"""
CI 质量门禁统一检查工具
被引用方：06-CICD/github-actions-test.yml / jenkins-pipeline.groovy
取代原 CI 内联 Python 脚本（消除三重重复）。
"""
import json
import logging
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def parse_junit(xml_path: str) -> Optional[Dict]:
    """解析 junit-xml，兼容 testsuite 单根 与 testsuites 多根。返回总数/通过/失败/跳过。"""
    p = Path(xml_path)
    if not p.exists():
        return None
    try:
        root = ET.parse(p).getroot()
    except Exception as e:
        logger.error(f"junit-xml 解析失败 {xml_path}: {e}")
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


# ===== 门禁定义 =====

GATES = {
    "smoke": {"min_pass_rate_pct": 95},
    "regression_p0_p1": {"min_pass_rate_pct": 90},  # 整体 P0+P1 通过率
    "coverage": {"min_pct": 80},
}


def check_smoke(xml_path: str) -> Tuple[bool, str]:
    res = parse_junit(xml_path)
    if res is None:
        return False, f"junit 文件不存在: {xml_path}"
    rate = res["pass_rate_pct"]
    ok = rate >= GATES["smoke"]["min_pass_rate_pct"]
    msg = f"冒烟通过率 {rate}% ({res['passed']}/{res['total']}) 要求 ≥{GATES['smoke']['min_pass_rate_pct']}%"
    return ok, msg


def check_regression(xml_path: str) -> Tuple[bool, str]:
    res = parse_junit(xml_path)
    if res is None:
        return False, f"junit 文件不存在: {xml_path}"
    rate = res["pass_rate_pct"]
    ok = rate >= GATES["regression_p0_p1"]["min_pass_rate_pct"]
    msg = f"回归通过率 {rate}% ({res['passed']}/{res['total']}) 要求 ≥{GATES['regression_p0_p1']['min_pass_rate_pct']}%"
    return ok, msg


def check_coverage(coverage_xml: str, threshold: float = 80.0) -> Tuple[bool, str]:
    """解析 coverage.xml（Cobertura 格式）的 line-rate"""
    p = Path(coverage_xml)
    if not p.exists():
        return False, f"coverage.xml 不存在: {coverage_xml}"
    try:
        root = ET.parse(p).getroot()
        line_rate = float(root.attrib.get("line-rate", 0)) * 100
    except Exception as e:
        return False, f"coverage 解析失败: {e}"
    ok = line_rate >= threshold
    return ok, f"覆盖率 {line_rate:.1f}% 要求 ≥{threshold}%"


def main():
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="CI 质量门禁统一检查")
    parser.add_argument("--smoke-xml", help="冒烟 junit xml 路径")
    parser.add_argument("--regression-xml", help="回归 junit xml 路径")
    parser.add_argument("--coverage-xml", help="coverage.xml 路径（Cobertura）")
    parser.add_argument("--coverage-threshold", type=float, default=80.0)
    parser.add_argument("--output-json", help="结果写入 JSON")
    args = parser.parse_args()

    failed = False
    summary = {}

    if args.smoke_xml:
        ok, msg = check_smoke(args.smoke_xml)
        flag = "✅" if ok else "❌"
        print(f"{flag} {msg}")
        summary["smoke"] = {"pass": ok, "message": msg}
        if not ok:
            failed = True

    if args.regression_xml:
        ok, msg = check_regression(args.regression_xml)
        flag = "✅" if ok else "❌"
        print(f"{flag} {msg}")
        summary["regression"] = {"pass": ok, "message": msg}
        if not ok:
            failed = True

    if args.coverage_xml:
        ok, msg = check_coverage(args.coverage_xml, args.coverage_threshold)
        flag = "✅" if ok else "❌"
        print(f"{flag} {msg}")
        summary["coverage"] = {"pass": ok, "message": msg}
        if not ok:
            failed = True

    if args.output_json:
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump({"overall_pass": not failed, "details": summary}, f, indent=2, ensure_ascii=False)

    if failed:
        print("❌ 质量门禁未通过")
        sys.exit(1)
    print("✅ 全部质量门禁通过")


if __name__ == "__main__":
    main()
