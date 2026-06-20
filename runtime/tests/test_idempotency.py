"""TDD tests for Idempotency + Retry + Dead Letter Queue (§补-18)."""

import time

import pytest

from runtime.infra.idempotency import (
    IdempotencyStore,
    TaskStatus,
    DeadLetterQueue,
    DeadLetterEntry,
    make_idempotency_key,
    retry_with_backoff,
)


class TestIdempotencyStore:
    def test_unique_keys_independent(self):
        """Different keys should be tracked independently."""
        store = IdempotencyStore()
        store.mark_running("key-1")
        store.mark_success("key-1", "result-1")
        assert store.is_duplicate("key-1") is True
        assert store.is_duplicate("key-2") is False

    def test_running_not_duplicate(self):
        """Running tasks are not considered duplicates."""
        store = IdempotencyStore()
        store.mark_running("key-1")
        assert store.is_duplicate("key-1") is False

    def test_failed_can_retry(self):
        """Failed tasks can be retried (not duplicates)."""
        store = IdempotencyStore()
        store.mark_running("key-1")
        store.mark_failed("key-1", "timeout")
        assert store.is_duplicate("key-1") is False

    def test_three_failures_goes_dead(self):
        """After 3 failures, task goes to DEAD status."""
        store = IdempotencyStore()
        store.mark_running("key-1")
        store.mark_failed("key-1", "error1")
        store.mark_failed("key-1", "error2")
        store.mark_failed("key-1", "error3")
        dead = store.get_dead_letters()
        assert len(dead) == 1
        assert dead[0].status == TaskStatus.DEAD

    def test_replay_dead(self):
        """Dead letters can be replayed."""
        store = IdempotencyStore()
        store.mark_running("key-1")
        for _ in range(3):
            store.mark_failed("key-1", "error")
        assert store.replay_dead("key-1") is True
        assert len(store.get_dead_letters()) == 0


class TestMakeIdempotencyKey:
    def test_deterministic(self):
        """Same inputs should produce same key."""
        k1 = make_idempotency_key("t1", "2026-01-01", {"a": 1})
        k2 = make_idempotency_key("t1", "2026-01-01", {"a": 1})
        assert k1 == k2

    def test_different_params(self):
        """Different params should produce different keys."""
        k1 = make_idempotency_key("t1", "2026-01-01", {"a": 1})
        k2 = make_idempotency_key("t1", "2026-01-01", {"a": 2})
        assert k1 != k2


class TestRetryWithBackoff:
    def test_success_first_attempt(self):
        """Successful call should not retry."""
        calls = []
        def fn():
            calls.append(1)
            return "ok"
        result = retry_with_backoff(fn, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert len(calls) == 1

    def test_retry_on_failure(self):
        """Failed call should retry."""
        calls = []
        def fn():
            calls.append(1)
            if len(calls) < 2:
                raise ValueError("fail")
            return "ok"
        result = retry_with_backoff(fn, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert len(calls) == 2

    def test_max_retries_exceeded(self):
        """Should raise after max retries."""
        call_count = [0]
        def fn():
            call_count[0] += 1
            raise ValueError("always fail")
        with pytest.raises(ValueError, match="always fail"):
            retry_with_backoff(fn, max_retries=2, base_delay=0.01)
        assert call_count[0] == 3  # initial attempt + 2 retries


class TestDeadLetterQueue:
    def test_push_and_list(self):
        """DLQ should store entries."""
        dlq = DeadLetterQueue()
        dlq.push(DeadLetterEntry(task_id="t1", idempotency_key="k1", error="timeout"))
        assert len(dlq) == 1
        entries = dlq.list_entries()
        assert entries[0].task_id == "t1"

    def test_retry_removes_entry(self):
        """Retry should remove from DLQ."""
        dlq = DeadLetterQueue()
        dlq.push(DeadLetterEntry(task_id="t1", idempotency_key="k1", error="timeout"))
        entry = dlq.retry("t1")
        assert entry is not None
        assert len(dlq) == 0

    def test_retry_nonexistent(self):
        """Retrying nonexistent task returns None."""
        dlq = DeadLetterQueue()
        assert dlq.retry("nonexistent") is None
