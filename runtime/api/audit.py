"""Audit trail with cryptographic hash-chain integrity.

Every audit entry is linked to its predecessor via SHA-256, forming a
tamper-evident chain. Breaking the chain or modifying any entry is
detectable via verify_integrity().

Storage: SQLite (file or :memory: for testing).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class AuditEntry:
    """A single immutable audit record in the hash chain."""

    id: str
    timestamp: str
    actor: str  # user ID or agent ID
    action: str  # e.g. "agent.decision", "test.execute", "gate.evaluate"
    resource: str  # what was acted on
    details: dict  # action-specific payload
    integrity_hash: str = ""  # SHA-256 of (prev_hash + entry_data)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "action": self.action,
            "resource": self.resource,
            "details": self.details,
            "integrity_hash": self.integrity_hash,
        }


class AuditTrail:
    """Tamper-evident audit log with cryptographic hash chaining.

    Each entry's hash = SHA-256(prev_entry.hash + serialized_entry_data).
    This creates a blockchain-like chain where any modification to any
    entry invalidates all subsequent hashes.

    Usage:
        audit = AuditTrail("workspace/audit.db")
        entry = audit.record("user1", "test.run", "smoke-test", {"status": "pass"})
        ok, msg = audit.verify_integrity()
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self._conn = conn
        return self._conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL,
                action TEXT NOT NULL,
                resource TEXT NOT NULL,
                details TEXT NOT NULL DEFAULT '{}',
                integrity_hash TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log(actor)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)
            """
        )
        conn.commit()

    # ── Hash chain helpers ──────────────────────────────────────

    @staticmethod
    def _compute_hash(prev_hash: str, entry_data: str) -> str:
        """SHA-256 of (previous hash + serialized entry data)."""
        combined = f"{prev_hash}:{entry_data}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def _get_last_hash(self) -> str:
        """Get the integrity_hash of the most recent entry."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT integrity_hash FROM audit_log ORDER BY timestamp DESC, rowid DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return "0" * 64  # Genesis hash
        return row["integrity_hash"]

    def _serialize_entry(self, entry: AuditEntry) -> str:
        """Serialize entry data for hashing (without the hash field itself)."""
        data = {
            "id": entry.id,
            "timestamp": entry.timestamp,
            "actor": entry.actor,
            "action": entry.action,
            "resource": entry.resource,
            "details": entry.details,
        }
        return json.dumps(data, sort_keys=True, ensure_ascii=False)

    # ── Public API ──────────────────────────────────────────────

    def record(
        self,
        actor: str,
        action: str,
        resource: str,
        details: dict | None = None,
    ) -> AuditEntry:
        """Record a new audit entry and return it with its integrity hash."""
        entry = AuditEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            action=action,
            resource=resource,
            details=details or {},
        )

        prev_hash = self._get_last_hash()
        entry_data = self._serialize_entry(entry)
        entry.integrity_hash = self._compute_hash(prev_hash, entry_data)

        conn = self._get_conn()
        conn.execute(
            "INSERT INTO audit_log (id, timestamp, actor, action, resource, details, integrity_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                entry.id,
                entry.timestamp,
                entry.actor,
                entry.action,
                entry.resource,
                json.dumps(entry.details, ensure_ascii=False),
                entry.integrity_hash,
            ),
        )
        conn.commit()
        logger_ = __import__("loguru", fromlist=["logger"]).logger
        logger_.debug("audit: {} {} {}", actor, action, resource)
        return entry

    def verify_integrity(self) -> tuple[bool, str]:
        """Verify the entire hash chain.

        Returns:
            (True, "ok") if all entries are consistent.
            (False, message) describing the first inconsistency found.
        """
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM audit_log ORDER BY timestamp ASC, rowid ASC"
        ).fetchall()

        if not rows:
            return True, "No entries to verify"

        expected_prev_hash = "0" * 64
        for row in rows:
            entry = AuditEntry(
                id=row["id"],
                timestamp=row["timestamp"],
                actor=row["actor"],
                action=row["action"],
                resource=row["resource"],
                details=json.loads(row["details"]),
                integrity_hash=row["integrity_hash"],
            )
            entry_data = self._serialize_entry(entry)
            computed_hash = self._compute_hash(expected_prev_hash, entry_data)

            if computed_hash != entry.integrity_hash:
                return False, (
                    f"Hash mismatch at entry {entry.id}: "
                    f"expected {computed_hash[:16]}..., got {entry.integrity_hash[:16]}..."
                )

            expected_prev_hash = entry.integrity_hash

        return True, "Integrity verified — all hashes consistent"

    def query(
        self,
        actor: str | None = None,
        action: str | None = None,
        since: str | None = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query audit entries with optional filters.

        Args:
            actor: Filter by actor ID.
            action: Filter by action prefix (e.g. "agent." matches all agent actions).
            since: ISO timestamp — only return entries after this time.
            limit: Maximum entries to return.
        """
        conn = self._get_conn()
        conditions: list[str] = []
        params: list[Any] = []

        if actor:
            conditions.append("actor = ?")
            params.append(actor)

        if action:
            conditions.append("action LIKE ?")
            params.append(f"{action}%")

        if since:
            conditions.append("timestamp > ?")
            params.append(since)

        where = " AND ".join(conditions) if conditions else "1=1"
        query_str = f"SELECT * FROM audit_log WHERE {where} ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query_str, params).fetchall()
        return [
            AuditEntry(
                id=row["id"],
                timestamp=row["timestamp"],
                actor=row["actor"],
                action=row["action"],
                resource=row["resource"],
                details=json.loads(row["details"]),
                integrity_hash=row["integrity_hash"],
            )
            for row in rows
        ]

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
