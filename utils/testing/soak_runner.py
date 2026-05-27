# SPDX-License-Identifier: MIT
"""
长时稳定性测试（soak / endurance / 内存泄漏检测）
被引用方：16-可靠性稳定性 agent / soak-test skill
"""
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def soak_test(scenario: Callable[[], None],
              duration_hours: float = 24,
              interval_sec: int = 10,
              metric_proc_pid: Optional[int] = None,
              output_dir: str = "workspace/执行日志/soak") -> Dict:
    """
    长时稳定性测试。
    scenario: 单次业务调用函数（无返回，无参数）
    duration_hours: 持续时长（小时）
    interval_sec: 两次调用间隔
    metric_proc_pid: 监控指定进程 PID（采集 CPU/内存）
    """
    import psutil

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    end_ts = time.time() + duration_hours * 3600
    start_ts = time.time()
    metrics: List[Dict] = []
    failures = 0
    successes = 0

    proc = None
    if metric_proc_pid:
        try:
            proc = psutil.Process(metric_proc_pid)
        except psutil.NoSuchProcess:
            logger.warning(f"进程 {metric_proc_pid} 不存在")

    iter_count = 0
    while time.time() < end_ts:
        iter_count += 1
        try:
            scenario()
            successes += 1
        except Exception as e:
            failures += 1
            logger.warning(f"iter {iter_count} 失败: {e}")

        # 进程指标采样
        sample = {
            "iter": iter_count,
            "elapsed_sec": round(time.time() - start_ts, 1),
            "successes": successes,
            "failures": failures,
            "fail_rate_pct": round(failures / max(iter_count, 1) * 100, 2),
        }
        if proc:
            try:
                sample["cpu_pct"] = proc.cpu_percent(interval=None)
                sample["rss_mb"] = round(proc.memory_info().rss / 1024 / 1024, 1)
            except psutil.NoSuchProcess:
                sample["proc_dead"] = True

        metrics.append(sample)

        # 每 60 个采样落盘一次（防中途崩溃丢数据）
        if iter_count % 60 == 0:
            _save(metrics, output_dir)

        time.sleep(interval_sec)

    _save(metrics, output_dir)

    # 内存泄漏判定：取首尾 RSS 平均，对比超阈值告警
    leak_warn = False
    if proc and len(metrics) > 20:
        early = [m for m in metrics[:10] if "rss_mb" in m]
        late = [m for m in metrics[-10:] if "rss_mb" in m]
        if early and late:
            avg_early = sum(m["rss_mb"] for m in early) / len(early)
            avg_late = sum(m["rss_mb"] for m in late) / len(late)
            growth_pct = (avg_late - avg_early) / avg_early * 100
            leak_warn = growth_pct > 30
            logger.info(f"内存增长: {avg_early:.0f} → {avg_late:.0f} MB ({growth_pct:+.1f}%)")

    return {
        "duration_hours": duration_hours,
        "total_iters": iter_count,
        "successes": successes,
        "failures": failures,
        "fail_rate_pct": round(failures / max(iter_count, 1) * 100, 2),
        "memory_leak_suspected": leak_warn,
        "report_dir": output_dir,
    }


def _save(metrics: List[Dict], output_dir: str):
    path = Path(output_dir) / f"soak_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")


# ===== 简易场景：HTTP 心跳 =====

def http_scenario(url: str, expected_status: int = 200):
    """通用 HTTP 心跳场景，可作为 soak_test 的 scenario 参数"""
    import requests
    def _scenario():
        r = requests.get(url, timeout=10)
        assert r.status_code == expected_status, f"status={r.status_code}"
    return _scenario


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="长时 soak 测试")
    parser.add_argument("--url", required=True, help="HTTP 心跳 URL")
    parser.add_argument("--hours", type=float, default=1.0)
    parser.add_argument("--interval", type=int, default=10)
    parser.add_argument("--pid", type=int, default=None, help="监控的进程 PID")
    args = parser.parse_args()
    result = soak_test(
        scenario=http_scenario(args.url),
        duration_hours=args.hours,
        interval_sec=args.interval,
        metric_proc_pid=args.pid,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
