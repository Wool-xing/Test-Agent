"""Per-run execution context. Thread-safe, no globals.

Replaces the module-level ``_upstream_outputs`` / ``_upstream_meta`` dicts in
``runtime.orchestrator.adapters.experts`` with a dataclass that each run owns.
Parallel DAG branches can read/write safely through the lock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Any

# Module-level lock shared by all contexts. A per-instance Lock field breaks
# Prefect's task-arg hashing (cannot hash _thread.lock) on every DAG submit.
_LOCK = Lock()


@dataclass
class ExecutionContext:
    """Per-run execution context. Thread-safe, no globals.

    Each call to ``run_decision_direct`` or ``run_decision_flow`` creates its
    own instance so parallel runs never share mutable state.
    """

    run_id: str
    upstream_outputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    upstream_meta: dict[str, dict[str, Any]] = field(default_factory=dict)

    def set_output(self, node_id: str, output: dict, meta: dict | None = None) -> None:
        """Store a node's output and optional metadata (thread-safe)."""
        with _LOCK:
            self.upstream_outputs[node_id] = output
            if meta is not None:
                self.upstream_meta[node_id] = meta

    def get_output(self, node_id: str) -> dict | None:
        """Read a node's output (thread-safe)."""
        with _LOCK:
            return self.upstream_outputs.get(node_id)

    def get_meta(self, node_id: str) -> dict | None:
        """Read a node's metadata (thread-safe)."""
        with _LOCK:
            return self.upstream_meta.get(node_id)

    def is_degraded(self, node_id: str) -> bool:
        """Check whether a specific upstream node ran in degraded mode."""
        meta = self.get_meta(node_id)
        return meta.get("degraded", False) if meta else False

    def has_any_degraded(self) -> bool:
        """True if any upstream node ran in degraded mode."""
        with _LOCK:
            return any(m.get("degraded", False) for m in self.upstream_meta.values())

    def snapshot(self) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        """Return a consistent (outputs, meta) snapshot for RunnerContext."""
        with _LOCK:
            return dict(self.upstream_outputs), dict(self.upstream_meta)
