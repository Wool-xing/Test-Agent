"""Multi-tenant data isolation — V2 with full tenant lifecycle management.

Builds on the V1 tenancy module (contextvars-based) with tenant creation,
query scoping, and access verification suitable for enterprise deployments.

Usage:
    from runtime.api.tenancy_v2 import TenantManager

    tm = TenantManager()
    tenant = tm.create_tenant("Acme Corp", "admin@acme.com")
    scoped = tm.scope_query("SELECT * FROM runs", tenant["id"])
    ok = tm.verify_access("user-123", tenant["id"])
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from loguru import logger


class TenantManager:
    """Full tenant lifecycle: create, retrieve, scope, verify.

    Uses SQLite for tenant metadata. Query scoping injects WHERE tenant_id=
    clauses for data isolation.
    """

    def __init__(self, db_path: str = "") -> None:
        if not db_path:
            db_path = os.environ.get("TAGENT_TENANT_DB", "workspace/tenants.db")
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
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tenants (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                admin_email TEXT NOT NULL,
                created_at TEXT NOT NULL,
                settings TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS tenant_members (
                tenant_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                joined_at TEXT NOT NULL,
                PRIMARY KEY (tenant_id, user_id),
                FOREIGN KEY (tenant_id) REFERENCES tenants(id)
            );
            """
        )
        conn.commit()

    # ── Tenant CRUD ─────────────────────────────────────────────

    def create_tenant(self, name: str, admin_email: str) -> dict:
        """Create a new tenant and return its metadata."""
        tenant_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        conn = self._get_conn()
        conn.execute(
            "INSERT INTO tenants (id, name, admin_email, created_at, settings) VALUES (?, ?, ?, ?, '{}')",
            (tenant_id, name, admin_email, now),
        )
        conn.commit()
        logger.info("tenant created: {} ({})", name, tenant_id)

        return {
            "id": tenant_id,
            "name": name,
            "admin_email": admin_email,
            "created_at": now,
        }

    def get_tenant(self, tenant_id: str) -> dict | None:
        """Retrieve tenant metadata by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
        if row is None:
            return None
        return dict(row)

    def list_tenants(self) -> list[dict]:
        """List all tenants."""
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM tenants ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]

    def delete_tenant(self, tenant_id: str) -> bool:
        """Delete a tenant and its memberships."""
        conn = self._get_conn()
        conn.execute("DELETE FROM tenant_members WHERE tenant_id = ?", (tenant_id,))
        cursor = conn.execute("DELETE FROM tenants WHERE id = ?", (tenant_id,))
        conn.commit()
        return cursor.rowcount > 0

    # ── Query Scoping ──────────────────────────────────────────

    def scope_query(self, base_query: str, tenant_id: str) -> str:
        """Inject a WHERE tenant_id=? clause into a SQL query for data isolation.

        Handles SELECT, UPDATE, and DELETE statements by adding or modifying
        the WHERE clause to filter by tenant.

        Args:
            base_query: The original query (e.g. "SELECT * FROM runs").
            tenant_id: The tenant to scope to.

        Returns:
            Modified query with tenant filter injected.
        """
        query = base_query.strip().rstrip(";")

        # Determine the tenant column name
        tenant_col = self._find_tenant_column(query)

        if " WHERE " in query.upper():
            # Append to existing WHERE
            idx = query.upper().index(" WHERE ") + 7
            return f"{query[:idx]}{tenant_col} = '{tenant_id}' AND {query[idx:]}"
        elif " ORDER BY " in query.upper():
            idx = query.upper().index(" ORDER BY ")
            return f"{query[:idx]} WHERE {tenant_col} = '{tenant_id}' {query[idx:]}"
        elif " GROUP BY " in query.upper():
            idx = query.upper().index(" GROUP BY ")
            return f"{query[:idx]} WHERE {tenant_col} = '{tenant_id}' {query[idx:]}"
        elif " LIMIT " in query.upper():
            idx = query.upper().index(" LIMIT ")
            return f"{query[:idx]} WHERE {tenant_col} = '{tenant_id}' {query[idx:]}"
        else:
            return f"{query} WHERE {tenant_col} = '{tenant_id}'"

    @staticmethod
    def _find_tenant_column(query: str) -> str:
        """Heuristic: detect the tenant column from the query.

        Common patterns: tenant_id, tenant, org_id, organization_id.
        Defaults to 'tenant_id'.
        """
        upper = query.upper()
        for col in ["tenant_id", "tenant", "org_id", "organization_id"]:
            if col.upper() in upper:
                return col
        return "tenant_id"

    # ── Access Verification ─────────────────────────────────────

    def verify_access(self, user_id: str, tenant_id: str) -> bool:
        """Check whether a user has access to a given tenant.

        Returns True if the user is a member of the tenant.
        """
        conn = self._get_conn()
        row = conn.execute(
            "SELECT 1 FROM tenant_members WHERE tenant_id = ? AND user_id = ?",
            (tenant_id, user_id),
        ).fetchone()
        return row is not None

    def add_member(self, tenant_id: str, user_id: str, role: str = "member") -> bool:
        """Add a user to a tenant. Returns True if added, False if already exists."""
        conn = self._get_conn()
        try:
            conn.execute(
                "INSERT INTO tenant_members (tenant_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)",
                (tenant_id, user_id, role, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_member(self, tenant_id: str, user_id: str) -> bool:
        """Remove a user from a tenant."""
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM tenant_members WHERE tenant_id = ? AND user_id = ?",
            (tenant_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0

    def get_members(self, tenant_id: str) -> list[dict]:
        """List all members of a tenant."""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT user_id, role, joined_at FROM tenant_members WHERE tenant_id = ? ORDER BY joined_at",
            (tenant_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
