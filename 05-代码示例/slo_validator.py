"""
SLO/SLI 性能契约验证（SRE 视角）
被引用方：test-lead / 性能测试

SLI（Service Level Indicator）：实测指标
SLO（Service Level Objective）：目标值（如 99.9% 可用性）
SLA（Service Level Agreement）：对外承诺，违反有惩罚

错误预算（Error Budget）= 100% - SLO，决定发布速度。
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ===== SLO 定义 =====

DEFAULT_SLOS = {
    "availability": {"target_pct": 99.9, "window_days": 30},
    "latency_p95_ms": {"target": 500, "window_days": 7},
    "latency_p99_ms": {"target": 1000, "window_days": 7},
    "error_rate_pct": {"target": 1.0, "window_days": 30},
    "throughput_min_qps": {"target": 100, "window_days": 1},
}


def evaluate_slo(metric_name: str, observed: float, slo_def: Dict) -> Dict:
    """单项 SLO 评估"""
    target = slo_def.get("target") or slo_def.get("target_pct")
    direction = slo_def.get("direction", "lower_is_better"
                             if "latency" in metric_name or "error" in metric_name
                             else "higher_is_better")

    if direction == "higher_is_better":
        meets = observed >= target
        margin_pct = (observed - target) / target * 100
    else:
        meets = observed <= target
        margin_pct = (target - observed) / target * 100

    return {
        "metric": metric_name,
        "observed": observed,
        "target": target,
        "direction": direction,
        "meets_slo": meets,
        "margin_pct": round(margin_pct, 2),
    }


# ===== 错误预算 =====

def error_budget(slo_pct: float, observed_pct: float,
                 window_days: int = 30) -> Dict:
    """
    错误预算：允许的不可用时间 / 已消耗的不可用时间。
    slo_pct: 99.9 表示目标 99.9%
    observed_pct: 实测可用率
    """
    allowed_downtime_min = (100 - slo_pct) / 100 * window_days * 24 * 60
    consumed_downtime_min = (100 - observed_pct) / 100 * window_days * 24 * 60
    remaining_min = allowed_downtime_min - consumed_downtime_min
    burn_rate = consumed_downtime_min / max(allowed_downtime_min, 0.001)

    return {
        "slo_pct": slo_pct,
        "observed_pct": observed_pct,
        "window_days": window_days,
        "allowed_downtime_min": round(allowed_downtime_min, 1),
        "consumed_downtime_min": round(consumed_downtime_min, 1),
        "remaining_budget_min": round(remaining_min, 1),
        "burn_rate": round(burn_rate, 3),
        "burn_rate_warning": burn_rate > 0.5,
        "budget_exhausted": remaining_min <= 0,
    }


# ===== 综合 SLO 报告 =====

def slo_report(metrics: Dict[str, float],
               slos: Optional[Dict] = None,
               output: Optional[str] = None) -> Dict:
    """
    metrics: {"availability": 99.95, "latency_p95_ms": 420, ...}
    """
    slos = slos or DEFAULT_SLOS
    results = {}
    overall_pass = True
    for name, val in metrics.items():
        if name not in slos:
            continue
        r = evaluate_slo(name, val, slos[name])
        results[name] = r
        if not r["meets_slo"]:
            overall_pass = False

    # 错误预算（如果含 availability）
    budget = None
    if "availability" in metrics and "availability" in slos:
        budget = error_budget(
            slos["availability"]["target_pct"],
            metrics["availability"],
            slos["availability"]["window_days"],
        )

    report = {
        "evaluated_at": datetime.now().isoformat(),
        "overall_pass": overall_pass,
        "slo_checks": results,
        "error_budget": budget,
    }

    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="SLO/SLI 验证")
    parser.add_argument("--metrics", required=True, help="JSON 文件含 metrics")
    parser.add_argument("--slos", default=None, help="JSON 文件含 SLO 定义")
    parser.add_argument("--output", default="workspace/执行日志/slo_report.json")
    args = parser.parse_args()
    metrics = json.loads(Path(args.metrics).read_text(encoding="utf-8"))
    slos = json.loads(Path(args.slos).read_text(encoding="utf-8")) if args.slos else None
    print(json.dumps(slo_report(metrics, slos, args.output), indent=2, ensure_ascii=False))
