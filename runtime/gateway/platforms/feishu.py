"""Feishu/Lark webhook adapter."""

from __future__ import annotations

import os

from runtime.gateway.base import DeliveryResult, Message, Platform, register


@register("feishu")
class FeishuPlatform(Platform):
    def __init__(self) -> None:
        self.webhook: str | None = None

    async def configure(self, *, webhook_url: str | None = None, **_kwargs) -> None:
        self.webhook = webhook_url or os.getenv("FEISHU_WEBHOOK_URL")

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
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error="FEISHU_WEBHOOK_URL not set")
        body = {"msg_type": "text", "content": {"text": msg.text}}
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(url, json=body)
            if r.is_success:
                return DeliveryResult(ok=True, platform=self.name, msg_id=str(r.json().get("data", {}).get("message_id", "")))
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error=f"{r.status_code}")
