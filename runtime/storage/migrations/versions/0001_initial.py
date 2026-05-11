"""initial flywheel schema

Revision ID: 0001
Revises:
Create Date: 2026-05-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"
    if is_pg:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    run_status = sa.Enum("pending", "running", "succeeded", "failed", "cancelled", name="run_status")
    case_result = sa.Enum("passed", "failed", "blocked", "skipped", name="case_result")
    defect_sev = sa.Enum("P0", "P1", "P2", "P3", name="defect_severity")
    defect_status = sa.Enum("open", "in_progress", "resolved", "closed", "rejected", name="defect_status")
    ev_kind = sa.Enum("log", "screenshot", "video", "har", "report", "other", name="evidence_kind")
    fb_kind = sa.Enum(
        "false_positive", "false_negative", "routing_wrong", "routing_correct", "other", name="feedback_kind"
    )

    op.create_table(
        "runs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("target_summary", sa.Text, nullable=False),
        sa.Column("target_kind", sa.String(64), nullable=False),
        sa.Column("decision", sa.JSON, nullable=False),
        sa.Column("status", run_status, nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("artifact_keys", sa.JSON, nullable=True),
    )

    op.create_table(
        "cases",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("priority", sa.String(8), nullable=False, server_default="P2"),
        sa.Column("steps", sa.JSON, nullable=True),
        sa.Column("result", case_result, nullable=True),
        sa.Column("expert", sa.String(64), nullable=True),
        sa.Column("skill", sa.String(64), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
    )
    op.create_index("ix_cases_run_id", "cases", ["run_id"])

    op.create_table(
        "defects",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id"), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("severity", defect_sev, nullable=False),
        sa.Column("status", defect_status, nullable=False, server_default="open"),
        sa.Column("root_cause", sa.Text, nullable=True),
        sa.Column("external_url", sa.String(1024), nullable=True),
        sa.Column("payload", sa.JSON, nullable=True),
    )

    op.create_table(
        "evidence",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("kind", ev_kind, nullable=False),
        sa.Column("minio_key", sa.String(1024), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("size_bytes", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_evidence_run_id", "evidence", ["run_id"])

    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(64), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("kind", fb_kind, nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("user", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    if is_pg:
        op.execute(
            """
            CREATE TABLE embeddings (
                id SERIAL PRIMARY KEY,
                source_type VARCHAR(32) NOT NULL,
                source_id INTEGER NOT NULL,
                model VARCHAR(64) NOT NULL,
                dim INTEGER NOT NULL,
                score DOUBLE PRECISION,
                payload JSONB,
                embedding vector(1536)
            )
            """
        )
        op.execute("CREATE INDEX ix_embeddings_source ON embeddings (source_type, source_id)")
    else:
        # sqlite fallback: omit VECTOR column
        op.create_table(
            "embeddings",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("source_type", sa.String(32), nullable=False),
            sa.Column("source_id", sa.Integer, nullable=False),
            sa.Column("model", sa.String(64), nullable=False),
            sa.Column("dim", sa.Integer, nullable=False),
            sa.Column("score", sa.Float, nullable=True),
            sa.Column("payload", sa.JSON, nullable=True),
        )


def downgrade() -> None:
    for t in ("embeddings", "feedback", "evidence", "defects", "cases", "runs"):
        op.execute(f"DROP TABLE IF EXISTS {t}")
    for enum_name in ("feedback_kind", "evidence_kind", "defect_status", "defect_severity", "case_result", "run_status"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
