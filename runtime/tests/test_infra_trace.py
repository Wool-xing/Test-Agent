"""TDD tests for Trace ID system (§补-22)."""

import uuid

from runtime.infra.trace import (
    get_trace_id,
    set_trace_id,
    clear_trace_id,
    generate_trace_id,
    trace_context,
)


class TestTraceId:
    def test_generate_is_valid_uuid(self):
        """Generated trace ID should be valid UUID."""
        tid = generate_trace_id()
        uuid.UUID(tid)

    def test_set_and_get(self):
        """set_trace_id should be retrievable via get_trace_id."""
        tid = set_trace_id("test-trace-001")
        assert get_trace_id() == "test-trace-001"

    def test_auto_generate(self):
        """get_trace_id should auto-generate if not set."""
        clear_trace_id()
        tid = get_trace_id()
        assert len(tid) > 0
        uuid.UUID(tid)

    def test_context_manager(self):
        """trace_context should set and restore trace ID."""
        set_trace_id("outer")
        with trace_context("inner"):
            assert get_trace_id() == "inner"
        assert get_trace_id() == "outer"

    def test_clear(self):
        """clear_trace_id should remove current trace ID."""
        set_trace_id("test")
        clear_trace_id()
        tid = get_trace_id()
        assert tid != "test"
