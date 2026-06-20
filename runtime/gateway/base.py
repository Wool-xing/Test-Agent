"""Platform abstraction."""

from __future__ import annotations

import abc
import ipaddress
import socket
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


def is_safe_webhook_url(url: str) -> bool:
    """Check that a URL does not point to private/internal network.

    Blocks: loopback, link-local, private (RFC 1918), and 0.0.0.0.
    Returns True if safe, False if the host resolves to a blocked IP.
    """
    try:
        host = urlparse(url).hostname
        if not host:
            return False
        addr = ipaddress.ip_address(host)
    except ValueError:
        # hostname — resolve it
        try:
            addr = ipaddress.ip_address(socket.gethostbyname(host))
        except (OSError, ValueError):
            return False  # can't resolve → block

    if addr.is_loopback or addr.is_link_local or addr.is_unspecified or addr.is_private:
        return False
    # Block cloud metadata endpoints (SSRF to AWS/GCP/Azure metadata)
    if str(addr) == "169.254.169.254":
        return False
    # DNS rebinding defense: re-resolve and compare
    try:
        addr2 = ipaddress.ip_address(socket.gethostbyname(host))
        if addr2 != addr:
            return False  # DNS rebinding detected
    except (OSError, ValueError):
        pass
    return True


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
