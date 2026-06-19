"""ProtocolAdapter abstract base.

All concrete adapters must implement this contract to register.
Honors:
  - 协议调用即测,不裸跑
  - 失败必带 seed+snapshot(可复现性横切准则)
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ProtocolResult:
    ok: bool
    payload: bytes | str | dict | None
    elapsed_ms: int
    error: str | None = None
    meta: dict[str, Any] | None = None


class ProtocolAdapter(abc.ABC):
    """Unified protocol contract."""

    name: str = "abstract"

    @abc.abstractmethod
    async def connect(self, target: str, **kwargs) -> None: ...

    @abc.abstractmethod
    async def send(self, payload: bytes | str | dict, **kwargs) -> ProtocolResult: ...

    @abc.abstractmethod
    async def recv(self, timeout: float = 30.0, **kwargs) -> ProtocolResult: ...

    @abc.abstractmethod
    async def close(self) -> None: ...

    async def ping(self, target: str, payload: bytes | str | dict = b"ping", timeout: float = 10.0) -> ProtocolResult:
        """High-level helper: connect -> send -> recv -> close."""
        await self.connect(target)
        try:
            send_res = await self.send(payload)
            if not send_res.ok:
                return send_res
            return await self.recv(timeout=timeout)
        finally:
            await self.close()


REGISTRY: dict[str, type[ProtocolAdapter]] = {}


def register(name: str):
    def deco(cls: type[ProtocolAdapter]):
        cls.name = name
        REGISTRY[name] = cls
        return cls

    return deco


def get_adapter(name: str) -> ProtocolAdapter:
    cls = REGISTRY.get(name)
    if cls is None:
        raise KeyError(f"unknown protocol adapter: {name}; available={list(REGISTRY)}")
    return cls()
