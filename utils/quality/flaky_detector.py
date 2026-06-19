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

from utils.paths import get_output_dir, current_run_id

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


# ═══════════════════════════════════════════════════════════════
# Graph-based root cause analysis
# ═══════════════════════════════════════════════════════════════


def _load_graph(graph_path: str) -> dict:
    """Load the graphify knowledge graph. Returns empty dict if not found."""
    gp = Path(graph_path)
    if not gp.exists():
        logger.warning("graph not found: %s", gp)
        return {}
    with open(gp, "r", encoding="utf-8") as f:
        return json.load(f)


def _find_node_ids(test_name: str, graph: dict) -> list[str]:
    """Find graph node IDs matching a test name.

    Matches against node label (stripped of module prefix) and norm_label.
    """
    nodes = graph.get("nodes", [])
    # Normalize: strip common prefixes like "tests.test_module." and
    # convert pytest nodeid separators "::" to something searchable
    clean = test_name.split("::")[-1] if "::" in test_name else test_name.split(".")[-1]
    clean_lower = clean.lower().replace(" ", "_").replace("-", "_")

    matched = []
    for node in nodes:
        label = node.get("label", "")
        norm = node.get("norm_label", "")
        if clean in label or clean in norm:
            matched.append(node["id"])
            continue
        if clean_lower in norm or clean_lower in label.lower():
            matched.append(node["id"])
            continue
        # Partial match on function names: "test_x" matches "test_x()"
        if clean_lower.rstrip("()") in norm and clean_lower.rstrip("()"):
            matched.append(node["id"])
    return matched


def _trace_dependencies(node_ids: list[str], graph: dict, max_depth: int = 3) -> dict[str, set[str]]:
    """BFS trace from source nodes through graph links.

    Returns: {node_id: set of reachable node_ids within max_depth}.
    """
    links = graph.get("links", [])
    # Build adjacency: source -> targets and target -> sources
    forward: dict[str, set[str]] = {}
    backward: dict[str, set[str]] = {}
    for link in links:
        src = link.get("source", "")
        tgt = link.get("target", "")
        if src and tgt:
            forward.setdefault(src, set()).add(tgt)
            backward.setdefault(tgt, set()).add(src)

    reachable: dict[str, set[str]] = {}
    for start in node_ids:
        visited: set[str] = set()
        queue = [(start, 0)]
        while queue:
            current, depth = queue.pop(0)
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            for neighbor in forward.get(current, set()) | backward.get(current, set()):
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))
        reachable[start] = visited

    return reachable


def _node_by_id(node_id: str, graph: dict) -> dict | None:
    for n in graph.get("nodes", []):
        if n.get("id") == node_id:
            return n
    return None


def _estimate_complexity(node: dict, graph: dict) -> int:
    """Estimate cyclomatic complexity via degree (number of incident edges)."""
    node_id = node.get("id", "")
    degree = 0
    for link in graph.get("links", []):
        if link.get("source") == node_id or link.get("target") == node_id:
            degree += 1
    return degree


def find_root_cause_graph(
    flaky_tests: list[str],
    graph_path: str = "graphify-out/graph.json",
) -> dict[str, list[str]]:
    """For each flaky test, trace the graph to find likely root causes.

    Returns: {test_name: [likely_cause_1, likely_cause_2, ...]}
    Root causes ranked by:
    1. Shared dependencies between flaky tests (common code)
    2. Recently changed functions in the dependency chain
    3. Functions with high cyclomatic complexity
    """
    graph = _load_graph(graph_path)
    if not graph:
        return {t: ["graph not available"] for t in flaky_tests}

    links = graph.get("links", [])
    nodes_by_id: dict[str, dict] = {n["id"]: n for n in graph.get("nodes", [])}

    # Step 1: Find all dependency sets for all flaky tests
    test_deps: dict[str, set[str]] = {}
    test_node_ids: dict[str, list[str]] = {}
    for test_name in flaky_tests:
        node_ids = _find_node_ids(test_name, graph)
        test_node_ids[test_name] = node_ids
        if node_ids:
            reachable = _trace_dependencies(node_ids, graph)
            all_deps: set[str] = set()
            for r in reachable.values():
                all_deps.update(r)
            test_deps[test_name] = all_deps
        else:
            test_deps[test_name] = set()

    # Step 2: Find shared dependencies (intersection across flaky tests)
    # Only consider code nodes (not rationale nodes)
    shared_candidates: dict[str, int] = {}
    for dep_id in {d for deps in test_deps.values() for d in deps}:
        node = nodes_by_id.get(dep_id)
        if node is None or node.get("file_type") == "rationale":
            continue
        count = sum(1 for deps in test_deps.values() if dep_id in deps)
        if count >= 2:
            shared_candidates[dep_id] = count

    results: dict[str, list[str]] = {}
    for test_name in flaky_tests:
        deps = test_deps.get(test_name, set())
        if not deps:
            results[test_name] = ["no matching graph nodes found"]
            continue

        causes: list[tuple[str, float]] = []

        # Rank 1: Shared dependencies (common code hit by multiple flaky tests)
        for dep_id, share_count in shared_candidates.items():
            if dep_id in deps:
                node = nodes_by_id.get(dep_id, {})
                label = node.get("label", dep_id)
                file_loc = node.get("source_file", "")
                loc_str = f" ({file_loc})" if file_loc else ""
                score = share_count * 10.0  # Base: more sharing = more likely cause
                causes.append((f"{label}{loc_str} [shared by {share_count} flaky tests]", score))

        # Rank 2: High-complexity functions in the chain
        for dep_id in deps - set(shared_candidates):
            node = nodes_by_id.get(dep_id)
            if node is None or node.get("file_type") == "rationale":
                continue
            complexity = _estimate_complexity(node, graph)
            if complexity >= 5:
                label = node.get("label", dep_id)
                file_loc = node.get("source_file", "")
                loc_str = f" ({file_loc})" if file_loc else ""
                score = complexity * 0.5
                causes.append((f"{label}{loc_str} [complexity={complexity}]", score))

        # Sort by score descending
        causes.sort(key=lambda x: x[1], reverse=True)
        results[test_name] = [c[0] for c in causes[:5]] or ["no clear root cause identified"]

    return results


