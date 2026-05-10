# SPDX-License-Identifier: MIT
"""
Pairwise / Allpairs 测试 - 组合优化
被引用方：03-用例设计 agent
原理：N 因素 K 水平全组合 = K^N，pairwise 仅保证任意两因素的水平组合都覆盖一次。
对兼容性 / 配置矩阵爆炸场景特别有效（如 OS × Browser × Lang × DB ≤ 几十用例）。
"""
import json
import logging
from itertools import combinations, product
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


def all_combinations(parameters: Dict[str, List]) -> List[Dict]:
    """笛卡尔积全组合（参考用，可能爆炸）"""
    keys = list(parameters.keys())
    values = [parameters[k] for k in keys]
    return [dict(zip(keys, combo)) for combo in product(*values)]


def pairwise(parameters: Dict[str, List]) -> List[Dict]:
    """
    生成覆盖所有两因素组合的最小用例集（贪心算法 IPO 风格）。
    parameters: {"OS": ["Win","Mac"], "Browser": ["Chrome","Firefox"], "Lang": ["zh","en"]}
    """
    keys = list(parameters.keys())
    if len(keys) < 2:
        return all_combinations(parameters)

    # 收集所有两两组合需要覆盖的配对
    required_pairs = set()
    for k1, k2 in combinations(keys, 2):
        for v1 in parameters[k1]:
            for v2 in parameters[k2]:
                required_pairs.add((k1, v1, k2, v2))

    selected: List[Dict] = []
    while required_pairs:
        # 每轮：构造一个能覆盖最多未覆盖 pair 的用例
        best_case = None
        best_cover = -1
        # 候选枚举：穷举所有可能的笛卡尔积（对小因素集合可行）
        for combo in product(*[parameters[k] for k in keys]):
            case = dict(zip(keys, combo))
            cover = _count_covered_pairs(case, required_pairs)
            if cover > best_cover:
                best_cover = cover
                best_case = case
                if cover == len(required_pairs):
                    break
        if best_case is None or best_cover == 0:
            break
        selected.append(best_case)
        # 移除已覆盖的 pair
        to_remove = set()
        for k1, v1, k2, v2 in required_pairs:
            if best_case.get(k1) == v1 and best_case.get(k2) == v2:
                to_remove.add((k1, v1, k2, v2))
        required_pairs -= to_remove

    return selected


def _count_covered_pairs(case: Dict, required: set) -> int:
    n = 0
    for k1, v1, k2, v2 in required:
        if case.get(k1) == v1 and case.get(k2) == v2:
            n += 1
    return n


def generate_test_cases(parameters: Dict[str, List],
                         id_prefix: str = "TC-PAIR",
                         output: str = "workspace/测试用例/pairwise_cases.json") -> str:
    cases = pairwise(parameters)
    enriched = [
        {"id": f"{id_prefix}-{i+1:03d}", "params": c, "type": "COMPAT"}
        for i, c in enumerate(cases)
    ]
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    Path(output).write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    full = len(list(product(*parameters.values())))
    logger.info(f"Pairwise: {len(cases)} 用例（全组合 {full} → 减少 {round((1 - len(cases)/full) * 100)}%）")
    return output


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Pairwise 用例生成")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--output", default="workspace/测试用例/pairwise_cases.json")
    args = parser.parse_args()
    if args.demo:
        # 4 因素 × 各 3 水平 = 81 全组合 → pairwise ≈ 9
        params = {
            "OS":      ["Windows", "macOS", "Linux"],
            "Browser": ["Chrome", "Firefox", "Safari"],
            "Lang":    ["zh-CN", "en-US", "ja-JP"],
            "DB":      ["MySQL", "Postgres", "SQLite"],
        }
        path = generate_test_cases(params, output=args.output)
        print(f"已生成: {path}")
