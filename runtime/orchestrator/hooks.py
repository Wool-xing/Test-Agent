"""Lifecycle hook registry — before_node / after_node / on_error callbacks.

Plug into flows.py or direct.py to inject custom metrics, notifications, or policies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from loguru import logger

NodeHook = Callable[[str, Dict[str, Any]], None]
"""Hook signature: (node_id, node_ctx) → None.

node_ctx keys: name, kind, inputs, timeout, results (after_node only), error (on_error only).
"""


@dataclass
class HookRegistry:
    before: List[NodeHook] = field(default_factory=list)
    after: List[NodeHook] = field(default_factory=list)
    on_error: List[NodeHook] = field(default_factory=list)

    def register_before(self, fn: NodeHook) -> None:
        self.before.append(fn)

    def register_after(self, fn: NodeHook) -> None:
        self.after.append(fn)

    def register_error(self, fn: NodeHook) -> None:
        self.on_error.append(fn)

    def fire_before(self, node_id: str, ctx: Dict[str, Any]) -> None:
        for fn in self.before:
            try:
                fn(node_id, ctx)
            except Exception:
                logger.debug("hook {}.{} failed for node {}", getattr(fn, '__module__', ''), getattr(fn, '__name__', repr(fn)), node_id)

    def fire_after(self, node_id: str, ctx: Dict[str, Any]) -> None:
        for fn in self.after:
            try:
                fn(node_id, ctx)
            except Exception:
                logger.debug("hook {}.{} failed for node {}", getattr(fn, '__module__', ''), getattr(fn, '__name__', repr(fn)), node_id)

    def fire_error(self, node_id: str, ctx: Dict[str, Any]) -> None:
        for fn in self.on_error:
            try:
                fn(node_id, ctx)
            except Exception:
                logger.debug("hook {}.{} failed for node {}", getattr(fn, '__module__', ''), getattr(fn, '__name__', repr(fn)), node_id)


# Global singleton — callers can replace per-run with a fresh instance.
_global_registry: HookRegistry | None = None


def get_hook_registry() -> HookRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = HookRegistry()
    return _global_registry


def reset_hook_registry() -> None:
    global _global_registry
    _global_registry = HookRegistry()
