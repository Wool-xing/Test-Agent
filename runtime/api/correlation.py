"""Request ID / correlation middleware for distributed tracing.

Inject X-Request-ID into every request/response. Propagate via loguru context.
"""

from __future__ import annotations

import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


HEADER_REQUEST_ID = "X-Request-ID"
HEADER_CORRELATION_ID = "X-Correlation-ID"


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Inject X-Request-ID and X-Correlation-ID headers.

    - If incoming request has X-Request-ID, reuse it (propagation)
    - Otherwise generate a new UUID
    - Always set X-Correlation-ID (same value if not provided)
    - Add response header for client traceability
    """

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        request_id = request.headers.get(HEADER_REQUEST_ID) or request.headers.get(
            "x-request-id", ""
        ) or str(uuid.uuid4())
        correlation_id = request.headers.get(HEADER_CORRELATION_ID) or request.headers.get(
            "x-correlation-id", request_id
        )

        # Store in request state for downstream access
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        try:
            from loguru import logger
            with logger.contextualize(request_id=request_id, correlation_id=correlation_id):
                response = await call_next(request)
        except Exception:  # noqa: BLE001 — loguru may not be available
            response = await call_next(request)

        response.headers[HEADER_REQUEST_ID] = request_id
        response.headers[HEADER_CORRELATION_ID] = correlation_id
        return response


def get_request_id(request: Request) -> str:
    """Get request ID from request state (set by middleware)."""
    return getattr(request.state, "request_id", "unknown")


def get_correlation_id(request: Request) -> str:
    """Get correlation ID from request state."""
    return getattr(request.state, "correlation_id", "unknown")