def auto_quarantine(
    flaky_tests: list[str],
    threshold: int = 3,
) -> list[str]:
    """Return list of tests that should be quarantined.

    A test is quarantined when it appears >= threshold times in the list.
    """
    from collections import Counter
    counts = Counter(flaky_tests)
    return [test_name for test_name, count in counts.items() if count >= threshold]


def suggest_fix(test_name: str, graph_path: str = "graphify-out/graph.json") -> str:
    """Given a flaky test, suggest a fix based on root cause analysis."""
    graph = _load_graph(graph_path)

    if not graph:
        return (
            f"No knowledge graph available for {test_name}. "
            "Suggestions: (1) Re-run test in isolation to confirm flakiness. "
            "(2) Check for hardcoded waits/sleeps. "
            "(3) Review shared mutable state or test ordering dependencies."
        )

    node_ids = _find_node_ids(test_name, graph)
    if not node_ids:
        return (
            f"No graph nodes found for {test_name}. "
            "Suggestions: (1) Re-run test in isolation. "
            "(2) Check for external dependencies (network, DB, file system). "
            "(3) Review test for non-deterministic inputs (random, time, UUID)."
        )

    reachable = _trace_dependencies(node_ids, graph)
    all_deps: set[str] = set()
    for r in reachable.values():
        all_deps.update(r)

    nodes_by_id: dict[str, dict] = {n["id"]: n for n in graph.get("nodes", [])}
    # Count dep types
    db_deps = 0
    network_deps = 0
    file_deps = 0
    high_complexity = 0
    for dep_id in all_deps:
        node = nodes_by_id.get(dep_id)
        if node is None:
            continue
        label = node.get("label", "").lower()
        file_loc = node.get("source_file", "").lower()
        if any(kw in label or kw in file_loc for kw in ["db", "database", "postgres", "mysql", "sqlite"]):
            db_deps += 1
        if any(kw in label or kw in file_loc for kw in ["http", "request", "network", "socket", "api"]):
            network_deps += 1
        if any(kw in label or kw in file_loc for kw in ["file", "path", "temp", "os."]):
            file_deps += 1
        if _estimate_complexity(node, graph) >= 8:
            high_complexity += 1

    suggestions = []
    if db_deps:
        suggestions.append(
            f"Database dependency detected ({db_deps} related nodes). "
            "Consider: (a) use test database with transactions/rollback, "
            "(b) ensure deterministic seed data, "
            "(c) verify connection pool is not exhausted between tests."
        )
    if network_deps:
        suggestions.append(
            f"Network dependency detected ({network_deps} related nodes). "
            "Consider: (a) mock external HTTP calls with responses/httpx-mock, "
            "(b) use local test server instead of real endpoints, "
            "(c) add retry with backoff for transient failures."
        )
    if file_deps:
        suggestions.append(
            f"File system dependency detected ({file_deps} related nodes). "
            "Consider: (a) use tmp_path fixture for isolated temp dirs, "
            "(b) clean up files in teardown/finally, "
            "(c) avoid race conditions on shared file paths."
        )
    if high_complexity:
        suggestions.append(
            f"High-complexity functions in dependency chain ({high_complexity} nodes with degree >= 8). "
            "Consider: (a) refactor complex functions to reduce coupling, "
            "(b) add more unit tests for edge cases, "
            "(c) break long functions into smaller, testable units."
        )
    if not suggestions:
        suggestions.append(
            f"No obvious risk pattern in dependency graph for {test_name}. "
            "Consider: (1) timing/race condition — add explicit synchronization, "
            "(2) test ordering dependency — use pytest-randomly to detect, "
            "(3) environment-specific — verify CI vs local parity."
        )

    return " | ".join(suggestions)


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
