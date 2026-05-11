"""Discord webhook adapter."""

from __future__ import annotations

import os

from runtime.gateway.base import DeliveryResult, Message, Platform, register


@register("discord")
class DiscordPlatform(Platform):
    def __init__(self) -> None:
        self.webhook: str | None = None

    async def configure(self, *, webhook_url: str | None = None, **_kwargs) -> None:
        self.webhook = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")

    async def send(self, msg: Message, *, target: str | None = None) -> DeliveryResult:
        try:
            import httpx
        except ImportError:
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error="httpx missing")
        url = target or self.webhook
        if not url:
            await self.configure()
            url = self.webhook
        if not url:
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error="DISCORD_WEBHOOK_URL not set")
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(url, json={"content": msg.text[:2000]})
            return DeliveryResult(ok=r.is_success, platform=self.name, msg_id=None, error=None if r.is_success else f"{r.status_code}")
