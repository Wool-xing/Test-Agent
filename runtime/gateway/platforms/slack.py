"""Slack incoming webhook adapter."""

from __future__ import annotations

import os

from runtime.gateway.base import DeliveryResult, Message, Platform, is_safe_webhook_url, register


@register("slack")
class SlackPlatform(Platform):
    def __init__(self) -> None:
        self.webhook: str | None = None

    async def configure(self, *, webhook_url: str | None = None, **_kwargs) -> None:
        self.webhook = webhook_url or os.getenv("SLACK_WEBHOOK_URL")

    async def send(self, msg: Message, *, target: str | None = None) -> DeliveryResult:
        try:
            import httpx
        except ImportError:
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error="httpx missing")
        url = target if target and target.startswith("https://") and is_safe_webhook_url(target) else None
        if not url:
            if not self.webhook:
                await self.configure()
            url = self.webhook
        if not url:
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error="SLACK_WEBHOOK_URL not set")
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(url, json={"text": msg.text})
            return DeliveryResult(ok=r.is_success, platform=self.name, msg_id=None, error=None if r.is_success else f"{r.status_code}")
