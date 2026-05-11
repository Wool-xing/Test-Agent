"""Flywheel repository: high-level CRUD used by orchestrator/api."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from runtime.storage.db import session_scope
from runtime.storage.models import (
    Case,
    CaseResult,
    Defect,
    DefectSeverity,
    Evidence,
    EvidenceKind,
    Feedback,
    FeedbackKind,
    Run,
    RunStatus,
)


def new_run_id() -> str:
    return uuid.uuid4().hex[:24]


def create_run(target_summary: str, target_kind: str, decision_dict: dict) -> str:
    run_id = new_run_id()
    with session_scope() as s:
        s.add(
            Run(
                id=run_id,
                target_summary=target_summary,
                target_kind=target_kind,
                decision=decision_dict,
                status=RunStatus.pending,
            )
        )
    return run_id


def set_run_status(run_id: str, status: RunStatus) -> None:
    with session_scope() as s:
        r = s.get(Run, run_id)
        if r is None:
            raise KeyError(run_id)
        r.status = status
        if status in (RunStatus.succeeded, RunStatus.failed, RunStatus.cancelled):
            r.finished_at = datetime.now(timezone.utc)


def add_case(
    run_id: str,
    title: str,
    *,
    priority: str = "P2",
    expert: str | None = None,
    skill: str | None = None,
    result: CaseResult | None = None,
    duration_ms: int | None = None,
    error: str | None = None,
    steps: list[dict] | None = None,
) -> int:
    with session_scope() as s:
        c = Case(
            run_id=run_id,
            title=title,
            priority=priority,
            expert=expert,
            skill=skill,
            result=result,
            duration_ms=duration_ms,
            error=error,
            steps=steps,
        )
        s.add(c)
        s.flush()
        return c.id


def add_defect(case_id: int | None, title: str, severity: DefectSeverity, **kwargs) -> int:
    with session_scope() as s:
        d = Defect(case_id=case_id, title=title, severity=severity, **kwargs)
        s.add(d)
        s.flush()
        return d.id


def add_evidence(run_id: str, kind: EvidenceKind, minio_key: str, sha256: str | None = None, size_bytes: int | None = None) -> int:
    with session_scope() as s:
        e = Evidence(run_id=run_id, kind=kind, minio_key=minio_key, sha256=sha256, size_bytes=size_bytes)
        s.add(e)
        s.flush()
        return e.id


def add_feedback(run_id: str, kind: FeedbackKind, note: str | None = None, user: str | None = None) -> int:
    with session_scope() as s:
        f = Feedback(run_id=run_id, kind=kind, note=note, user=user)
        s.add(f)
        s.flush()
        return f.id
