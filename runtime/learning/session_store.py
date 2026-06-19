"""SQLite + FTS5 persistent session storage for cross-session learning.

Stores full SessionRecord objects with JSON-serialized complex fields.
FTS5 full-text search over target, outcomes, and agent decision content.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path


@dataclass
class SessionRecord:
    """A single test session record capturing routing, execution, and outcomes."""

    id: str
    created_at: str
    target: str  # What was tested
    routing_decision: dict  # The RoutingDecision JSON
    dag_results: list[dict]  # Each node's result
    outcomes: dict  # Pass/fail/skip counts, e.g. {"passed": 10, "failed": 2, "skipped": 1}
    agent_decisions: list[dict]  # Key decisions made by agents
    human_feedback: str | None = None
    extracted_patterns: list[str] = field(default_factory=list)


class SessionStore:
    """SQLite + FTS5 persistent session storage with full-text search.

    Usage:
        store = SessionStore(Path("workspace/_test_sessions.db"))
        store.save_session(SessionRecord(id="abc", ...))
        results = store.search("login failure")
        similar = store.find_similar("web auth test")
        stats = store.get_stats(days=30)
        recent = store.list_recent(limit=20)
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    # ── connection ────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(str(self.db_path))
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        return c

    # ── schema ────────────────────────────────────────────────────

    def _init_db(self) -> None:
        with self._conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id                TEXT PRIMARY KEY,
                    created_at        TEXT NOT NULL,
                    target            TEXT NOT NULL,
                    routing_decision  TEXT NOT NULL,
                    dag_results       TEXT NOT NULL,
                    outcomes          TEXT NOT NULL,
                    agent_decisions   TEXT NOT NULL,
                    human_feedback    TEXT,
                    extracted_patterns TEXT NOT NULL
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5(
                    target,
                    outcomes_summary,
                    agent_chain,
                    human_feedback,
                    content='sessions',
                    content_rowid='rowid',
                    tokenize='unicode61'
                );

                -- Triggers to keep FTS5 in sync
                CREATE TRIGGER IF NOT EXISTS sessions_ai AFTER INSERT ON sessions BEGIN
                    INSERT INTO sessions_fts(rowid, target, outcomes_summary, agent_chain, human_feedback)
                    VALUES (
                        new.rowid,
                        new.target,
                        new.outcomes,
                        (SELECT json_group_array(json_extract(value, '$.agent')) FROM json_each(new.agent_decisions)),
                        new.human_feedback
                    );
                END;

                CREATE TRIGGER IF NOT EXISTS sessions_ad AFTER DELETE ON sessions BEGIN
                    INSERT INTO sessions_fts(sessions_fts, rowid, target, outcomes_summary, agent_chain, human_feedback)
                    VALUES ('delete', old.rowid, old.target, old.outcomes, '', old.human_feedback);
                END;

                CREATE TRIGGER IF NOT EXISTS sessions_au AFTER UPDATE ON sessions BEGIN
                    INSERT INTO sessions_fts(sessions_fts, rowid, target, outcomes_summary, agent_chain, human_feedback)
                    VALUES ('delete', old.rowid, old.target, old.outcomes, '', old.human_feedback);
                    INSERT INTO sessions_fts(rowid, target, outcomes_summary, agent_chain, human_feedback)
                    VALUES (
                        new.rowid,
                        new.target,
                        new.outcomes,
                        (SELECT json_group_array(json_extract(value, '$.agent')) FROM json_each(new.agent_decisions)),
                        new.human_feedback
                    );
                END;

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);
                CREATE INDEX IF NOT EXISTS idx_sessions_target ON sessions(target);
                """
            )

    # ── CRUD ──────────────────────────────────────────────────────

    def save_session(self, s: SessionRecord) -> str:
        """Persist a session record. Returns the session id."""
        with self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO sessions
                   (id, created_at, target, routing_decision, dag_results,
                    outcomes, agent_decisions, human_feedback, extracted_patterns)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    s.id,
                    s.created_at,
                    s.target,
                    json.dumps(s.routing_decision, ensure_ascii=False),
                    json.dumps(s.dag_results, ensure_ascii=False),
                    json.dumps(s.outcomes, ensure_ascii=False),
                    json.dumps(s.agent_decisions, ensure_ascii=False),
                    s.human_feedback,
                    json.dumps(s.extracted_patterns, ensure_ascii=False),
                ),
            )
        return s.id

    def get_session(self, session_id: str) -> SessionRecord | None:
        """Retrieve a single session by id."""
        with self._conn() as c:
            row = c.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return self._row_to_record(row) if row else None

    # ── search ────────────────────────────────────────────────────

    def search(self, query: str, limit: int = 10) -> list[SessionRecord]:
        """FTS5 full-text search over sessions. Returns matching records."""
        # Sanitize query for FTS5: escape double-quotes, wrap phrases
        safe_query = query.replace('"', '""')
        with self._conn() as c:
            rows = c.execute(
                """SELECT s.* FROM sessions s
                   INNER JOIN sessions_fts f ON s.rowid = f.rowid
                   WHERE sessions_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (safe_query, limit),
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def find_similar(self, target: str, limit: int = 5) -> list[SessionRecord]:
        """Find sessions with similar targets using LIKE matching.

        Tries prefix, suffix, and word-based matching for robustness.
        """
        words = [w for w in target.split() if len(w) >= 3]
        if not words:
            with self._conn() as c:
                rows = c.execute(
                    "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [self._row_to_record(r) for r in rows]

        # Build LIKE clauses for each word
        like_clauses = " OR ".join(["target LIKE ?" for _ in words])
        params = [f"%{w}%" for w in words]
        with self._conn() as c:
            rows = c.execute(
                f"""SELECT * FROM sessions
                    WHERE {like_clauses}
                    ORDER BY created_at DESC
                    LIMIT ?""",
                [*params, limit],
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    # ── stats ─────────────────────────────────────────────────────

    def get_stats(self, days: int = 30) -> dict:
        """Aggregate stats for the last N days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        with self._conn() as c:
            row = c.execute(
                """SELECT
                     COUNT(*) AS total_sessions,
                     COUNT(DISTINCT target) AS unique_targets,
                     MIN(created_at) AS earliest,
                     MAX(created_at) AS latest
                   FROM sessions
                   WHERE created_at >= ?""",
                (cutoff,),
            ).fetchone()

            # Aggregate outcomes across sessions
            outcome_rows = c.execute(
                "SELECT outcomes FROM sessions WHERE created_at >= ?",
                (cutoff,),
            ).fetchall()

        total_passed = 0
        total_failed = 0
        total_skipped = 0
        for orow in outcome_rows:
            try:
                o = json.loads(orow["outcomes"])
                total_passed += o.get("passed", 0)
                total_failed += o.get("failed", 0)
                total_skipped += o.get("skipped", 0)
            except (json.JSONDecodeError, TypeError):
                pass

        total_cases = total_passed + total_failed + total_skipped
        pass_rate = (total_passed / total_cases * 100) if total_cases > 0 else 0.0

        return {
            "total_sessions": row["total_sessions"],
            "unique_targets": row["unique_targets"],
            "earliest": row["earliest"],
            "latest": row["latest"],
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "total_cases": total_cases,
            "pass_rate_pct": round(pass_rate, 1),
            "period_days": days,
        }

    # ── listing ───────────────────────────────────────────────────

    def list_recent(self, limit: int = 20) -> list[SessionRecord]:
        """Return the most recent sessions."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    # ── helpers ───────────────────────────────────────────────────

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> SessionRecord:
        return SessionRecord(
            id=row["id"],
            created_at=row["created_at"],
            target=row["target"],
            routing_decision=json.loads(row["routing_decision"]),
            dag_results=json.loads(row["dag_results"]),
            outcomes=json.loads(row["outcomes"]),
            agent_decisions=json.loads(row["agent_decisions"]),
            human_feedback=row["human_feedback"],
            extracted_patterns=json.loads(row["extracted_patterns"]),
        )
