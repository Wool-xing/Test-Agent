"""DingTalk webhook adapter."""

from __future__ import annotations

import os

from runtime.gateway.base import DeliveryResult, Message, Platform, register


@register("dingtalk")
class DingTalkPlatform(Platform):
    def __init__(self) -> None:
        self.webhook: str | None = None

    async def configure(self, *, webhook_url: str | None = None, **_kwargs) -> None:
        self.webhook = webhook_url or os.getenv("DINGTALK_WEBHOOK_URL")

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
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error="DINGTALK_WEBHOOK_URL not set")
        body = {"msgtype": "text", "text": {"content": msg.text}}
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(url, json=body)
            if r.is_success and r.json().get("errcode") == 0:
                return DeliveryResult(ok=True, platform=self.name, msg_id=None)
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error=f"{r.status_code}: {r.text[:120]}")
