# SPDX-License-Identifier: MIT
"""
Flaky 测试检测器
依赖：pytest 启用 --junitxml 输出到 workspace/测试报告/{PROJECT_NAME}/history/
被引用方：regression-test skill
"""
import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from paths import get_output_dir, current_run_id

logger = logging.getLogger(__name__)


class FlakyTestDetector:
    """读取最近 N 次 junit-xml，识别 flaky（既有 pass 又有 fail）。"""

    def __init__(
        self,
        history_dir: str = None,
        history_limit: int = 5,
        quarantine_threshold: float = 0.3,
    ):
        self.history_dir = Path(history_dir) if history_dir else get_output_dir("history")
        self.history_limit = history_limit
        self.quarantine_threshold = quarantine_threshold

    def _load_recent_results(self) -> Dict[str, List[str]]:
        results: Dict[str, List[str]] = {}
        if not self.history_dir.exists():
            return results
        files = sorted(self.history_dir.glob("*.xml"))[-self.history_limit:]
        for f in files:
            try:
                tree = ET.parse(f)
                root = tree.getroot()
                # 兼容 testsuite 单根 与 testsuites 多根
                suites = [root] if root.tag == "testsuite" else root.findall(".//testsuite")
                for suite in suites:
                    for tc in suite.findall(".//testcase"):
                        test_id = f"{tc.get('classname')}.{tc.get('name')}"
                        status = "failed" if tc.find("failure") is not None or tc.find("error") is not None else "passed"
                        results.setdefault(test_id, []).append(status)
            except Exception as e:
                logger.warning(f"解析 {f} 失败: {e}")
        return results

    def detect(self) -> List[Dict]:
        """返回 flaky 用例清单，按失败率降序。"""
        recent = self._load_recent_results()
        flaky = []
        for test_id, history in recent.items():
            if len(history) < 2:
                continue
            pass_count = history.count("passed")
            fail_count = history.count("failed")
            if pass_count > 0 and fail_count > 0:
                rate = fail_count / len(history)
                flaky.append({
                    "test_id": test_id,
                    "fail_rate_pct": round(rate * 100, 1),
                    "history": history,
                    "action": "quarantine" if rate > self.quarantine_threshold else "monitor",
                })
        return sorted(flaky, key=lambda x: x["fail_rate_pct"], reverse=True)

    def detect_trends(self) -> List[Dict]:
        """跨运行趋势分析 — 检测 Pass→Fail→Pass / Fail→Pass→Fail 模式。

        返回每个 flaky 用例的趋势摘要:
          - pattern: "P-F-P" | "F-P-F" | "mixed"
          - transitions: 状态切换次数
          - streak: 当前连续状态
          - confidence: 基于 pattern 稳定性的置信度 (0-1)
        """
        recent = self._load_recent_results()
        trends = []
        for test_id, history in recent.items():
            if len(history) < 3:
                continue
            transitions = sum(1 for i in range(1, len(history)) if history[i] != history[i - 1])
            if transitions == 0:
                continue  # 全 pass 或全 fail — 不 flaky
            streak = history[-1]
            streak_len = 1
            for s in reversed(history[:-1]):
                if s == streak:
                    streak_len += 1
                else:
                    break
            pass_count = history.count("passed")
            fail_count = history.count("failed")
            fail_rate = fail_count / len(history)
            # P-F-P variant: pass→fail→pass (likely env flaky)
            # F-P-F variant: fail→pass→fail (likely regression)
            pattern = "mixed"
            if transitions == 2 and history[0] == "passed" and history[-1] == "passed":
                pattern = "P-F-P"
            elif transitions == 2 and history[0] == "failed" and history[-1] == "failed":
                pattern = "F-P-F"
            confidence = min(transitions / len(history) + fail_rate, 1.0)
            trends.append({
                "test_id": test_id,
                "pattern": pattern,
                "transitions": transitions,
                "streak": streak,
                "streak_len": streak_len,
                "fail_rate_pct": round(fail_rate * 100, 1),
                "confidence": round(confidence, 2),
                "history": history,
                "action": "quarantine" if fail_rate > self.quarantine_threshold else "monitor",
            })
        return sorted(trends, key=lambda x: x["confidence"], reverse=True)

    def generate_quarantine(self, flaky_list: List[Dict], output_path: str = None) -> Path:
        """生成隔离清单 — 每行一个 test_id，供 pytest --deselect 或 CI skip。"""
        if output_path is None:
            output_path = str(get_output_dir("quarantine", current_run_id()) / "quarantine.txt")
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"# Flaky quarantine — {len(flaky_list)} tests — {__import__('datetime').datetime.now():%Y-%m-%d %H:%M}"]
        for item in flaky_list:
            lines.append(f"# [{item.get('pattern', item.get('action', ''))}] fail_rate={item['fail_rate_pct']}%")
            lines.append(item["test_id"])
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info(f"quarantine list written: {out} ({len(flaky_list)} tests)")
        return out

    def generate_pytest_markers(self, flaky_list: List[Dict], output_path: str = None) -> Path:
        """生成 pytest marker 配置 — 标记 flaky 用例为 @pytest.mark.flaky。"""
        if output_path is None:
            output_path = str(get_output_dir("quarantine", current_run_id()) / "flaky_markers.ini")
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        lines = ["[pytest]", "markers ="]
        seen: set[str] = set()
        for item in flaky_list:
            tid = item["test_id"]
            # 提取简单模块名::用例名
            if "::" in tid:
                marker_name = tid.split("::")[-1].replace(" ", "_")[:40]
            else:
                marker_name = tid.replace(".", "_").replace(" ", "_")[:40]
            if marker_name in seen:
                marker_name = f"{marker_name}_{hash(tid) % 1000}"
            seen.add(marker_name)
            lines.append(f"    flaky({marker_name}): flaky test (fail_rate={item['fail_rate_pct']}%)")
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info(f"pytest marker config written: {out}")
        return out


def archive_junit(src: str, dest_dir: str = None):
    """把本次 junit-xml 归档到 history 目录（按时间命名）"""
    from datetime import datetime
    src_p = Path(src)
    dest_p = Path(dest_dir) if dest_dir else get_output_dir("history")
    dest_p.mkdir(parents=True, exist_ok=True)
    name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{src_p.name}"
    target = dest_p / name
    target.write_bytes(src_p.read_bytes())
    logger.info(f"归档 junit: {target}")
    return target


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Flaky 检测 + 趋势分析 + 隔离")
    parser.add_argument("--history", default=None)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--archive", help="本次 junit-xml 路径（归档后再检测）")
    parser.add_argument("--trends", action="store_true", help="输出趋势分析")
    parser.add_argument("--quarantine", action="store_true", help="生成隔离清单")
    parser.add_argument("--markers", action="store_true", help="生成 pytest marker 配置")
    args = parser.parse_args()
    if args.archive:
        archive_junit(args.archive, args.history)
    detector = FlakyTestDetector(args.history, args.limit)
    if args.trends:
        trends = detector.detect_trends()
        print(json.dumps(trends, indent=2, ensure_ascii=False))
    else:
        flaky = detector.detect()
        print(json.dumps(flaky, indent=2, ensure_ascii=False))
    if args.quarantine:
        flaky = detector.detect()
        detector.generate_quarantine(flaky)
    if args.markers:
        flaky = detector.detect()
        detector.generate_pytest_markers(flaky)
