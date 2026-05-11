"""Email (SMTP) adapter."""

from __future__ import annotations

import asyncio
import os
import smtplib
from email.message import EmailMessage

from runtime.gateway.base import DeliveryResult, Message, Platform, register


@register("email")
class EmailPlatform(Platform):
    def __init__(self) -> None:
        self.host = None
        self.port = 587
        self.user = None
        self.password = None
        self.from_addr = None

    async def configure(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        from_addr: str | None = None,
        **_kwargs,
    ) -> None:
        self.host = host or os.getenv("SMTP_HOST")
        self.port = port or int(os.getenv("SMTP_PORT", "587"))
        self.user = user or os.getenv("SMTP_USER")
        self.password = password or os.getenv("SMTP_PASSWORD")
        self.from_addr = from_addr or os.getenv("SMTP_FROM") or self.user

    async def send(self, msg: Message, *, target: str | None = None) -> DeliveryResult:
        await self.configure()
        if not self.host or not target:
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error="SMTP_HOST or target missing")
        m = EmailMessage()
        m["From"] = self.from_addr or self.user
        m["To"] = target
        m["Subject"] = (msg.extra or {}).get("subject", "Test-Agent notification")
        m.set_content(msg.text)
        try:
            await asyncio.to_thread(self._send_sync, m)
            return DeliveryResult(ok=True, platform=self.name, msg_id=None)
        except Exception as e:
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error=str(e))

    def _send_sync(self, message: EmailMessage) -> None:
        with smtplib.SMTP(self.host, self.port) as s:
            s.starttls()
            if self.user and self.password:
                s.login(self.user, self.password)
            s.send_message(message)
