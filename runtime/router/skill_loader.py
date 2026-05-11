"""Convenience facade; the actual scan lives in registry.registry."""

from __future__ import annotations

from runtime.registry.registry import build_catalog


def list_skills() -> list[dict]:
    return [s.short() for s in build_catalog().skills.values()]
