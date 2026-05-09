"""
JMeter JTL 结果解析与性能门禁检查
被引用方：07-test-executor / jmeter-script-gen skill / CI yml/groovy
"""
import csv
import json
import logging
import sys
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ===== JTL 解析 =====

def parse_jtl(jtl_path: str) -> Dict:
    """
    解析 JMeter JTL（CSV 格式）结果，输出性能指标汇总。
    duration 用 max(timeStamp) - min(timeStamp)（防多线程时序错乱）。
    error_rate 字段统一以 _pct 后缀，单位为百分比。
    """
    rows: List[Dict] = []
    with open(jtl_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        return {"error": "JTL 文件为空，无结果数据"}

    elapsed = sorted(int(r["elapsed"]) for r in rows)
    success = [r["success"].lower() == "true" for r in rows]
    timestamps = [int(r["timeStamp"]) for r in rows]
    duration_sec = max(1, (max(timestamps) - min(timestamps)) / 1000)

    p95_idx = min(len(elapsed) - 1, int(len(elapsed) * 0.95))
    p99_idx = min(len(elapsed) - 1, int(len(elapsed) * 0.99))
    error_count = len(rows) - sum(success)

    return {
        "total_requests": len(rows),
        "success_count": sum(success),
        "error_count": error_count,
        "error_rate_pct": round(error_count / len(rows) * 100, 2),
        "tps": round(len(rows) / duration_sec, 1),
        "avg_response_ms": round(mean(elapsed)),
        "p95_response_ms": elapsed[p95_idx],
        "p99_response_ms": elapsed[p99_idx],
        "max_response_ms": elapsed[-1],
        "duration_sec": round(duration_sec),
    }


# ===== 性能门禁 =====

DEFAULT_GATES_FULL = {
    "tps_min": 100,
    "p95_max_ms": 500,
    "avg_max_ms": 200,
    "error_rate_max_pct": 1.0,
}

# CI 快速验证门禁（5 并发场景，与完整压测分层）
DEFAULT_GATES_CI_QUICK = {
    "tps_min": 20,
    "p95_max_ms": 800,
    "avg_max_ms": 400,
    "error_rate_max_pct": 1.0,
}


def check_performance_gates(metrics: Dict, gates: Optional[Dict] = None) -> Dict:
    if gates is None:
        gates = DEFAULT_GATES_FULL
    checks = {
        "tps": {
            "actual": metrics["tps"],
            "required": f"≥{gates['tps_min']}",
            "pass": metrics["tps"] >= gates["tps_min"],
        },
        "p95": {
            "actual": metrics["p95_response_ms"],
            "required": f"≤{gates['p95_max_ms']}ms",
            "pass": metrics["p95_response_ms"] <= gates["p95_max_ms"],
        },
        "avg": {
            "actual": metrics["avg_response_ms"],
            "required": f"≤{gates['avg_max_ms']}ms",
            "pass": metrics["avg_response_ms"] <= gates["avg_max_ms"],
        },
        "error": {
            "actual_pct": metrics["error_rate_pct"],
            "required": f"<{gates['error_rate_max_pct']}%",
            "pass": metrics["error_rate_pct"] < gates["error_rate_max_pct"],
        },
    }
    overall_pass = all(v["pass"] for v in checks.values())
    return {"checks": checks, "overall": "PASS" if overall_pass else "FAIL"}


# ===== 基线对比 =====

def compare_with_baseline(metrics: Dict, baseline_path: str, regression_max_pct: float = 20.0) -> Dict:
    """与基线 JSON 对比，检测性能回归。"""
    p = Path(baseline_path)
    if not p.exists():
        return {"baseline_exists": False, "regression": None}
    baseline = json.loads(p.read_text(encoding="utf-8"))
    base_avg = baseline.get("avg_response_ms", 0)
    if base_avg <= 0:
        return {"baseline_exists": True, "regression": None, "error": "baseline avg invalid"}
    regression_pct = (metrics["avg_response_ms"] - base_avg) / base_avg * 100
    return {
        "baseline_exists": True,
        "baseline_avg_ms": base_avg,
        "current_avg_ms": metrics["avg_response_ms"],
        "regression_pct": round(regression_pct, 1),
        "is_regression": regression_pct > regression_max_pct,
    }


def update_baseline(metrics: Dict, baseline_path: str):
    p = Path(baseline_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"基线已更新：{baseline_path}")


# ===== CLI 入口（CI 调用）=====

def main():
    import argparse
    parser = argparse.ArgumentParser(description="JMeter JTL 解析 + 性能门禁")
    parser.add_argument("jtl", help="JTL 文件路径")
    parser.add_argument("--mode", choices=["full", "ci_quick"], default="full")
    parser.add_argument("--baseline", default="workspace/执行日志/baselines/perf_baseline.json")
    parser.add_argument("--update-baseline", action="store_true", help="本次结果写入基线")
    parser.add_argument("--regression-max-pct", type=float, default=20.0)
    args = parser.parse_args()

    metrics = parse_jtl(args.jtl)
    if "error" in metrics:
        print(f"❌ {metrics['error']}")
        sys.exit(1)

    gates = DEFAULT_GATES_CI_QUICK if args.mode == "ci_quick" else DEFAULT_GATES_FULL
    result = check_performance_gates(metrics, gates)
    baseline_cmp = compare_with_baseline(metrics, args.baseline, args.regression_max_pct)

    print("=== JMeter 性能测试结果 ===")
    print(f"模式：{args.mode}")
    print(f"总请求：{metrics['total_requests']}  TPS：{metrics['tps']}/s")
    print(f"平均响应：{metrics['avg_response_ms']}ms  P95：{metrics['p95_response_ms']}ms  P99：{metrics['p99_response_ms']}ms")
    print(f"错误率：{metrics['error_rate_pct']}%")
    for name, c in result["checks"].items():
        flag = "✅" if c["pass"] else "❌"
        print(f"  {flag} {name}: {c.get('actual') or c.get('actual_pct')} (需 {c['required']})")
    if baseline_cmp.get("baseline_exists"):
        rflag = "❌" if baseline_cmp.get("is_regression") else "✅"
        print(f"  {rflag} 基线对比: 平均响应 {baseline_cmp['regression_pct']:+.1f}%")

    if args.update_baseline and result["overall"] == "PASS":
        update_baseline(metrics, args.baseline)

    sys.exit(0 if result["overall"] == "PASS" else 1)


if __name__ == "__main__":
    main()
