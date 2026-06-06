"""Generic webhook POST adapter (catch-all)."""

from __future__ import annotations

import os

from runtime.gateway.base import DeliveryResult, Message, Platform, is_safe_webhook_url, register


@register("webhook")
class WebhookPlatform(Platform):
    def __init__(self) -> None:
        self.url: str | None = None
        self.headers: dict[str, str] = {}

    async def configure(self, *, url: str | None = None, headers: dict | None = None, **_kwargs) -> None:
        self.url = url or os.getenv("GENERIC_WEBHOOK_URL")
        self.headers = headers or {}

    async def send(self, msg: Message, *, target: str | None = None) -> DeliveryResult:
        try:
            import httpx
        except ImportError:
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error="httpx missing")
        url = target if target and target.startswith("https://") and is_safe_webhook_url(target) else None
        if not url:
            if not self.url:
                await self.configure()
            url = self.url
        if not url:
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error="no url")
        body = {"text": msg.text, "user": msg.user, "room": msg.room, "extra": msg.extra}
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(url, json=body, headers=self.headers)
            return DeliveryResult(ok=r.is_success, platform=self.name, msg_id=None, error=None if r.is_success else f"{r.status_code}")
