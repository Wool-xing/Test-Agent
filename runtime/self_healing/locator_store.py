"""Multi‑attribute element locator storage with fallback chains."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LocatorEntry:
    name: str
    primary: str
    fallbacks: list[str] = field(default_factory=list)


class LocatorStore:
    """In‑memory locator registry with optional JSON persistence."""

    def __init__(self) -> None:
        self._store: dict[str, LocatorEntry] = {}

    def add(self, name: str, primary: str, fallbacks: list[str] | None = None) -> None:
        self._store[name] = LocatorEntry(name=name, primary=primary, fallbacks=fallbacks or [])

    def resolve(self, name: str) -> list[str]:
        """Return ordered locator chain: primary + fallbacks."""
        entry = self._store.get(name)
        if entry is None:
            raise KeyError(f"locator '{name}' not found")
        return [entry.primary, *entry.fallbacks]

    def remove(self, name: str) -> None:
        self._store.pop(name, None)

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, name: str) -> bool:
        return name in self._store
