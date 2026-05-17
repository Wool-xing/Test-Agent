"""DORA 2025 metrics tracker — rework rate, change failure rate, MTTR, flaky rate.

DORA 2025 replaced Elite/High/Medium/Low tiers with 7 archetypes.
Key metrics tracked:
- rework_rate: unplanned redeployments / total deploys  (primary stability metric)
- change_failure_rate: % of changes that cause incidents
- mttr_minutes: mean time to recover from failure
- flaky_test_rate: % of tests that are flaky
- lead_time_minutes: time from commit to deploy-ready

Reference: DORA 2025 Accelerate State of DevOps Report
"""

from __future__ import annotations

import json
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Deployment:
    id: str
    timestamp: float
    planned: bool      # True = planned, False = unplanned (rework)
    success: bool


@dataclass
class Incident:
    id: str
    timestamp: float
    severity: str      # P0 | P1 | P2
    resolved_at: float | None = None
    resolution_minutes: float = 0.0


@dataclass
class CommitRecord:
    commit_hash: str
    timestamp: float
    deploy_ready_at: float | None = None


@dataclass
class DoraSummary:
    rework_rate: float            # 0.0–1.0, lower is better
    change_failure_rate: float    # 0.0–1.0, lower is better
    mttr_minutes: float           # mean time to recover
    flaky_test_rate: float        # 0.0–1.0, lower is better
    lead_time_mean_minutes: float # mean lead time
    total_deployments: int
    total_incidents: int
    archetype: str                # DORA 2025 archetype

    def to_dict(self) -> dict[str, Any]:
        return {
            "rework_rate": round(self.rework_rate, 4),
            "change_failure_rate": round(self.change_failure_rate, 4),
            "mttr_minutes": round(self.mttr_minutes, 1),
            "flaky_test_rate": round(self.flaky_test_rate, 4),
            "lead_time_mean_minutes": round(self.lead_time_mean_minutes, 1),
            "total_deployments": self.total_deployments,
            "total_incidents": self.total_incidents,
            "archetype": self.archetype,
        }


class DoraTracker:
    """Thread-safe DORA metrics collector."""

    def __init__(self, persist_path: str = "workspace/dora_metrics.json") -> None:
        self._lock = threading.Lock()
        self._persist = Path(persist_path)
        self._deployments: list[Deployment] = []
        self._incidents: list[Incident] = []
        self._commits: list[CommitRecord] = []
        self._flaky_tests: dict[str, int] = defaultdict(int)  # test_name → flaky count
        self._total_test_runs: int = 0
        self._load()

    # ── Record ──

    def record_deployment(self, deploy_id: str, planned: bool = True, success: bool = True) -> None:
        with self._lock:
            self._deployments.append(Deployment(
                id=deploy_id, timestamp=time.time(),
                planned=planned, success=success,
            ))
            self._prune_deployments()
            self._save()

    def record_incident(self, incident_id: str, severity: str = "P1") -> str:
        """Record incident start. Returns incident_id for resolve_incident()."""
        with self._lock:
            inc = Incident(id=incident_id, timestamp=time.time(), severity=severity)
            self._incidents.append(inc)
            self._save()
            return incident_id

    def resolve_incident(self, incident_id: str) -> None:
        """Mark incident as resolved and compute MTTR."""
        now = time.time()
        with self._lock:
            for inc in self._incidents:
                if inc.id == incident_id and inc.resolved_at is None:
                    inc.resolved_at = now
                    inc.resolution_minutes = round((now - inc.timestamp) / 60, 1)
                    self._save()
                    return

    def record_commit(self, commit_hash: str) -> None:
        with self._lock:
            self._commits.append(CommitRecord(
                commit_hash=commit_hash, timestamp=time.time(),
            ))
            self._prune_commits()
            self._save()

    def mark_deploy_ready(self, commit_hash: str) -> None:
        now = time.time()
        with self._lock:
            for c in self._commits:
                if c.commit_hash == commit_hash and c.deploy_ready_at is None:
                    c.deploy_ready_at = now
                    self._save()
                    return

    def record_flaky_test(self, test_name: str) -> None:
        with self._lock:
            self._flaky_tests[test_name] += 1

    def record_test_run(self) -> None:
        with self._lock:
            self._total_test_runs += 1

    # ── Compute ──

    def summarize(self) -> DoraSummary:
        with self._lock:
            total_deploys = len(self._deployments)
            rework = sum(1 for d in self._deployments if not d.planned)
            failures = sum(1 for d in self._deployments if not d.success)

            resolved = [i for i in self._incidents if i.resolved_at is not None]
            mttr = (sum(i.resolution_minutes for i in resolved) / len(resolved)
                    ) if resolved else 0.0

            ready_commits = [c for c in self._commits if c.deploy_ready_at is not None]
            lead_times = [(c.deploy_ready_at - c.timestamp) / 60 for c in ready_commits if c.deploy_ready_at]
            avg_lead = sum(lead_times) / len(lead_times) if lead_times else 0.0

            total_tests = len(self._flaky_tests) + self._total_test_runs
            flaky_rate = len(self._flaky_tests) / max(total_tests, 1)

            rework_rate = rework / max(total_deploys, 1)
            change_failure_rate = failures / max(total_deploys, 1)

            # DORA 2025 archetype classification
            if change_failure_rate < 0.05 and mttr < 60:
                archetype = "Elite"
            elif change_failure_rate < 0.10 and mttr < 120:
                archetype = "High"
            elif change_failure_rate < 0.15:
                archetype = "Medium"
            else:
                archetype = "Low"

            return DoraSummary(
                rework_rate=rework_rate,
                change_failure_rate=change_failure_rate,
                mttr_minutes=round(mttr, 1),
                flaky_test_rate=round(flaky_rate, 4),
                lead_time_mean_minutes=round(avg_lead, 1),
                total_deployments=total_deploys,
                total_incidents=len(self._incidents),
                archetype=archetype,
            )

    # ── Persistence ──

    def _save(self) -> None:
        self._persist.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "deployments": [{"id": d.id, "timestamp": d.timestamp,
                             "planned": d.planned, "success": d.success}
                            for d in self._deployments[-500:]],
            "incidents": [{"id": i.id, "timestamp": i.timestamp,
                           "severity": i.severity, "resolution_minutes": i.resolution_minutes}
                          for i in self._incidents[-500:]],
            "commits": [{"hash": c.commit_hash, "timestamp": c.timestamp,
                         "deploy_ready_at": c.deploy_ready_at}
                        for c in self._commits[-500:]],
            "flaky_tests": dict(self._flaky_tests),
            "total_test_runs": self._total_test_runs,
        }
        self._persist.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _load(self) -> None:
        if not self._persist.exists():
            return
        data = json.loads(self._persist.read_text(encoding="utf-8"))
        self._deployments = [Deployment(**d) for d in data.get("deployments", [])]
        self._incidents = [Incident(**i) for i in data.get("incidents", [])]
        self._commits = [CommitRecord(**c) for c in data.get("commits", [])]
        self._flaky_tests = defaultdict(int, data.get("flaky_tests", {}))
        self._total_test_runs = data.get("total_test_runs", 0)

    def _prune_deployments(self) -> None:
        if len(self._deployments) > 1000:
            self._deployments = self._deployments[-500:]

    def _prune_commits(self) -> None:
        if len(self._commits) > 1000:
            self._commits = self._commits[-500:]


