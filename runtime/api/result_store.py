"""Thread-safe result store with LRU eviction.

Replaces unbounded dict in main.py. Features:
- LRU eviction when max_entries exceeded
- TTL-based expiry (default 24h)
- Thread-safe operations
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any


class ResultStore:
    """Bounded, thread-safe store for run results."""

    def __init__(self, max_entries: int = 1000, ttl_seconds: int = 86400) -> None:
        self._max = max_entries
        self._ttl = ttl_seconds
        self._store: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self._lock = threading.Lock()

    def put(self, run_id: str, result: dict[str, Any]) -> None:
        """Store a result. Evicts oldest if over capacity."""
        with self._lock:
            self._evict_expired()
            if run_id in self._store:
                self._store.move_to_end(run_id)
            self._store[run_id] = (time.time(), result)
            self._store.move_to_end(run_id)
            while len(self._store) > self._max:
                self._store.popitem(last=False)

    def get(self, run_id: str) -> dict[str, Any] | None:
        """Get a result. Returns None if not found or expired."""
        with self._lock:
            entry = self._store.get(run_id)
            if entry is None:
                return None
            ts, result = entry
            if time.time() - ts > self._ttl:
                del self._store[run_id]
                return None
            self._store.move_to_end(run_id)
            return result

    def list_all(self) -> list[dict[str, Any]]:
        """List all non-expired results (most recent first)."""
        with self._lock:
            self._evict_expired()
            return [r for _, r in reversed(self._store.values())]

    def list_page(self, page: int = 1, per_page: int = 20) -> dict[str, Any]:
        """Paginated listing."""
        with self._lock:
            self._evict_expired()
            all_items = [r for _, r in reversed(self._store.values())]
            total = len(all_items)
            start = (page - 1) * per_page
            end = start + per_page
            return {
                "items": all_items[start:end],
                "total": total,
                "page": page,
                "per_page": per_page,
                "pages": (total + per_page - 1) // per_page if total > 0 else 1,
            }

    def remove(self, run_id: str) -> bool:
        """Remove a result. Returns True if removed."""
        with self._lock:
            if run_id in self._store:
                del self._store[run_id]
                return True
            return False

    def __len__(self) -> int:
        with self._lock:
            self._evict_expired()
            return len(self._store)

    def __contains__(self, run_id: str) -> bool:
        return self.get(run_id) is not None

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [k for k, (ts, _) in self._store.items() if now - ts > self._ttl]
        for k in expired:
            del self._store[k]
