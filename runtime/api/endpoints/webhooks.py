"""IM webhook endpoints — Telegram / Discord / 飞书.

Mount these routes on the FastAPI app to enable inbound IM → Agent processing.
Each endpoint validates the incoming payload, extracts the message text, dispatches
to the kernel via bridge.process_im_message(), and replies via the platform adapter.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from loguru import logger

from runtime.gateway.bridge import process_im_message

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ── helpers ──────────────────────────────────────────────────────────


def _verify_discord_signature(body: bytes, signature: str, timestamp: str) -> bool:
    """Verify Discord interaction signature (Ed25519). Returns True if valid."""
    public_key = os.getenv("DISCORD_PUBLIC_KEY", "")
    if not public_key:
        logger.warning("DISCORD_PUBLIC_KEY not set — signature verification skipped")
        return True  # allow in dev; set key in production

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature

        key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key))
        message = timestamp.encode() + body
        key.verify(bytes.fromhex(signature), message)
        return True
    except (ValueError, InvalidSignature) as e:
        logger.warning("Discord signature verification failed: {}", e)
        return False
    except ImportError:
        logger.warning("cryptography not available — Discord signature skipped")
        return True  # allow in dev


def _extract_text_from_payload(platform: str, data: dict) -> str | None:
    """Extract message text from a platform-specific webhook payload."""
    if platform == "telegram":
        msg = data.get("message", {})
        return (msg.get("text") or msg.get("caption") or "").strip() or None

    if platform == "discord":
        # Discord interaction: /command options → text
        cmd_data = data.get("data", {})
        options = cmd_data.get("options", [])
        if options:
            parts = [cmd_data.get("name", "")]
            for opt in options:
                parts.append(f"{opt.get('name', '')}: {opt.get('value', '')}")
            return " ".join(parts).strip()
        return cmd_data.get("name", "").strip() or None

    if platform == "feishu":
        event = data.get("event", {})
        text = event.get("text", "")
        if not text:
            # Try rich text format
            text_content = event.get("content", "{}")
            try:
                content = json.loads(text_content) if isinstance(text_content, str) else text_content
                text = content.get("text", "")
            except (json.JSONDecodeError, TypeError):
                pass
        return text.strip() or None

    return None


def _extract_sender(data: dict) -> str:
    """Extract sender identity from webhook payload."""
    # Telegram
    msg = data.get("message", {})
    sender = msg.get("from", {})
    if sender:
        return sender.get("username") or sender.get("first_name") or str(sender.get("id", "unknown"))

    # Discord
    member = data.get("member", {})
    user = member.get("user", {})
    if user:
        return user.get("username") or str(user.get("id", "unknown"))

    # 飞书
    event = data.get("event", {})
    sender_id = event.get("sender_id") or event.get("open_id")
    if sender_id:
        sender_name = sender_id.get("open_id", "") if isinstance(sender_id, dict) else str(sender_id)
        return sender_name

    return "unknown"


# ── Telegram ─────────────────────────────────────────────────────────


@router.post("/telegram")
async def telegram_webhook(request: Request, bg: BackgroundTasks) -> JSONResponse:
    """Receive Telegram bot updates. Processes text messages through the test kernel."""
    try:
        data: dict = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")

    text = _extract_text_from_payload("telegram", data)
    if not text:
        return JSONResponse({"status": "ignored", "reason": "no text"})

    chat_id = str(data.get("message", {}).get("chat", {}).get("id", ""))

    bg.add_task(_process_async, text, "telegram", chat_id)
    return JSONResponse({"status": "accepted"})


# ── Discord ──────────────────────────────────────────────────────────


@router.post("/discord")
async def discord_webhook(request: Request, bg: BackgroundTasks):
    """Receive Discord interactions. Verifies Ed25519 signature, handles PING/PONG."""
    body = await request.body()
    signature = request.headers.get("X-Signature-Ed25519", "")
    timestamp = request.headers.get("X-Signature-Timestamp", "")

    # Verify signature
    if not _verify_discord_signature(body, signature, timestamp):
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        data: dict = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid JSON")

    # Discord PING/PONG for endpoint verification
    if data.get("type") == 1:
        return JSONResponse({"type": 1})  # PONG

    # Handle application command
    if data.get("type") == 2:
        text = _extract_text_from_payload("discord", data)
        if not text:
            return JSONResponse({
                "type": 4,
                "data": {"content": "Usage: /test <your test request>"},
            })

        token = data.get("token", "")
        app_id = data.get("application_id", "")
        interaction_id = data.get("id", "")

        # Acknowledge immediately, then process
        bg.add_task(_process_discord_followup, text, token, app_id)
        return JSONResponse({
            "type": 5,  # DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE
            "data": {"content": "🔍 Test-Agent is analyzing..."},
        })

    return JSONResponse({"status": "ignored"})


async def _process_discord_followup(text: str, token: str, app_id: str) -> None:
    """Process Discord interaction and send follow-up via webhook."""
    import httpx

    try:
        result = await process_im_message(text, "discord", target=None)

        async with httpx.AsyncClient(timeout=15.0) as client:
            url = f"https://discord.com/api/v10/webhooks/{app_id}/{token}/messages/@original"
            await client.patch(url, json={
                "content": result.reply[:2000],  # Discord message limit
            })
    except Exception as exc:
        logger.warning("Discord follow-up failed: {}", exc)


# ── 飞书 (Feishu / Lark) ─────────────────────────────────────────────


@router.post("/feishu")
async def feishu_webhook(request: Request, bg: BackgroundTasks):
    """Receive 飞书 event callbacks. Handles URL verification and text messages."""
    try:
        data: dict = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")

    # URL verification challenge (飞书 sets up webhook)
    challenge = data.get("challenge")
    if challenge:
        return JSONResponse({"challenge": challenge})

    # Event callback
    event_type = data.get("header", {}).get("event_type", "")
    if event_type == "im.message.receive_v1":
        text = _extract_text_from_payload("feishu", data)
        if text:
            chat_id = data.get("event", {}).get("message", {}).get("chat_id", "")
            bg.add_task(_process_async, text, "feishu", chat_id)

    return JSONResponse({"code": 0})


# ── background processing ────────────────────────────────────────────


async def _process_async(text: str, platform_name: str, target: str | None) -> None:
    """Background task: process IM message and reply."""
    try:
        result = await process_im_message(text, platform_name, target=target)
        if not result.ok:
            logger.warning("IM process failed for {}: {}", platform_name, result.error)
    except Exception as exc:
        logger.exception("IM processing crashed for {}: {}", platform_name, exc)
