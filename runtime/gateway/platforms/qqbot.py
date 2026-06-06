"""QQ Bot API adapter — official QQ Open Platform Bot.

Requires: BotAppID + BotToken from https://q.qq.com
API docs: https://bot.q.qq.com/wiki

Supports:
  - Outbound: send C2C / group / channel messages via HTTP API
  - Inbound: webhook callback handled by runtime/api/endpoints/webhooks.py
"""

from __future__ import annotations

import os
import time

from loguru import logger

from runtime.gateway.base import DeliveryResult, Message, Platform, register

_ACCESS_TOKEN: str | None = None
_ACCESS_TOKEN_EXPIRY: float = 0


def _get_access_token(app_id: str, client_secret: str) -> str | None:
    """Obtain QQ Bot access_token (cached, 2h TTL)."""
    global _ACCESS_TOKEN, _ACCESS_TOKEN_EXPIRY
    import httpx

    if _ACCESS_TOKEN and time.time() < _ACCESS_TOKEN_EXPIRY - 60:
        return _ACCESS_TOKEN

    try:
        r = httpx.post(
            "https://bots.qq.com/app/getAppAccessToken",
            json={"appId": app_id, "clientSecret": client_secret},
            timeout=15,
        )
        data = r.json()
        token = data.get("access_token")
        if token:
            _ACCESS_TOKEN = token
            _ACCESS_TOKEN_EXPIRY = time.time() + data.get("expires_in", 7200)
            return token
    except Exception as e:
        logger.warning("QQ Bot access_token fetch failed: {}", e)
    return None


@register("qqbot")
class QQBotPlatform(Platform):
    """QQ Bot outbound adapter.

    Env vars:
      QQBOT_APP_ID     — Bot AppID from QQ Open Platform
      QQBOT_CLIENT_SECRET — Bot ClientSecret
    """

    def __init__(self) -> None:
        self.app_id: str | None = None
        self.client_secret: str | None = None

    async def configure(
        self,
        *,
        app_id: str | None = None,
        client_secret: str | None = None,
        **_kwargs,
    ) -> None:
        self.app_id = app_id or os.getenv("QQBOT_APP_ID")
        self.client_secret = client_secret or os.getenv("QQBOT_CLIENT_SECRET")

    async def send(self, msg: Message, *, target: str | None = None) -> DeliveryResult:
        try:
            import httpx
        except ImportError:
            return DeliveryResult(ok=False, platform=self.name, msg_id=None, error="httpx missing")
        if not self.app_id or not self.client_secret:
            await self.configure()
        if not self.app_id or not self.client_secret:
            return DeliveryResult(
                ok=False, platform=self.name, msg_id=None,
                error="QQBOT_APP_ID/QQBOT_CLIENT_SECRET not set",
            )

        import asyncio
        token = await asyncio.to_thread(
            _get_access_token, self.app_id, self.client_secret,
        )
        if not token:
            return DeliveryResult(
                ok=False, platform=self.name, msg_id=None,
                error="failed to get QQ Bot access_token",
            )

        if not target:
            return DeliveryResult(
                ok=False, platform=self.name, msg_id=None,
                error="target (openid / group_openid) required",
            )

        url, body = _build_qqbot_request(target, msg.text)
        async with httpx.AsyncClient(timeout=15.0) as c:
            r = await c.post(
                url, json=body,
                headers={"Authorization": f"QQBot {token}"},
            )
            if r.is_success:
                resp = r.json()
                return DeliveryResult(
                    ok=True, platform=self.name,
                    msg_id=str(resp.get("id", "")),
                )
            return DeliveryResult(
                ok=False, platform=self.name, msg_id=None,
                error=f"{r.status_code}: {r.text[:120]}",
            )


def _build_qqbot_request(target: str, text: str) -> tuple[str, dict]:
    """Build QQ Bot API URL + body for the given target.

    Target format:
      - "user:<openid>"      → C2C message
      - "group:<openid>"     → group message
      - "channel:<id>"       → channel message (guild)
      - plain openid         → treated as C2C user
    """
    base = "https://api.sgroup.qq.com"
    content = text[:2000]  # QQ Bot text limit

    if target.startswith("user:"):
        url = f"{base}/v2/users/{target[5:]}/messages"
    elif target.startswith("group:"):
        url = f"{base}/v2/groups/{target[6:]}/messages"
    elif target.startswith("channel:"):
        url = f"{base}/v2/channels/{target[8:]}/messages"
    else:
        url = f"{base}/v2/users/{target}/messages"

    body = {
        "content": content,
        "msg_type": 0,  # text
    }
    return url, body
