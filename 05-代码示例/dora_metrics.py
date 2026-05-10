"""
DORA 4 大指标 - DevOps 成熟度度量
- 部署频率（Deployment Frequency）
- 变更前置时间（Lead Time for Changes）
- 变更失败率（Change Failure Rate）
- 平均恢复时间（MTTR）

被引用方：度量 / 持续改进 / 管理层报告
数据源：Git 提交 + CI/CD 部署日志 + 事故记录
"""
import json
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ===== 部署频率 =====

def deployment_frequency(deployments: List[Dict], days: int = 30) -> Dict:
    """
    deployments: [{"timestamp": "2026-05-10T...", "env": "prod", "success": True}]
    """
    cutoff = datetime.now() - timedelta(days=days)
    recent = [
        d for d in deployments
        if datetime.fromisoformat(d["timestamp"].replace("Z", "")) > cutoff
        and d.get("env") == "prod"
        and d.get("success", True)
    ]
    per_day = len(recent) / max(days, 1)
    rating = (
        "Elite" if per_day >= 1
        else "High" if per_day >= 1 / 7
        else "Medium" if per_day >= 1 / 30
        else "Low"
    )
    return {
        "period_days": days,
        "deployments": len(recent),
        "per_day": round(per_day, 2),
        "rating": rating,
    }


# ===== 变更前置时间 =====

def lead_time_for_changes(git_dir: str = ".",
                          deployments: Optional[List[Dict]] = None) -> Dict:
    """
    从 git commit 时间到部署时间的间隔（小时）。
    简化版：取最近 commit 时间 vs 最近成功 prod 部署时间。
    """
    proc = subprocess.run(
        ["git", "log", "--pretty=format:%H,%ct", "-n", "100"],
        cwd=git_dir, capture_output=True, text=True,
    )
    if not deployments:
        return {"error": "需提供 deployments 数据"}

    # 取最近成功 prod 部署
    last_prod = max([d for d in deployments if d.get("env") == "prod" and d.get("success")],
                    key=lambda x: x["timestamp"], default=None)
    if not last_prod:
        return {"error": "无成功 prod 部署"}

    deploy_ts = datetime.fromisoformat(last_prod["timestamp"].replace("Z", ""))
    # 取该部署对应的最早未部署 commit（简化：取倒数第二个 commit 时间）
    commits = proc.stdout.splitlines()
    if not commits:
        return {"error": "无 commit"}
    commit_hash, ts = commits[0].split(",")
    commit_ts = datetime.fromtimestamp(int(ts))

    lead_hours = (deploy_ts - commit_ts).total_seconds() / 3600
    rating = (
        "Elite" if lead_hours < 1
        else "High" if lead_hours < 24
        else "Medium" if lead_hours < 24 * 7
        else "Low"
    )
    return {"lead_time_hours": round(lead_hours, 1), "rating": rating}


# ===== 变更失败率 =====

def change_failure_rate(deployments: List[Dict], days: int = 30) -> Dict:
    cutoff = datetime.now() - timedelta(days=days)
    recent = [
        d for d in deployments
        if datetime.fromisoformat(d["timestamp"].replace("Z", "")) > cutoff
        and d.get("env") == "prod"
    ]
    if not recent:
        return {"period_days": days, "total": 0, "failure_rate_pct": None}
    failures = sum(1 for d in recent if not d.get("success", True) or d.get("rollback"))
    rate = failures / len(recent) * 100
    rating = (
        "Elite" if rate <= 5
        else "High" if rate <= 10
        else "Medium" if rate <= 15
        else "Low"
    )
    return {
        "period_days": days,
        "total_deployments": len(recent),
        "failures": failures,
        "failure_rate_pct": round(rate, 1),
        "rating": rating,
    }


# ===== MTTR =====

def mean_time_to_restore(incidents: List[Dict]) -> Dict:
    """
    incidents: [{"started": "...", "resolved": "...", "severity": "P0"}]
    """
    durations = []
    for i in incidents:
        if not i.get("resolved"):
            continue
        start = datetime.fromisoformat(i["started"].replace("Z", ""))
        end = datetime.fromisoformat(i["resolved"].replace("Z", ""))
        durations.append((end - start).total_seconds() / 3600)
    if not durations:
        return {"mttr_hours": None, "incidents": 0}
    avg = sum(durations) / len(durations)
    rating = (
        "Elite" if avg < 1
        else "High" if avg < 24
        else "Medium" if avg < 24 * 7
        else "Low"
    )
    return {
        "incidents": len(durations),
        "mttr_hours": round(avg, 2),
        "p95_hours": round(sorted(durations)[int(len(durations) * 0.95)], 2),
        "rating": rating,
    }


# ===== 综合报告 =====

def dora_summary(deployments: List[Dict], incidents: List[Dict],
                  git_dir: str = ".", days: int = 30) -> Dict:
    return {
        "report_date": datetime.now().isoformat(),
        "period_days": days,
        "deployment_frequency": deployment_frequency(deployments, days),
        "lead_time_for_changes": lead_time_for_changes(git_dir, deployments),
        "change_failure_rate": change_failure_rate(deployments, days),
        "mttr": mean_time_to_restore(incidents),
    }


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="DORA 指标")
    parser.add_argument("--deployments", required=True, help="JSON 文件")
    parser.add_argument("--incidents", default=None, help="JSON 文件")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    deps = json.loads(Path(args.deployments).read_text())
    incs = json.loads(Path(args.incidents).read_text()) if args.incidents else []
    print(json.dumps(dora_summary(deps, incs, days=args.days),
                      indent=2, ensure_ascii=False))
