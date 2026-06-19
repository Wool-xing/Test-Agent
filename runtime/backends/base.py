"""BaseExecutionEnv abstract base.

All 7 backends implement this contract; new backend = new file + @register.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ExecResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int | None
    elapsed_ms: int


class BaseExecutionEnv(abc.ABC):
    name: str = "abstract"

    @abc.abstractmethod
    async def connect(self) -> None: ...

    @abc.abstractmethod
    async def exec(self, cmd: str, *, timeout: float = 60.0, cwd: str | None = None, env: dict | None = None) -> ExecResult: ...

    @abc.abstractmethod
    async def read(self, path: str) -> bytes: ...

    @abc.abstractmethod
    async def write(self, path: str, data: bytes) -> None: ...

    @abc.abstractmethod
    async def sync_in(self, local: Path, remote: str) -> None: ...

    @abc.abstractmethod
    async def sync_out(self, remote: str, local: Path) -> None: ...

    @abc.abstractmethod
    async def close(self) -> None: ...


REGISTRY: dict[str, type[BaseExecutionEnv]] = {}


def register(name: str):
    def deco(cls: type[BaseExecutionEnv]):
        cls.name = name
        REGISTRY[name] = cls
        return cls

    return deco


def get_backend(name: str, **kwargs) -> BaseExecutionEnv:
    cls = REGISTRY.get(name)
    if cls is None:
        raise KeyError(f"unknown backend: {name}; available={sorted(REGISTRY)}")
    return cls(**kwargs)
