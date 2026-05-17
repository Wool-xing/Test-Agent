"""Multi‑tenant utilities — pluggable, does NOT modify existing DB schema or queries.

Activation: set TAGENT_TENANCY_ENABLED=1 and configure TAGENT_TENANT_ID.
When disabled (default), all operations are single‑tenant (backward compat).

Design:
  - Uses contextvars for per‑request tenant propagation (no DB schema changes).
  - Existing queries are unchanged — tenancy is transparent when disabled.
  - Future: add tenant_id column to tables + filter in queries (Phase 5+).
"""

from __future__ import annotations

import contextvars
import os
from typing import Optional

from loguru import logger

_current_tenant: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_tenant", default=None
)


def tenancy_enabled() -> bool:
    return os.getenv("TAGENT_TENANCY_ENABLED", "0") == "1"


def set_current_tenant(tenant_id: str) -> None:
    """Set tenant for the current async context (request / task)."""
    _current_tenant.set(tenant_id)


def get_current_tenant() -> str | None:
    """Get current tenant, or None if tenancy disabled."""
    if not tenancy_enabled():
        return None
    return _current_tenant.get()


def resolve_tenant(headers: dict[str, str] | None = None) -> str:
    """Resolve tenant from headers or env. Falls back to 'default'.

    Header priority: X-Tenant-Id > TAGENT_TENANT_ID env > 'default'
    """
    if not tenancy_enabled():
        return "default"

    if headers:
        tid = headers.get("X-Tenant-Id", "").strip()
        if tid:
            return tid

    return os.getenv("TAGENT_TENANT_ID", "default")


def tenant_prefix(path: str) -> str:
    """Prefix a path or key with the current tenant for isolation.

    Example: 'workspace/reports' → 'tenant_acme/workspace/reports'
    When tenancy disabled, returns path unchanged.
    """
    tid = get_current_tenant()
    if not tid:
        return path
    return f"tenant_{tid}/{path}"


# ── Tenant‑aware resource naming ─────────────────────────────

def tenant_namespace(resource: str) -> str:
    """Generate a tenant‑scoped resource name.

    Example: (tenant='acme', resource='testcases') → 'acme/testcases'
    """
    tid = get_current_tenant()
    if not tid:
        return resource
    return f"{tid}/{resource}"


def tenant_info() -> dict:
    """Return current tenancy status for dashboard / debug."""
    return {
        "enabled": tenancy_enabled(),
        "current_tenant": get_current_tenant(),
        "default_tenant": os.getenv("TAGENT_TENANT_ID", "default"),
    }