# Global singleton
_tracker: DoraTracker | None = None


def get_dora_tracker() -> DoraTracker:
    global _tracker
    if _tracker is None:
        _tracker = DoraTracker()
    return _tracker


# ═══════════════════════════════════════════════════════════════
# FastAPI integration
# ═══════════════════════════════════════════════════════════════

def create_dora_router():
    """Create FastAPI router for DORA metrics endpoints."""
    try:
        from fastapi import APIRouter
    except ImportError:
        return None

    router = APIRouter(tags=["dora"])

    @router.get("/dora/summary")
    async def dora_summary():
        return get_dora_tracker().summarize().to_dict()

    @router.post("/dora/deployment")
    async def record_deployment(deploy_id: str = "", planned: bool = True, success: bool = True):
        get_dora_tracker().record_deployment(deploy_id or f"auto-{int(time.time())}", planned, success)
        return {"status": "recorded"}

    @router.post("/dora/incident")
    async def record_incident(incident_id: str = "", severity: str = "P1"):
        get_dora_tracker().record_incident(incident_id or f"inc-{int(time.time())}", severity)
        return {"status": "recorded"}

    @router.post("/dora/flaky-test")
    async def record_flaky(test_name: str):
        get_dora_tracker().record_flaky_test(test_name)
        return {"status": "recorded"}

    return router


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="DORA metrics tracker")
    sub = ap.add_subparsers(dest="cmd")

    sub.add_parser("summary", help="Print DORA summary")

    dep = sub.add_parser("deploy", help="Record deployment")
    dep.add_argument("--id", required=True)
    dep.add_argument("--unplanned", action="store_true")

    inc = sub.add_parser("incident", help="Record/resolve incident")
    inc.add_argument("--id", required=True)
    inc.add_argument("--severity", default="P1")
    inc.add_argument("--resolve", action="store_true")

    args = ap.parse_args()
    tracker = get_dora_tracker()

    if args.cmd == "summary":
        print(json.dumps(tracker.summarize().to_dict(), indent=2, ensure_ascii=False))
    elif args.cmd == "deploy":
        tracker.record_deployment(args.id, planned=not args.unplanned)
        print(f"Deployment {args.id} recorded")
    elif args.cmd == "incident":
        if args.resolve:
            tracker.resolve_incident(args.id)
            print(f"Incident {args.id} resolved")
        else:
            tracker.record_incident(args.id, args.severity)
            print(f"Incident {args.id} recorded")
