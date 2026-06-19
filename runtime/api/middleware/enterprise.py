"""Composite enterprise middleware stack.

Combines SSO authentication, RBAC authorization, and audit logging into
a single middleware that can be added to a FastAPI application.

Usage:
    sso = SSOManager(SSOConfig(...))
    rbac = RBAC()
    audit = AuditTrail("workspace/audit.db")

    app.add_middleware(
        EnterpriseMiddleware,
        sso_manager=sso,
        rbac=rbac,
        audit=audit,
        exclude_paths=["/health", "/docs", "/openapi.json"],
    )
"""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import Response

from runtime.api.audit import AuditTrail
from runtime.api.auth.rbac import RBAC, Permission, Role
from runtime.api.auth.sso import SSOManager


class EnterpriseMiddleware:
    """Composite middleware: SSO auth -> RBAC check -> Audit.

    This is a Starlette-style pure-ASGI middleware that:
    1. Validates the SSO token (if present) on protected routes.
    2. Extracts user role from token claims.
    3. Logs the request to the audit trail.
    4. Attaches user context to request.state for downstream handlers.

    Does NOT replace per-endpoint @rbac.require() decorators — those
    provide granular permission checks. This middleware handles
    authentication and request-level audit.
    """

    def __init__(
        self,
        app,
        *,
        sso_manager: SSOManager,
        rbac: RBAC,
        audit: AuditTrail,
        exclude_paths: list[str] | None = None,
    ) -> None:
        self.app = app
        self.sso = sso_manager
        self.rbac = rbac
        self.audit = audit
        self.exclude_paths = set(
            exclude_paths or ["/health", "/health/deep", "/docs", "/openapi.json"]
        )

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)

        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            await self.app(scope, receive, send)
            return

        # Extract and validate SSO token
        auth = request.headers.get("Authorization", "")
        user_id = "anonymous"
        user_role = Role.VIEWER

        if auth.startswith("Bearer "):
            token = auth[7:]
            try:
                claims = await self.sso.validate_token_async(token)
                user_id = claims.get("sub") or claims.get("email", "unknown")
                # Resolve role from claims
                roles = claims.get("roles", [])
                if "admin" in roles:
                    user_role = Role.ADMIN
                elif "manager" in roles:
                    user_role = Role.MANAGER
                elif "tester" in roles:
                    user_role = Role.TESTER
                else:
                    user_role = Role.VIEWER

                # Attach to request state
                request.state.user = claims
                request.state.user_id = user_id
                request.state.role = user_role
            except Exception:
                # Token invalid — record attempt and reject
                self.audit.record(
                    actor="anonymous",
                    action="auth.failed",
                    resource=request.url.path,
                    details={"method": request.method, "ip": request.client.host if request.client else ""},
                )
                response = Response(
                    content='{"detail":"Invalid token"}',
                    status_code=401,
                    media_type="application/json",
                )
                await response(scope, receive, send)
                return

        # Record request in audit trail (before processing)
        self.audit.record(
            actor=user_id,
            action=f"api.{request.method.lower()}",
            resource=request.url.path,
            details={
                "method": request.method,
                "query_params": str(request.query_params),
                "role": user_role.value,
            },
        )

        await self.app(scope, receive, send)


def create_enterprise_middleware(
    sso: SSOManager,
    rbac: RBAC,
    audit: AuditTrail,
    *,
    exclude_paths: list[str] | None = None,
) -> type:
    """Factory: create an EnterpriseMiddleware class bound to the given instances.

    Returns a middleware class suitable for `app.add_middleware()`.

    Usage:
        Middleware = create_enterprise_middleware(sso, rbac, audit)
        app.add_middleware(Middleware)
    """

    class BoundEnterpriseMiddleware:
        def __init__(self, app, **kwargs: Any) -> None:
            self._inner = EnterpriseMiddleware(
                app,
                sso_manager=sso,
                rbac=rbac,
                audit=audit,
                exclude_paths=exclude_paths,
            )

        async def __call__(self, scope, receive, send) -> None:
            await self._inner(scope, receive, send)

    return BoundEnterpriseMiddleware
