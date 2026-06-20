"""Deprecation Policy (§补-24) — controlled feature lifecycle.

3 levels:
  L1 Soft Deprecated — available but warns, retained 2 major versions
  L2 Hard Deprecated — requires explicit config flag, retained 1 version
  L3 Removed — code deleted, config warns on detection

DEPRECATIONS.md tracks all current deprecations.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class DeprecationLevel(Enum):
    SOFT = "soft"     # Warn but still work
    HARD = "hard"     # Require explicit opt-in
    REMOVED = "removed"  # Config key detected, notify user


@dataclass
class DeprecationEntry:
    name: str                     # Feature/command/config key name
    level: DeprecationLevel
    message: str                  # User-facing message
    removed_in_version: str       # e.g. "V2.3.0"
    replacement: str = ""         # e.g. "tagent new-command"
    deprecated_since: str = ""    # e.g. "V2.0.0"


class DeprecationRegistry:
    """Track all deprecated features."""

    def __init__(self):
        self._entries: dict[str, DeprecationEntry] = {}
        self._on_deprecated: list[Callable] = []
        self._on_hard_blocked: list[Callable] = []

    def register(self, entry: DeprecationEntry) -> None:
        self._entries[entry.name] = entry

    def check(self, name: str) -> DeprecationEntry | None:
        """Check if a feature is deprecated. Returns entry or None."""
        return self._entries.get(name)

    def is_hard_blocked(self, name: str) -> bool:
        """Check if a hard-deprecated feature is blocked (no opt-in flag)."""
        entry = self._entries.get(name)
        if entry and entry.level == DeprecationLevel.HARD:
            import os
            flag = os.environ.get(f"TAGENT_DEPRECATED_ALLOW_{name.upper().replace('-', '_')}", "")
            return flag.lower() != "true"
        return False

    def warn_if_deprecated(self, name: str) -> None:
        """Issue warning if feature is deprecated."""
        entry = self.check(name)
        if not entry:
            return
        if entry.level == DeprecationLevel.REMOVED:
            print(f"[REMOVED] '{name}' was removed in {entry.removed_in_version}. {entry.replacement}")
            return
        msg = f"[DEPRECATED] '{name}' is {entry.level.value}-deprecated since {entry.deprecated_since}. Will be removed in {entry.removed_in_version}."
        if entry.replacement:
            msg += f" Use '{entry.replacement}' instead."
        warnings.warn(msg, DeprecationWarning, stacklevel=2)
        for cb in self._on_deprecated:
            cb(entry)

    def list_all(self) -> list[DeprecationEntry]:
        return list(self._entries.values())

    def list_active(self) -> list[DeprecationEntry]:
        return [e for e in self._entries.values() if e.level != DeprecationLevel.REMOVED]


# Singleton
_registry: DeprecationRegistry | None = None


def get_deprecation_registry() -> DeprecationRegistry:
    global _registry
    if _registry is None:
        _registry = DeprecationRegistry()
    return _registry
