"""WeChat Work (企业微信) adapter.

Two sending modes:
  1. Webhook mode (群机器人): set WECHAT_WEBHOOK_URL → push to group
  2. API mode (自建应用):   set WECHAT_CORP_ID + WECHAT_APP_SECRET + WECHAT_AGENT_ID
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


def _get_access_token(corp_id: str, secret: str) -> str | None:
    """Obtain WeChat Work access_token (cached, 2h TTL)."""
    global _ACCESS_TOKEN, _ACCESS_TOKEN_EXPIRY
    import httpx

    if _ACCESS_TOKEN and time.time() < _ACCESS_TOKEN_EXPIRY - 120:
        return _ACCESS_TOKEN

    try:
        r = httpx.get(
            "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
            params={"corpid": corp_id, "corpsecret": secret},
            timeout=10,
        )
        data = r.json()
        token = data.get("access_token")
        if token:
            _ACCESS_TOKEN = token
            _ACCESS_TOKEN_EXPIRY = time.time() + data.get("expires_in", 7200)
            return token
    except Exception as e:
        logger.warning("WeChat access_token fetch failed: {}", e)
    return None


@register("wechat")
class WeChatPlatform(Platform):
    """WeChat Work outbound adapter.

    Env vars:
      WECHAT_WEBHOOK_URL   — group bot webhook (one-way push)
      WECHAT_CORP_ID       — enterprise corp id (for API mode)
      WECHAT_APP_SECRET    — app secret (for API mode, also WECHAT_SECRET)
      WECHAT_AGENT_ID      — app agent id (for API mode)
    """

    def __init__(self) -> None:
        self.webhook: str | None = None
        self.corp_id: str | None = None
        self.secret: str | None = None
        self.agent_id: str | None = None

    async def configure(
        self,
        *,
        webhook_url: str | None = None,
        corp_id: str | None = None,
        secret: str | None = None,
        agent_id: str | None = None,
        **_kwargs,
    ) -> None:
        self.webhook = webhook_url or os.getenv("WECHAT_WEBHOOK_URL")
        self.corp_id = corp_id or os.getenv("WECHAT_CORP_ID")
        self.secret = secret or os.getenv("WECHAT_APP_SECRET") or os.getenv("WECHAT_SECRET")
        self.agent_id = agent_id or os.getenv("WECHAT_AGENT_ID")

    async def send(self, msg: Message, *, target: str | None = None) -> DeliveryResult:
        """Send message. Uses API mode when target is a userid, webhook otherwise."""
        # If target is a WeChat userid (not a URL), use API mode for direct reply
        if target and not target.startswith("https://"):
            return await self._send_via_api(msg, target)
        return await self._send_via_webhook(msg, target)

    async def _send_via_api(self, msg: Message, userid: str) -> DeliveryResult:
        """Send via WeChat Work message/send API (自建应用模式)."""
        try:
            import httpx
        except ImportError:
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error="httpx missing")
        if not self.corp_id or not self.secret:
            await self.configure()
        if not self.corp_id or not self.secret:
            return DeliveryResult(
                ok=False, platform=self.name, msg_id=None,
                error="WECHAT_CORP_ID/WECHAT_APP_SECRET not set",
            )
        if not self.agent_id:
            self.agent_id = os.getenv("WECHAT_AGENT_ID")
        if not self.agent_id:
            return DeliveryResult(
                ok=False, platform=self.name, msg_id=None,
                error="WECHAT_AGENT_ID not set",
            )

        import asyncio
        token = await asyncio.to_thread(_get_access_token, self.corp_id, self.secret)
        if not token:
            return DeliveryResult(
                ok=False, platform=self.name, msg_id=None,
                error="failed to get WeChat access_token",
            )

        body = {
            "touser": userid,
            "msgtype": "text",
            "agentid": int(self.agent_id),
            "text": {"content": msg.text},
        }
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(
                f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}",
                json=body,
            )
            resp = r.json()
            if resp.get("errcode") == 0:
                return DeliveryResult(ok=True, platform=self.name, msg_id=None)
            return DeliveryResult(
                ok=False, platform=self.name, msg_id=None,
                error=f"errcode={resp.get('errcode')}: {resp.get('errmsg', '')}",
            )

    async def _send_via_webhook(self, msg: Message, target: str | None) -> DeliveryResult:
        """Send via webhook URL (群机器人模式, existing behavior)."""
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
                error="WECHAT_WEBHOOK_URL not set",
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
