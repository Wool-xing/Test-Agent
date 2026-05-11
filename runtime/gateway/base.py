"""Platform abstraction · hermes §1.5."""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Message:
    text: str
    user: str | None = None
    room: str | None = None
    extra: dict[str, Any] | None = None


@dataclass(slots=True)
class DeliveryResult:
    ok: bool
    platform: str
    msg_id: str | None
    error: str | None = None


class Platform(abc.ABC):
    name: str = "abstract"

    @abc.abstractmethod
    async def send(self, msg: Message, *, target: str | None = None) -> DeliveryResult: ...

    @abc.abstractmethod
    async def configure(self, **kwargs) -> None: ...


REGISTRY: dict[str, type[Platform]] = {}


def register(name: str):
    def deco(cls: type[Platform]):
        cls.name = name
        REGISTRY[name] = cls
        return cls

    return deco


def get_platform(name: str) -> Platform:
    cls = REGISTRY.get(name)
    if cls is None:
        raise KeyError(f"unknown platform: {name}; available={sorted(REGISTRY)}")
    return cls()
