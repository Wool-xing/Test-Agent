# SPDX-License-Identifier: MIT
"""
变异测试（Mutation Testing）- 评估测试用例有效性
被引用方：度量 / 测试质量评估

工具：mutmut（推荐）/ cosmic-ray
原理：随机修改源码（变异），跑测试套件。如测试仍通过 → 变异"存活" → 用例不够严
"""
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def run_mutmut(target: str = "./src", paths_to_mutate: Optional[str] = None) -> Dict:
    """
    运行 mutmut 变异测试。需 pip install mutmut。
    """
    cmd = ["mutmut", "run"]
    if paths_to_mutate:
        cmd += ["--paths-to-mutate", paths_to_mutate]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

    # 解析输出
    summary = subprocess.run(["mutmut", "results"], capture_output=True, text=True)
    text = summary.stdout
    killed = text.count("killed")
    survived = text.count("survived")
    suspicious = text.count("suspicious")
    timeout = text.count("timeout")
    total = killed + survived + suspicious + timeout
    score = round(killed / max(total, 1) * 100, 1)

    return {
        "total_mutants": total,
        "killed": killed,
        "survived": survived,
        "suspicious": suspicious,
        "timeout": timeout,
        "mutation_score_pct": score,
        "interpretation": (
            "≥80% 优秀" if score >= 80
            else "60-80% 良好" if score >= 60
            else "<60% 测试不充分"
        ),
    }


def show_survived_mutants(limit: int = 20) -> Dict:
    """查看存活变异（暴露未测的代码路径）"""
    proc = subprocess.run(
        ["mutmut", "results"], capture_output=True, text=True, timeout=30,
    )
    survived_ids = []
    for line in proc.stdout.splitlines():
        if "survived" in line:
            parts = line.split()
            if parts and parts[0].isdigit():
                survived_ids.append(parts[0])
    return {"survived_mutants": survived_ids[:limit]}


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="变异测试")
    sub = parser.add_subparsers(dest="cmd")
    r = sub.add_parser("run"); r.add_argument("--target", default="./src")
    s = sub.add_parser("survived"); s.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if args.cmd == "run":
        print(json.dumps(run_mutmut(args.target), indent=2, ensure_ascii=False))
    elif args.cmd == "survived":
        print(json.dumps(show_survived_mutants(args.limit), indent=2))
