"""Idempotency + Retry + Dead Letter Queue (§补-18).

Idempotency: Every task has a unique key. Execute-once semantics.
Retry: Exponential backoff with jitter. 3 retries max.
DLQ: Failed tasks go to dead letter queue for manual replay.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    DEAD = "dead"


@dataclass
class TaskRecord:
    idempotency_key: str
    status: TaskStatus
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    retry_count: int = 0
    result: Any = None
    error: str = ""


class IdempotencyStore:
    """Thread-safe store for idempotency keys."""

    def __init__(self, success_ttl: float = 86400, failed_ttl: float = 259200):
        self._store: dict[str, TaskRecord] = {}
        self._lock = threading.Lock()
        self._success_ttl = success_ttl   # 24h
        self._failed_ttl = failed_ttl     # 72h

    def is_duplicate(self, key: str) -> bool:
        """Check if key has already been successfully processed."""
        with self._lock:
            rec = self._store.get(key)
            if rec and rec.status == TaskStatus.SUCCESS:
                age = time.time() - (rec.completed_at or rec.created_at)
                if age < self._success_ttl:
                    return True
        return False

    def mark_running(self, key: str) -> None:
        with self._lock:
            self._store[key] = TaskRecord(idempotency_key=key, status=TaskStatus.RUNNING)

    def mark_success(self, key: str, result: Any = None) -> None:
        with self._lock:
            if key in self._store:
                self._store[key].status = TaskStatus.SUCCESS
                self._store[key].completed_at = time.time()
                self._store[key].result = result

    def mark_failed(self, key: str, error: str) -> None:
        with self._lock:
            if key in self._store:
                rec = self._store[key]
                rec.retry_count += 1
                rec.error = error
                if rec.retry_count >= 3:
                    rec.status = TaskStatus.DEAD
                else:
                    rec.status = TaskStatus.FAILED

    def get_dead_letters(self) -> list[TaskRecord]:
        with self._lock:
            return [r for r in self._store.values() if r.status == TaskStatus.DEAD]

    def replay_dead(self, key: str) -> bool:
        with self._lock:
            rec = self._store.get(key)
            if rec and rec.status == TaskStatus.DEAD:
                rec.status = TaskStatus.PENDING
                rec.retry_count = 0
                rec.error = ""
                return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired records. Returns count removed."""
        now = time.time()
        removed = 0
        with self._lock:
            expired = []
            for key, rec in self._store.items():
                age = now - (rec.completed_at or rec.created_at)
                if rec.status == TaskStatus.SUCCESS and age > self._success_ttl:
                    expired.append(key)
                elif rec.status in (TaskStatus.FAILED, TaskStatus.DEAD) and age > self._failed_ttl:
                    expired.append(key)
            for key in expired:
                del self._store[key]
                removed += 1
        return removed


def make_idempotency_key(task_id: str, triggered_at: str, params: dict) -> str:
    """Generate a deterministic idempotency key."""
    payload = f"{task_id}:{triggered_at}:{json.dumps(params, sort_keys=True)}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def retry_with_backoff(
    fn: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: float = 0.25,
) -> Any:
    """Execute fn with exponential backoff retry.

    Delays: 1s → 4s → 16s (with ±25% jitter)
    """
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                delay = min(base_delay * (4 ** attempt), max_delay)
                jitter_amount = delay * jitter * (2 * (hash(str(e)) % 100) / 100 - 1)
                time.sleep(delay + jitter_amount)
    raise last_exc


# Dead Letter Queue
@dataclass
class DeadLetterEntry:
    task_id: str
    idempotency_key: str
    error: str
    failed_at: float = field(default_factory=time.time)
    retry_count: int = 3


class DeadLetterQueue:
    """Persistent dead letter queue for failed tasks."""

    def __init__(self, max_entries: int = 1000):
        self._queue: list[DeadLetterEntry] = []
        self._lock = threading.Lock()
        self._max = max_entries

    def push(self, entry: DeadLetterEntry) -> None:
        with self._lock:
            self._queue.append(entry)
            if len(self._queue) > self._max:
                self._queue = self._queue[-self._max:]

    def list_entries(self) -> list[DeadLetterEntry]:
        with self._lock:
            return list(self._queue)

    def retry(self, task_id: str) -> DeadLetterEntry | None:
        with self._lock:
            for i, entry in enumerate(self._queue):
                if entry.task_id == task_id:
                    return self._queue.pop(i)
        return None

    def __len__(self) -> int:
        with self._lock:
            return len(self._queue)
