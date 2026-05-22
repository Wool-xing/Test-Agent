"""Flywheel ORM. Postgres (pgvector) primary, sqlite fallback for tests."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    target_summary: Mapped[str] = mapped_column(Text)
    target_kind: Mapped[str] = mapped_column(String(64))
    decision: Mapped[dict] = mapped_column(JSON)  # full RoutingDecision JSON
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus, name="run_status"), default=RunStatus.pending)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    artifact_keys: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    cases: Mapped[list[Case]] = relationship(back_populates="run", cascade="all, delete-orphan")
    evidence: Mapped[list[Evidence]] = relationship(back_populates="run", cascade="all, delete-orphan")


class CaseResult(str, enum.Enum):
    passed = "passed"
    failed = "failed"
    blocked = "blocked"
    skipped = "skipped"


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    title: Mapped[str] = mapped_column(String(512))
    priority: Mapped[str] = mapped_column(String(8), default="P2")  # P0/P1/P2/P3
    steps: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    result: Mapped[CaseResult | None] = mapped_column(Enum(CaseResult, name="case_result"), nullable=True)
    expert: Mapped[str | None] = mapped_column(String(64), nullable=True)
    skill: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[Run] = relationship(back_populates="cases")
    defects: Mapped[list[Defect]] = relationship(back_populates="case", cascade="all, delete-orphan")


class DefectSeverity(str, enum.Enum):
    p0 = "P0"
    p1 = "P1"
    p2 = "P2"
    p3 = "P3"


class DefectStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"
    rejected = "rejected"


class Defect(Base):
    __tablename__ = "defects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(512))
    severity: Mapped[DefectSeverity] = mapped_column(Enum(DefectSeverity, name="defect_severity"))
    status: Mapped[DefectStatus] = mapped_column(Enum(DefectStatus, name="defect_status"), default=DefectStatus.open)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)  # zentao/jira
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    case: Mapped[Case | None] = relationship(back_populates="defects")


class EvidenceKind(str, enum.Enum):
    log = "log"
    screenshot = "screenshot"
    video = "video"
    har = "har"
    report = "report"
    other = "other"


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    kind: Mapped[EvidenceKind] = mapped_column(Enum(EvidenceKind, name="evidence_kind"))
    minio_key: Mapped[str] = mapped_column(String(1024))
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    run: Mapped[Run] = relationship(back_populates="evidence")


class FeedbackKind(str, enum.Enum):
    false_positive = "false_positive"
    false_negative = "false_negative"
    routing_wrong = "routing_wrong"
    routing_correct = "routing_correct"
    other = "other"


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    kind: Mapped[FeedbackKind] = mapped_column(Enum(FeedbackKind, name="feedback_kind"))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    user: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class Embedding(Base):
    """pgvector-backed embedding for similarity search.

    The actual VECTOR column is added in the alembic migration to keep this file
    importable without pgvector installed (sqlite fallback for tests).
    """

    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_type: Mapped[str] = mapped_column(String(32))  # case|defect|report
    source_id: Mapped[int] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(String(64))
    dim: Mapped[int] = mapped_column(Integer)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
