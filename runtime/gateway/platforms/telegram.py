"""Telegram Bot API adapter."""

from __future__ import annotations

import os

from runtime.gateway.base import DeliveryResult, Message, Platform, register


@register("telegram")
class TelegramPlatform(Platform):
    def __init__(self) -> None:
        self.token: str | None = None
        self.default_chat: str | None = None

    async def configure(self, *, token: str | None = None, chat_id: str | None = None, **_kwargs) -> None:
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.default_chat = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    async def send(self, msg: Message, *, target: str | None = None) -> DeliveryResult:
        try:
            import httpx
        except ImportError:
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error="httpx missing")
        if not self.token:
            await self.configure()
        if not self.token:
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error="TELEGRAM_BOT_TOKEN not set")
        chat = target or msg.room or self.default_chat
        if not chat:
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error="no chat_id")
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage",
                json={"chat_id": chat, "text": msg.text, "parse_mode": "Markdown"},
            )
            if r.is_success:
                return DeliveryResult(ok=True, platform=self.name, msg_id=str(r.json().get("result", {}).get("message_id")))
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error=f"{r.status_code} {r.text[:200]}")
