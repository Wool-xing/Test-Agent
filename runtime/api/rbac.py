"""Role‑based access control — pluggable, does NOT modify existing auth middleware.

Usage:
    from runtime.api.rbac import require_role, Role

    @app.get("/admin")
    @require_role(Role.ADMIN)
    def admin_only(): ...

Activation: set TAGENT_RBAC_ENABLED=1 and configure TAGENT_ADMIN_TOKENS.
When disabled (default), all endpoints behave as before.
"""

from __future__ import annotations

import os
from enum import Enum
from functools import wraps
from typing import Callable, List, Optional

from loguru import logger


class Role(str, Enum):
    ADMIN = "admin"
    LEAD = "lead"
    TESTER = "tester"
    VIEWER = "viewer"


# Default: 1 admin token for bootstrap. Override via TAGENT_ADMIN_TOKENS (comma‑separated).
def _load_tokens() -> dict[str, Role]:
    tokens: dict[str, Role] = {}
    admin_tokens = os.getenv("TAGENT_ADMIN_TOKENS", "")
    lead_tokens = os.getenv("TAGENT_LEAD_TOKENS", "")
    tester_tokens = os.getenv("TAGENT_TESTER_TOKENS", "")
    viewer_tokens = os.getenv("TAGENT_VIEWER_TOKENS", "")

    for t in admin_tokens.split(","):
        t = t.strip()
        if t:
            tokens[t] = Role.ADMIN
    for t in lead_tokens.split(","):
        t = t.strip()
        if t:
            tokens[t] = Role.LEAD
    for t in tester_tokens.split(","):
        t = t.strip()
        if t:
            tokens[t] = Role.TESTER
    for t in viewer_tokens.split(","):
        t = t.strip()
        if t:
            tokens[t] = Role.VIEWER

    # Fallback: single API auth token → admin
    api_token = os.getenv("TAGENT_API_AUTH_TOKEN", "")
    if api_token and api_token not in tokens:
        tokens[api_token] = Role.ADMIN

    return tokens


def _rbac_enabled() -> bool:
    return os.getenv("TAGENT_RBAC_ENABLED", "0") == "1"


def resolve_role(token: str) -> Optional[Role]:
    """Resolve a bearer token to a role. Returns None if RBAC disabled or token unknown."""
    if not _rbac_enabled():
        return Role.ADMIN  # when off, everyone is admin (backward compat)
    return _load_tokens().get(token)


def require_role(required: Role) -> Callable:
    """Decorator: require minimum role for a FastAPI endpoint.

    When RBAC is disabled (default), always passes.
    """

    ROLE_LEVEL = {Role.ADMIN: 4, Role.LEAD: 3, Role.TESTER: 2, Role.VIEWER: 1}

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
            if not _rbac_enabled():
                return await func(*args, **kwargs)

            # Try to extract token from kwargs (FastAPI-injected)
            request = kwargs.get("request")
            if request is None:
                # Try args
                from fastapi import Request
                for a in args:
                    if isinstance(a, Request):
                        request = a
                        break

            token: str | None = None
            if request:
                auth = request.headers.get("Authorization", "")
                if auth.startswith("Bearer "):
                    token = auth[7:]

            if not token:
                logger.warning("RBAC: no token, access denied")
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "Authentication required"}, status_code=401)

            role = resolve_role(token)
            if role is None:
                logger.warning("RBAC: unknown token")
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": "Invalid token"}, status_code=403)

            if ROLE_LEVEL.get(role, 0) < ROLE_LEVEL.get(required, 0):
                logger.warning(f"RBAC: role {role.value} < required {required.value}")
                from fastapi.responses import JSONResponse
                return JSONResponse({"detail": f"Role {required.value} required"}, status_code=403)

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def get_permissions(role: Role) -> list[str]:
    """Return allowed actions for a given role."""
    permissions: dict[Role, list[str]] = {
        Role.ADMIN: ["*"],
        Role.LEAD: ["run.start", "run.cancel", "report.view", "dashboard.view", "config.read", "agent.list"],
        Role.TESTER: ["run.start", "report.view", "dashboard.view", "agent.list"],
        Role.VIEWER: ["report.view", "dashboard.view", "agent.list"],
    }
    return permissions.get(role, [])
