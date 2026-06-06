"""IM webhook endpoints — Telegram / Discord / 飞书 / 企微 / 钉钉 / QQ Bot.

Mount these routes on the FastAPI app to enable inbound IM → Agent processing.
Each endpoint validates the incoming payload, extracts the message text, dispatches
to the kernel via bridge.process_im_message(), and replies via the platform adapter.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import struct
import time
import xml.etree.ElementTree as ET
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
            text_content = event.get("content", "{}")
            try:
                content = json.loads(text_content) if isinstance(text_content, str) else text_content
                text = content.get("text", "")
            except (json.JSONDecodeError, TypeError):
                pass
        return text.strip() or None

    if platform == "dingtalk":
        # DingTalk outbound robot callback: text in msg["text"]["content"]
        msg = data.get("msg", {})
        return (msg.get("text", {}).get("content") or "").strip() or None

    if platform == "qqbot":
        # QQ Bot webhook: op=0 dispatch payload
        d = data.get("d", {}) if isinstance(data, dict) else {}
        # C2C message: content directly in d
        text = d.get("content", "")
        if not text:
            # Group/Channel message: try attachments
            for att in d.get("attachments", []):
                text += att.get("content", "")
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


# ── WeChat Work crypto helpers ────────────────────────────────────────


def _wechat_verify_signature(token: str, timestamp: str, nonce: str,
                              encrypt: str, signature: str) -> bool:
    """Verify WeChat Work callback signature: SHA1(sort(token, ts, nonce, encrypt))."""
    params = sorted([token, str(timestamp), str(nonce), encrypt])
    sign = hashlib.sha1("".join(params).encode()).hexdigest()
    return sign == signature


def _wechat_decrypt(encrypted: str, encoding_aes_key: str) -> str:
    """Decrypt WeChat Work AES-256-CBC encrypted message.

    Returns the plaintext XML string extracted from the decrypted buffer.
    Buffer layout: random(16) + msg_len(4 big-endian) + msg + corpid.
    """
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    aes_key = base64.b64decode(encoding_aes_key + "=")
    cipher = Cipher(algorithms.AES(aes_key), modes.CBC(aes_key[:16]))
    decryptor = cipher.decryptor()
    plain = decryptor.update(base64.b64decode(encrypted)) + decryptor.finalize()
    # Strip PKCS#7 padding
    pad = plain[-1]
    plain = plain[:-pad]
    # Extract message: skip random(16) + msg_len(4)
    msg_len = struct.unpack(">I", plain[16:20])[0]
    return plain[20:20 + msg_len].decode("utf-8")


def _parse_wechat_xml(xml_str: str) -> dict[str, str]:
    """Parse decrypted WeChat Work XML message into a dict."""
    root = ET.fromstring(xml_str)
    def _text(tag: str) -> str:
        el = root.find(tag)
        return (el.text or "") if el is not None else ""
    return {
        "from_user": _text("FromUserName"),
        "to_user": _text("ToUserName"),
        "msg_type": _text("MsgType"),
        "content": _text("Content"),
        "agent_id": _text("AgentID"),
    }


# ── DingTalk signature helper ─────────────────────────────────────────


def _verify_dingtalk_signature(timestamp: str, sign: str) -> bool:
    """Verify DingTalk callback signature (HMAC-SHA256)."""
    app_secret = os.getenv("DINGTALK_APP_SECRET", "")
    if not app_secret:
        logger.warning("DINGTALK_APP_SECRET not set — signature skipped")
        return True
    message = timestamp + "\n" + app_secret
    expected = base64.b64encode(
        hmac.new(app_secret.encode(), message.encode(), hashlib.sha256).digest()
    ).decode()
    return hmac.compare_digest(sign, expected)


# ── QQ Bot signature helper ───────────────────────────────────────────


def _verify_qqbot_signature(body: bytes, signature: str, timestamp: str) -> bool:
    """Verify QQ Bot Ed25519 signature. Same algorithm as Discord."""
    public_key = os.getenv("QQBOT_PUBLIC_KEY", "")
    if not public_key:
        logger.warning("QQBOT_PUBLIC_KEY not set — signature skipped")
        return True  # allow in dev

    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature

        key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key))
        message = timestamp.encode() + body
        key.verify(bytes.fromhex(signature), message)
        return True
    except (ValueError, InvalidSignature) as e:
        logger.warning("QQ Bot signature verification failed: {}", e)
        return False
    except ImportError:
        logger.warning("cryptography not available — QQ Bot signature skipped")
        return True


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


# ── 企业微信 (WeChat Work / WeCom) ───────────────────────────────────


@router.api_route("/wechat", methods=["GET", "POST"])
async def wechat_webhook(request: Request, bg: BackgroundTasks):
    """Receive 企业微信 app callbacks.

    GET  — URL verification (echostr challenge + signature check)
    POST — message event callback (AES-encrypted XML body)
    """
    params = request.query_params
    msg_signature = params.get("msg_signature", "")
    timestamp = params.get("timestamp", "")
    nonce = params.get("nonce", "")

    token = os.getenv("WECHAT_TOKEN", "")
    aes_key = os.getenv("WECHAT_ENCODING_AES_KEY", "")

    if request.method == "GET":
        # URL verification: decrypt echostr and return
        echostr = params.get("echostr", "")
        if not all([token, aes_key, msg_signature, echostr]):
            raise HTTPException(status_code=400, detail="missing params")
        if not _wechat_verify_signature(token, timestamp, nonce, echostr, msg_signature):
            raise HTTPException(status_code=403, detail="signature mismatch")
        try:
            plain = _wechat_decrypt(echostr, aes_key)
        except Exception as e:
            logger.warning("WeChat echostr decrypt failed: {}", e)
            raise HTTPException(status_code=400, detail="decrypt failed")
        return PlainTextResponse(content=plain)

    # POST: message callback
    try:
        body_xml = (await request.body()).decode("utf-8")
    except Exception:
        raise HTTPException(status_code=400, detail="invalid body")

    if not all([token, aes_key]):
        raise HTTPException(status_code=400, detail="WECHAT_TOKEN/WECHAT_ENCODING_AES_KEY not set")

    # Extract encrypted content from XML
    try:
        root = ET.fromstring(body_xml)
        encrypt_el = root.find("Encrypt")
        encrypted = (encrypt_el.text or "") if encrypt_el is not None else ""
    except ET.ParseError as e:
        logger.warning("WeChat XML parse failed: {}", e)
        raise HTTPException(status_code=400, detail="invalid XML")

    if not encrypted:
        raise HTTPException(status_code=400, detail="missing Encrypt")

    # Verify signature
    if not _wechat_verify_signature(token, timestamp, nonce, encrypted, msg_signature):
        raise HTTPException(status_code=403, detail="signature mismatch")

    # Decrypt
    try:
        plain_xml = _wechat_decrypt(encrypted, aes_key)
    except Exception as e:
        logger.warning("WeChat message decrypt failed: {}", e)
        raise HTTPException(status_code=400, detail="decrypt failed")

    parsed = _parse_wechat_xml(plain_xml)

    # Only handle text messages
    if parsed.get("msg_type") != "text" or not parsed.get("content"):
        return PlainTextResponse(content="success")  # ACK for non-text

    bg.add_task(
        _process_async_wechat,
        parsed["content"], "wechat",
        parsed["from_user"], parsed["agent_id"],
    )
    return PlainTextResponse(content="success")


async def _process_async_wechat(text: str, platform: str, userid: str,
                                  agent_id: str) -> None:
    """Background task for WeChat: route → reply via API."""
    try:
        result = await process_im_message(text, platform, target=userid)
        if not result.ok:
            logger.warning("WeChat IM process failed: {}", result.error)
    except Exception as exc:
        logger.exception("WeChat IM processing crashed: {}", exc)

        # Send error reply back to user
        from runtime.gateway.base import Message, get_platform
        try:
            platform_obj = get_platform("wechat")
            await platform_obj.configure()
            await platform_obj.send(
                Message(text=f"❌ 处理失败: {exc}"), target=userid,
            )
        except Exception:
            pass


# ── 钉钉 (DingTalk) ─────────────────────────────────────────────────


@router.post("/dingtalk")
async def dingtalk_webhook(request: Request, bg: BackgroundTasks):
    """Receive DingTalk app callbacks.

    Verifies HMAC-SHA256 signature, extracts text, and dispatches to kernel.
    """
    # Verify signature
    timestamp = request.headers.get("timestamp", "")
    sign = request.headers.get("sign", "")
    if timestamp and sign:
        if not _verify_dingtalk_signature(timestamp, sign):
            raise HTTPException(status_code=401, detail="invalid signature")

    try:
        data: dict = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON")

    # DingTalk callback types: check_for_url (verification) or event
    # URL verification challenge
    if data.get("eventType") == "check_url":
        return JSONResponse(data)  # Echo back for verification

    # Extract sender and group info
    sender_id = data.get("senderId") or data.get("senderStaffId") or ""
    conversation_id = data.get("conversationId") or data.get("sessionWebhook", "")

    text = _extract_text_from_payload("dingtalk", data)
    if not text:
        text = (data.get("text", {}) or {}).get("content", "")

    if not text:
        return JSONResponse({"status": "ignored", "reason": "no text"})

    target = sender_id or conversation_id
    bg.add_task(
        _process_async_with_reply, text, "dingtalk", target, sender_id,
    )
    return JSONResponse({"status": "accepted"})


async def _process_async_with_reply(text: str, platform: str, target: str,
                                      sender: str) -> None:
    """Background task: process IM message and reply to sender."""
    try:
        result = await process_im_message(text, platform, target=sender)
        if not result.ok:
            logger.warning("{} IM process failed: {}", platform, result.error)
    except Exception as exc:
        logger.exception("{} IM processing crashed: {}", platform, exc)


# ── QQ Bot ───────────────────────────────────────────────────────────


@router.post("/qqbot")
async def qqbot_webhook(request: Request, bg: BackgroundTasks):
    """Receive QQ Bot webhook events.

    Verifies Ed25519 signature, extracts message text, dispatches to kernel.
    """
    body = await request.body()
    signature = request.headers.get("X-Signature-Ed25519", "")
    timestamp = request.headers.get("X-Signature-Timestamp", "")

    # Verify signature
    if signature and timestamp:
        if not _verify_qqbot_signature(body, signature, timestamp):
            raise HTTPException(status_code=401, detail="invalid signature")

    try:
        data: dict = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid JSON")

    op = data.get("op", -1)

    # Heartbeat / Hello — respond with heartbeat ACK
    if op == 1:  # HELLO
        return JSONResponse({"op": 1})
    if op == 10:  # HEARTBEAT
        return JSONResponse({"op": 11})  # HEARTBEAT_ACK
    if op == 13:  # HTTP callback validation
        return JSONResponse({"plain_token": data.get("d", {}).get("plain_token", "")})

    # op=0: dispatched event
    if op != 0:
        return JSONResponse({"status": "ignored", "reason": f"unsupported op {op}"})

    event_type = data.get("t", "")

    # Only handle message events
    if event_type not in (
        "C2C_MESSAGE_CREATE",
        "AT_MESSAGE_CREATE",
        "GROUP_AT_MESSAGE_CREATE",
        "MESSAGE_CREATE",
        "DIRECT_MESSAGE_CREATE",
    ):
        return JSONResponse({"status": "ignored", "reason": f"event {event_type}"})

    text = _extract_text_from_payload("qqbot", data)
    if not text:
        return JSONResponse({"status": "ignored", "reason": "no text"})

    # Extract author for reply target
    d = data.get("d", {})
    author = d.get("author", {})
    user_openid = author.get("id") or author.get("user_openid") or ""

    # Build target: "user:<openid>" for C2C, "group:<openid>" for group
    if event_type in ("GROUP_AT_MESSAGE_CREATE",):
        target = f"group:{d.get('group_openid', d.get('group_id', ''))}"
    elif event_type == "C2C_MESSAGE_CREATE":
        target = f"user:{user_openid}"
    else:
        target = f"user:{user_openid}"

    bg.add_task(_process_async_with_reply, text, "qqbot", target, user_openid)
    return JSONResponse({"status": "accepted"})


# ── background processing ────────────────────────────────────────────


async def _process_async(text: str, platform_name: str, target: str | None) -> None:
    """Background task: process IM message and reply."""
    try:
        result = await process_im_message(text, platform_name, target=target)
        if not result.ok:
            logger.warning("IM process failed for {}: {}", platform_name, result.error)
    except Exception as exc:
        logger.exception("IM processing crashed for {}: {}", platform_name, exc)
