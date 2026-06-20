"""Dependency Injection & Testability (§补-25).

Lightweight DI: no heavy framework. Three patterns:
  Pattern 1: Function parameter injection (recommended)
  Pattern 2: ExecutionContext object (cross-layer)
  Pattern 3: Registry (plugin/provider discovery)

Every injectable interface gets a Fake implementation for testing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


# ── Injectable interfaces ───────────────────────────────

class LLMProvider(Protocol):
    """Abstract LLM provider — injectable for testing."""
    def complete(self, system: str, user: str) -> str: ...
    def complete_json(self, system: str, user: str) -> dict: ...


class StorageAdapter(Protocol):
    """Abstract storage — injectable for testing."""
    def execute(self, query: str, params: dict | None = None) -> Any: ...
    def fetch(self, query: str, params: dict | None = None) -> list[dict]: ...


class FileSystem(Protocol):
    """Abstract filesystem — injectable for testing."""
    def read_text(self, path: str) -> str: ...
    def write_text(self, path: str, content: str) -> None: ...
    def exists(self, path: str) -> bool: ...


class Clock(Protocol):
    """Abstract clock — injectable for testing time-dependent code."""
    def now(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...


# ── ExecutionContext (Pattern 2) ─────────────────────────

@dataclass
class ExecutionContext:
    """Cross-layer context with injectable dependencies."""
    trace_id: str = ""
    llm: LLMProvider | None = None
    storage: StorageAdapter | None = None
    fs: FileSystem | None = None
    clock: Clock | None = None
    config: dict[str, Any] = field(default_factory=dict)


# ── Fake Implementations (for testing) ───────────────────

class FakeLLM(LLMProvider):
    """Fake LLM that returns deterministic responses. Zero cost, zero latency."""

    def __init__(self, responses: dict[str, str] | None = None):
        self.responses = responses or {}
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        key = user[:50]
        return self.responses.get(key, '{"status": "ok"}')

    def complete_json(self, system: str, user: str) -> dict:
        import json
        return json.loads(self.complete(system, user))


class InMemoryStorage(StorageAdapter):
    """In-memory storage for testing — dict backend, zero dependencies."""

    def __init__(self):
        self._data: dict[str, list[dict]] = {}
        self.queries: list[str] = []

    def execute(self, query: str, params: dict | None = None) -> Any:
        self.queries.append(query)
        return None

    def fetch(self, query: str, params: dict | None = None) -> list[dict]:
        self.queries.append(query)
        table = query.split("FROM")[-1].strip().split()[0] if "FROM" in query else "default"
        return self._data.get(table, [])

    def insert(self, table: str, row: dict) -> None:
        self._data.setdefault(table, []).append(row)


class InMemoryFS(FileSystem):
    """In-memory filesystem for testing — no disk I/O."""

    def __init__(self, files: dict[str, str] | None = None):
        self._files: dict[str, str] = files or {}
        self.writes: list[tuple[str, str]] = []

    def read_text(self, path: str) -> str:
        return self._files.get(path, "")

    def write_text(self, path: str, content: str) -> None:
        self.writes.append((path, content))
        self._files[path] = content

    def exists(self, path: str) -> bool:
        return path in self._files


class FakeClock(Clock):
    """Fake clock for testing time-dependent code."""

    def __init__(self, start_time: float = 0.0):
        self._now = start_time
        self.sleeps: list[float] = []

    def now(self) -> float:
        return self._now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)

    def advance(self, seconds: float) -> None:
        self._now += seconds


# ── Real Implementations ─────────────────────────────────

class RealLLM(LLMProvider):
    """Real LLM via LiteLLM — production use."""

    def complete(self, system: str, user: str) -> str:
        from runtime.router.llm_client import LLMClient
        client = LLMClient()
        return client.complete(system, user)

    def complete_json(self, system: str, user: str) -> dict:
        from runtime.router.llm_client import LLMClient
        client = LLMClient()
        return client.complete_json(system, user)


class RealFS(FileSystem):
    """Real filesystem — production use."""

    def read_text(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    def write_text(self, path: str, content: str) -> None:
        Path(path).write_text(content, encoding="utf-8")

    def exists(self, path: str) -> bool:
        return Path(path).exists()


class RealClock(Clock):
    """Real clock — production use."""

    def now(self) -> float:
        import time
        return time.time()

    def sleep(self, seconds: float) -> None:
        import time
        time.sleep(seconds)
