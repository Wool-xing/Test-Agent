"""Convenience facade; the actual scan lives in registry.registry."""

from __future__ import annotations

from runtime.registry.registry import build_catalog


def list_experts() -> list[dict]:
    return [e.short() for e in build_catalog().experts.values()]
