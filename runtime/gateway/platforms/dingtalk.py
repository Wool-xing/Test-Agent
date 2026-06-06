"""DingTalk (钉钉) adapter.

Two sending modes:
  1. Webhook mode (自定义机器人): set DINGTALK_WEBHOOK_URL → push to group
  2. API mode (应用机器人): set DINGTALK_APP_KEY + DINGTALK_APP_SECRET
     → send to specific user via message/send API (needed for two-way replies)

Inbound messages are handled by runtime/api/endpoints/webhooks.py.
"""

from __future__ import annotations

import os
import time

from loguru import logger

from runtime.gateway.base import DeliveryResult, Message, Platform, is_safe_webhook_url, register

_ACCESS_TOKEN: str | None = None
_ACCESS_TOKEN_EXPIRY: float = 0


def _get_access_token(app_key: str, app_secret: str) -> str | None:
    """Obtain DingTalk access_token (cached, 2h TTL)."""
    global _ACCESS_TOKEN, _ACCESS_TOKEN_EXPIRY
    import httpx

    if _ACCESS_TOKEN and time.time() < _ACCESS_TOKEN_EXPIRY - 120:
        return _ACCESS_TOKEN

    try:
        r = httpx.get(
            "https://oapi.dingtalk.com/gettoken",
            params={"appkey": app_key, "appsecret": app_secret},
            timeout=10,
        )
        data = r.json()
        token = data.get("access_token")
        if token:
            _ACCESS_TOKEN = token
            _ACCESS_TOKEN_EXPIRY = time.time() + data.get("expires_in", 7200)
            return token
    except Exception as e:
        logger.warning("DingTalk access_token fetch failed: {}", e)
    return None


@register("dingtalk")
class DingTalkPlatform(Platform):
    """DingTalk outbound adapter.

    Env vars:
      DINGTALK_WEBHOOK_URL  — group bot webhook (one-way push)
      DINGTALK_APP_KEY      — app key (for API mode)
      DINGTALK_APP_SECRET   — app secret (for API mode)
    """

    def __init__(self) -> None:
        self.webhook: str | None = None
        self.app_key: str | None = None
        self.app_secret: str | None = None
        self.agent_id: str | None = None

    async def configure(
        self,
        *,
        webhook_url: str | None = None,
        app_key: str | None = None,
        app_secret: str | None = None,
        agent_id: str | None = None,
        **_kwargs,
    ) -> None:
        self.webhook = webhook_url or os.getenv("DINGTALK_WEBHOOK_URL")
        self.app_key = app_key or os.getenv("DINGTALK_APP_KEY")
        self.app_secret = app_secret or os.getenv("DINGTALK_APP_SECRET")
        self.agent_id = agent_id or os.getenv("DINGTALK_AGENT_ID")

    async def send(self, msg: Message, *, target: str | None = None) -> DeliveryResult:
        """Send message. Uses API mode when target is a userid, webhook otherwise."""
        # If target is a DingTalk userid (not a URL), use API mode for direct reply
        if target and not target.startswith("https://"):
            return await self._send_via_api(msg, target)
        return await self._send_via_webhook(msg, target)

    async def _send_via_api(self, msg: Message, userid: str) -> DeliveryResult:
        """Send via DingTalk message/send API (应用机器人模式)."""
        try:
            import httpx
        except ImportError:
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error="httpx missing")
        if not self.app_key or not self.app_secret:
            await self.configure()
        if not self.app_key or not self.app_secret:
            return DeliveryResult(
                ok=False, platform=self.name, msg_id=None,
                error="DINGTALK_APP_KEY/DINGTALK_APP_SECRET not set",
            )

        import asyncio
        token = await asyncio.to_thread(_get_access_token, self.app_key, self.app_secret)
        if not token:
            return DeliveryResult(
                ok=False, platform=self.name, msg_id=None,
                error="failed to get DingTalk access_token",
            )

        body = {
            "touser": userid,
            "agent_id": self.agent_id or "",
            "msg": {"msgtype": "text", "text": {"content": msg.text}},
        }
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(
                f"https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2"
                f"?access_token={token}",
                json=body,
            )
            resp = r.json()
            if resp.get("errcode") == 0:
                return DeliveryResult(
                    ok=True, platform=self.name,
                    msg_id=str(resp.get("task_id", "")),
                )
            return DeliveryResult(
                ok=False, platform=self.name, msg_id=None,
                error=f"errcode={resp.get('errcode')}: {resp.get('errmsg', '')}",
            )

    async def _send_via_webhook(self, msg: Message, target: str | None) -> DeliveryResult:
        """Send via webhook URL (自定义机器人模式, existing behavior)."""
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
            return DeliveryResult(
                ok=False, platform=self.name, msg_id=None,
                error="DINGTALK_WEBHOOK_URL not set",
            )
        body = {"msgtype": "text", "text": {"content": msg.text}}
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(url, json=body)
            if r.is_success and r.json().get("errcode") == 0:
                return DeliveryResult(ok=True, platform=self.name, msg_id=None)
            return DeliveryResult(
                ok=False, platform=self.name, msg_id=None,
                error=f"{r.status_code}: {r.text[:120]}",
            )
