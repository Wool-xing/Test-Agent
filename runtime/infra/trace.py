"""Correlation Trace ID (§补-22) — unique ID propagated through all layers.

Trace ID generated at entry (CLI/TUI/API), propagated downward via:
  - Internal calls: Context object
  - HTTP/API calls: X-Trace-Id header
  - LLM API calls: metadata field
  - Subprocesses: TAGENT_TRACE_ID env var
"""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager
from contextvars import ContextVar

# Context variable — thread/async safe, propagates through call chain
_current_trace_id: ContextVar[str] = ContextVar("trace_id", default="")


def generate_trace_id() -> str:
    """Generate a new UUID v7 trace ID."""
    return str(uuid.uuid4())


def set_trace_id(trace_id: str | None = None) -> str:
    """Set the current trace ID. Generates new one if not provided."""
    tid = trace_id or generate_trace_id()
    _current_trace_id.set(tid)
    os.environ["TAGENT_TRACE_ID"] = tid
    return tid


def get_trace_id() -> str:
    """Get current trace ID. Generates one if not set."""
    tid = _current_trace_id.get("")
    if not tid:
        tid = os.environ.get("TAGENT_TRACE_ID", "") or generate_trace_id()
        _current_trace_id.set(tid)
    return tid


def clear_trace_id() -> None:
    """Clear current trace ID."""
    _current_trace_id.set("")
    os.environ.pop("TAGENT_TRACE_ID", None)


@contextmanager
def trace_context(trace_id: str | None = None):
    """Context manager that sets trace ID for a block."""
    old = _current_trace_id.get("")
    tid = set_trace_id(trace_id)
    try:
        yield tid
    finally:
        _current_trace_id.set(old)
        if old:
            os.environ["TAGENT_TRACE_ID"] = old
        else:
            os.environ.pop("TAGENT_TRACE_ID", None)
