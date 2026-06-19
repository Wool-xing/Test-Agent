"""Role-Based Access Control — permission-level authorization.

Provides Role and Permission enums, role-to-permission mappings,
and decorators for FastAPI endpoint protection.

Usage:
    from runtime.api.auth.rbac import RBAC, Role, Permission

    rbac = RBAC()

    @app.get("/admin")
    @rbac.require(Permission.MANAGE_USERS)
    async def admin_only(request: Request): ...
"""

from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any

from fastapi import Request
from loguru import logger


class Role(str, Enum):
    """User roles in ascending privilege order."""

    ADMIN = "admin"
    MANAGER = "manager"
    TESTER = "tester"
    VIEWER = "viewer"


class Permission(str, Enum):
    """Granular permissions for resource actions."""

    RUN_TESTS = "run:tests"
    VIEW_RESULTS = "view:results"
    MANAGE_AGENTS = "manage:agents"
    MANAGE_PLUGINS = "manage:plugins"
    MANAGE_USERS = "manage:users"
    VIEW_AUDIT = "view:audit"
    MANAGE_TENANT = "manage:tenant"


ROLE_PERMISSIONS: dict[Role, list[Permission]] = {
    Role.ADMIN: [p for p in Permission],
    Role.MANAGER: [
        Permission.RUN_TESTS,
        Permission.VIEW_RESULTS,
        Permission.MANAGE_AGENTS,
        Permission.MANAGE_PLUGINS,
        Permission.VIEW_AUDIT,
    ],
    Role.TESTER: [
        Permission.RUN_TESTS,
        Permission.VIEW_RESULTS,
    ],
    Role.VIEWER: [
        Permission.VIEW_RESULTS,
        Permission.VIEW_AUDIT,
    ],
}


class RBAC:
    """Permission-based access control engine.

    Supports both imperative checks and declarative decorators.
    When disabled (default), all checks pass — backward compatible.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._permissions: dict[Role, set[Permission]] = {
            role: set(perms) for role, perms in ROLE_PERMISSIONS.items()
        }

    def has_permission(self, role: Role, permission: Permission) -> bool:
        """Check whether a role grants a specific permission."""
        if not self.enabled:
            return True
        allowed = self._permissions.get(role, set())
        return permission in allowed

    def check(self, role: Role, required: Permission) -> None:
        """Raise HTTPException(403) if role lacks the required permission.

        Use as a guard clause in endpoint handlers:
            rbac.check(user_role, Permission.RUN_TESTS)
        """
        if not self.enabled:
            return
        if not self.has_permission(role, required):
            msg = f"Permission '{required.value}' requires role higher than {role.value}"
            logger.warning("RBAC denied: {}", msg)
            from fastapi import HTTPException

            raise HTTPException(status_code=403, detail=msg)

    def require(self, permission: Permission) -> Callable:
        """Decorator: require a specific permission for a FastAPI endpoint.

        Extracts the authenticated user's role from `request.state.role` or
        from `request.state.user_roles` (set by auth middleware).

        When RBAC is disabled, always passes.

        Usage:
            @app.get("/admin/users")
            @rbac.require(Permission.MANAGE_USERS)
            async def manage_users(request: Request): ...
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:  # type: ignore[no-untyped-def]
                if not self.enabled:
                    return await func(*args, **kwargs)

                # Extract the Request object
                request: Request | None = kwargs.get("request")
                if request is None:
                    for a in args:
                        if isinstance(a, Request):
                            request = a
                            break

                if request is None:
                    logger.warning("RBAC: no Request in endpoint params, denying")
                    from fastapi import HTTPException

                    raise HTTPException(status_code=403, detail="RBAC requires a Request parameter")

                # Resolve role from request state
                role_str: str | None = getattr(request.state, "role", None)
                if role_str is None:
                    # Try user_roles list (SSO middleware sets this)
                    user_roles: list[str] = getattr(request.state, "user_roles", [])
                    if "admin" in user_roles:
                        role_str = "admin"
                    elif "manager" in user_roles:
                        role_str = "manager"
                    elif "tester" in user_roles:
                        role_str = "tester"
                    else:
                        role_str = "viewer"

                try:
                    role = Role(role_str)
                except ValueError:
                    logger.warning("RBAC: unknown role '{}'", role_str)
                    from fastapi import HTTPException

                    raise HTTPException(status_code=403, detail=f"Unknown role: {role_str}")

                self.check(role, permission)
                return await func(*args, **kwargs)

            return wrapper

        return decorator

    def get_permissions(self, role: Role) -> list[str]:
        """Return list of permission string values for a given role."""
        perms = self._permissions.get(role, set())
        return sorted(p.value for p in perms)

    def grant_permission(self, role: Role, permission: Permission) -> None:
        """Add a permission to a role (runtime override)."""
        if role not in self._permissions:
            self._permissions[role] = set()
        self._permissions[role].add(permission)

    def revoke_permission(self, role: Role, permission: Permission) -> None:
        """Remove a permission from a role (runtime override)."""
        if role in self._permissions:
            self._permissions[role].discard(permission)
