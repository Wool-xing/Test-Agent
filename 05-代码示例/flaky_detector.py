"""
Flaky 测试检测器
依赖：pytest 启用 --junitxml 输出到 workspace/执行日志/history/
被引用方：regression-test skill
"""
import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class FlakyTestDetector:
    """读取最近 N 次 junit-xml，识别 flaky（既有 pass 又有 fail）。"""

    def __init__(
        self,
        history_dir: str = "workspace/执行日志/history",
        history_limit: int = 5,
        quarantine_threshold: float = 0.3,
    ):
        self.history_dir = Path(history_dir)
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


def archive_junit(src: str, dest_dir: str = "workspace/执行日志/history"):
    """把本次 junit-xml 归档到 history 目录（按时间命名）"""
    from datetime import datetime
    src_p = Path(src)
    dest_p = Path(dest_dir)
    dest_p.mkdir(parents=True, exist_ok=True)
    name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{src_p.name}"
    target = dest_p / name
    target.write_bytes(src_p.read_bytes())
    logger.info(f"归档 junit: {target}")
    return target


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Flaky 检测")
    parser.add_argument("--history", default="workspace/执行日志/history")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--archive", help="本次 junit-xml 路径（归档后再检测）")
    args = parser.parse_args()
    if args.archive:
        archive_junit(args.archive, args.history)
    detector = FlakyTestDetector(args.history, args.limit)
    print(json.dumps(detector.detect(), indent=2, ensure_ascii=False))
