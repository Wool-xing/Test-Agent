"""
UX 量化指标：任务完成时间 / 点击次数 / 错误恢复率 / 首屏可交互时间
被引用方：UI/移动 测试中调用，量化用户体验
"""
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ===== 任务级别 UX 跟踪器 =====

class UXTracker:
    """跟踪一个用户任务的 UX 指标"""

    def __init__(self, task_name: str):
        self.task_name = task_name
        self.start_ts: Optional[float] = None
        self.end_ts: Optional[float] = None
        self.click_count = 0
        self.error_count = 0
        self.recovery_count = 0
        self.events: List[Dict] = []

    def start(self):
        self.start_ts = time.time()
        self._log_event("task_start")

    def end(self, success: bool = True):
        self.end_ts = time.time()
        self._log_event("task_end", success=success)

    def click(self, target: str = ""):
        self.click_count += 1
        self._log_event("click", target=target)

    def error(self, message: str = ""):
        self.error_count += 1
        self._log_event("error", message=message)

    def recover(self):
        self.recovery_count += 1
        self._log_event("recovery")

    def _log_event(self, event_type: str, **kwargs):
        self.events.append({
            "ts": round(time.time(), 3),
            "type": event_type,
            **kwargs,
        })

    def summary(self) -> Dict:
        duration_ms = None
        if self.start_ts and self.end_ts:
            duration_ms = int((self.end_ts - self.start_ts) * 1000)
        return {
            "task": self.task_name,
            "duration_ms": duration_ms,
            "click_count": self.click_count,
            "error_count": self.error_count,
            "recovery_count": self.recovery_count,
            "recovery_rate": round(self.recovery_count / max(self.error_count, 1), 2),
            "events": self.events,
        }


# ===== 首屏可交互时间（Web）=====

def measure_tti(page, url: str, ready_selector: str, timeout: int = 30) -> float:
    """
    Web 首屏可交互时间：从 navigate 到 ready_selector 可见。
    page: Playwright Page 对象
    返回毫秒
    """
    t0 = time.time()
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_selector(ready_selector, timeout=timeout * 1000)
    return round((time.time() - t0) * 1000, 1)


# ===== 操作路径深度 =====

def task_efficiency(actual_clicks: int, optimal_clicks: int) -> float:
    """效率评分：理想点击数 / 实际点击数（1.0 = 完美）"""
    if actual_clicks <= 0:
        return 0.0
    return round(min(optimal_clicks / actual_clicks, 1.0), 2)


# ===== 错误恢复率 =====

def error_recovery_rate(error_count: int, recovery_count: int) -> float:
    if error_count <= 0:
        return 1.0
    return round(recovery_count / error_count, 2)


# ===== 持久化 =====

def save_ux_report(summaries: List[Dict],
                   output_dir: str = "workspace/执行日志/ux") -> str:
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = Path(output_dir) / f"ux_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(summaries, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)


# ===== UX 门禁建议 =====

DEFAULT_UX_GATES = {
    "task_max_duration_ms": 30_000,    # 任务 < 30s
    "task_max_clicks": 10,              # < 10 次点击
    "tti_max_ms": 3000,                 # 首屏 < 3s
    "min_recovery_rate": 0.8,           # 错误恢复率 ≥ 80%
}


def check_ux_gates(summary: Dict, gates: Optional[Dict] = None) -> Dict:
    g = gates or DEFAULT_UX_GATES
    checks = {
        "duration": summary.get("duration_ms", 0) <= g["task_max_duration_ms"],
        "clicks":   summary.get("click_count", 0) <= g["task_max_clicks"],
        "recovery": summary.get("recovery_rate", 1.0) >= g["min_recovery_rate"],
    }
    return {"checks": checks, "pass": all(checks.values())}


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    print("ux_metrics module loaded")
