"""TDD: IM webhook endpoints — payload parsing, verification, response formatting.

本文件中所有 secret/签名均为虚构测试数据，不是真实凭据。
All secrets and signatures are fake test fixtures — not real credentials.
"""

from __future__ import annotations

import json


class TestPayloadExtraction:
    """Test _extract_text_from_payload for each platform."""

    def test_telegram_text_message(self):
        from runtime.api.endpoints.webhooks import _extract_text_from_payload
        payload = {
            "message": {
                "text": "test the login page",
                "chat": {"id": 123456},
                "from": {"username": "tester"},
            }
        }
        assert _extract_text_from_payload("telegram", payload) == "test the login page"

    def test_telegram_caption_fallback(self):
        from runtime.api.endpoints.webhooks import _extract_text_from_payload
        payload = {
            "message": {
                "caption": "check this screenshot for bugs",
                "chat": {"id": 123456},
            }
        }
        assert _extract_text_from_payload("telegram", payload) == "check this screenshot for bugs"

    def test_telegram_no_text(self):
        from runtime.api.endpoints.webhooks import _extract_text_from_payload
        payload = {"message": {"chat": {"id": 123456}}}
        assert _extract_text_from_payload("telegram", payload) is None

    def test_discord_slash_command(self):
        from runtime.api.endpoints.webhooks import _extract_text_from_payload
        payload = {
            "type": 2,
            "data": {
                "name": "test",
                "options": [{"name": "request", "value": "smoke test the API"}],
            },
        }
        text = _extract_text_from_payload("discord", payload)
        assert "test" in text
        assert "smoke test the API" in text

    def test_discord_no_options(self):
        from runtime.api.endpoints.webhooks import _extract_text_from_payload
        payload = {
            "type": 2,
            "data": {"name": "test"},
        }
        assert _extract_text_from_payload("discord", payload) == "test"

    def test_feishu_text_message(self):
        from runtime.api.endpoints.webhooks import _extract_text_from_payload
        payload = {
            "event": {
                "text": "run regression test",
                "sender_id": "ou_xxx",
            }
        }
        assert _extract_text_from_payload("feishu", payload) == "run regression test"

    def test_feishu_rich_text_content(self):
        from runtime.api.endpoints.webhooks import _extract_text_from_payload
        payload = {
            "event": {
                "content": '{"text": "run security scan"}',
                "sender_id": "ou_xxx",
            }
        }
        assert _extract_text_from_payload("feishu", payload) == "run security scan"

    def test_feishu_empty(self):
        from runtime.api.endpoints.webhooks import _extract_text_from_payload
        payload = {"event": {}}
        assert _extract_text_from_payload("feishu", payload) is None


class TestSenderExtraction:
    """Test _extract_sender for each platform."""

    def test_telegram_username(self):
        from runtime.api.endpoints.webhooks import _extract_sender
        payload = {
            "message": {"from": {"username": "qa_engineer", "id": 111}}
        }
        assert _extract_sender(payload) == "qa_engineer"

    def test_telegram_fallback_to_id(self):
        from runtime.api.endpoints.webhooks import _extract_sender
        payload = {
            "message": {"from": {"id": 999, "first_name": "Tester"}}
        }
        assert _extract_sender(payload) == "Tester"

    def test_telegram_no_sender(self):
        from runtime.api.endpoints.webhooks import _extract_sender
        payload = {"message": {}}
        assert _extract_sender(payload) == "unknown"

    def test_discord_member(self):
        from runtime.api.endpoints.webhooks import _extract_sender
        payload = {
            "member": {"user": {"username": "dev_user", "id": "222"}}
        }
        assert _extract_sender(payload) == "dev_user"

    def test_feishu_sender(self):
        from runtime.api.endpoints.webhooks import _extract_sender
        payload = {
            "event": {"sender_id": "ou_abc123"}
        }
        assert _extract_sender(payload) == "ou_abc123"


class TestDiscordSignatureVerification:
    """Test Ed25519 signature verification for Discord."""

    def test_no_public_key_rejected_even_in_dev(self):
        import os

        from runtime.api.endpoints.webhooks import _verify_discord_signature
        # dev mode no longer bypasses verification — fail-closed everywhere
        old_key = os.environ.pop("DISCORD_PUBLIC_KEY", None)
        os.environ["TAGENT_ENV"] = "dev"
        try:
            assert _verify_discord_signature(b"{}", "bad_sig", "123") is False
        finally:
            if old_key:
                os.environ["DISCORD_PUBLIC_KEY"] = old_key
            os.environ.pop("TAGENT_ENV", None)

    def test_invalid_signature_rejected(self):
        import os

        from runtime.api.endpoints.webhooks import _verify_discord_signature

        # Valid Ed25519 public key (test key — not a real Discord key)
        test_pubkey = "00" * 32  # 32 bytes hex
        os.environ["DISCORD_PUBLIC_KEY"] = test_pubkey
        try:
            result = _verify_discord_signature(b'{"type":1}', "00" * 64, "1234567890")
            assert result is False  # invalid signature
        finally:
            os.environ.pop("DISCORD_PUBLIC_KEY", None)


class TestFeishuChallenge:
    """Test 飞书 URL verification — direct logic test (avoids TestClient cross-suite contamination)."""

    def test_challenge_logic(self):
        """Challenge echo is the core logic; verify without full app."""
        import os

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        # Isolated app — avoids cross-test event loop pollution in full suite
        os.environ["FEISHU_VERIFICATION_TOKEN"] = "x"
        try:
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)
            response = client.post(
                "/webhooks/feishu",
                json={"challenge": "verify_me_abc123", "token": "x"},
            )
            assert response.status_code == 200
            assert response.json()["challenge"] == "verify_me_abc123"
        finally:
            os.environ.pop("FEISHU_VERIFICATION_TOKEN", None)


class TestTelegramWebhook:
    """Test Telegram webhook endpoint."""

    def test_no_text_returns_ignored(self):
        import os

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        os.environ["TELEGRAM_SECRET_TOKEN"] = "tg-secret-123"
        try:
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)
            response = client.post(
                "/webhooks/telegram",
                json={"message": {}},
                headers={"X-Telegram-Bot-Api-Secret-Token": "tg-secret-123"},
            )
            assert response.status_code == 200
            assert response.json()["status"] == "ignored"
        finally:
            os.environ.pop("TELEGRAM_SECRET_TOKEN", None)

    def test_text_accepted(self):
        import os

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        os.environ["TELEGRAM_SECRET_TOKEN"] = "tg-secret-123"
        try:
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)
            response = client.post(
                "/webhooks/telegram",
                json={
                    "message": {
                        "text": "hello",
                        "chat": {"id": 123},
                        "from": {"username": "tester"},
                    }
                },
                headers={"X-Telegram-Bot-Api-Secret-Token": "tg-secret-123"},
            )
            assert response.status_code == 200
            assert response.json()["status"] == "accepted"
        finally:
            os.environ.pop("TELEGRAM_SECRET_TOKEN", None)

    def test_missing_secret_token_rejected(self):
        """POST without X-Telegram-Bot-Api-Secret-Token must be 401."""
        import os

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        os.environ["TELEGRAM_SECRET_TOKEN"] = "tg-secret-123"
        try:
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)
            response = client.post("/webhooks/telegram", json={"message": {"text": "hi"}})
            assert response.status_code == 401
        finally:
            os.environ.pop("TELEGRAM_SECRET_TOKEN", None)

    def test_wrong_secret_token_rejected(self):
        import os

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        os.environ["TELEGRAM_SECRET_TOKEN"] = "tg-secret-123"
        try:
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)
            response = client.post(
                "/webhooks/telegram",
                json={"message": {"text": "hi"}},
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
            )
            assert response.status_code == 401
        finally:
            os.environ.pop("TELEGRAM_SECRET_TOKEN", None)

    def test_unconfigured_secret_rejected(self):
        """Without TELEGRAM_SECRET_TOKEN set, requests are rejected (fail-closed)."""
        import os

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        os.environ.pop("TELEGRAM_SECRET_TOKEN", None)
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        response = client.post("/webhooks/telegram", json={"message": {"text": "hi"}})
        assert response.status_code == 401


class TestBridgeFormatting:
    """Test DAG summary text formatting."""

    def test_all_ok(self):
        from runtime.gateway.bridge import _format_dag_summary

        summary = {
            "total": 3,
            "succeeded": 3,
            "failed": 0,
            "results": {
                "a": {"name": "smoke-test", "ok": True, "duration_ms": 150},
                "b": {"name": "bug-manager", "ok": True, "duration_ms": 0},
                "c": {"name": "report-generator", "ok": True, "duration_ms": 200},
            },
        }
        text = _format_dag_summary(summary)
        assert "3/3 ok" in text
        assert "smoke-test" in text
        assert "All checks passed" in text

    def test_some_failed(self):
        from runtime.gateway.bridge import _format_dag_summary

        summary = {
            "total": 4,
            "succeeded": 3,
            "failed": 1,
            "results": {
                "a": {"name": "req-analyst", "ok": True, "duration_ms": 100},
                "b": {"name": "automation", "ok": False, "duration_ms": 500},
            },
        }
        text = _format_dag_summary(summary)
        assert "3/4 ok" in text
        assert "1 failed" in text
        assert "❌" in text

    def test_max_nodes_truncation(self):
        from runtime.gateway.bridge import _format_dag_summary

        results = {}
        for i in range(15):
            results[str(i)] = {"name": f"node-{i}", "ok": True, "duration_ms": 10}

        summary = {"total": 15, "succeeded": 15, "failed": 0, "results": results}
        text = _format_dag_summary(summary, max_nodes=5)
        assert "…" in text or "+" in text  # truncated indicator
        assert "node-0" in text
        # Should not mention all 15 nodes
        assert text.count("node-") <= 6

    def test_empty_results(self):
        from runtime.gateway.bridge import _format_dag_summary

        summary = {"total": 0, "succeeded": 0, "failed": 0, "results": {}}
        text = _format_dag_summary(summary)
        assert "0/0 ok" in text


# ── WeChat Work crypto ────────────────────────────────────────────────


class TestWeChatCrypto:
    """Test WeChat Work AES decryption, signature verification, XML parsing."""

    def test_signature_verification(self):
        from runtime.api.endpoints.webhooks import _wechat_verify_signature

        token = "test_token"
        ts = "1234567890"
        nonce = "test_nonce"
        encrypt = "encrypted_msg_content"
        # SHA1(sort(token, ts, nonce, encrypt))
        import hashlib
        expected = hashlib.sha1(
            "".join(sorted([token, ts, nonce, encrypt])).encode()
        ).hexdigest()
        assert _wechat_verify_signature(token, ts, nonce, encrypt, expected) is True

    def test_signature_mismatch(self):
        from runtime.api.endpoints.webhooks import _wechat_verify_signature
        assert _wechat_verify_signature("a", "1", "2", "3", "bad_signature") is False

    def test_decrypt_roundtrip(self):
        """Encrypt a known message, then decrypt it — verify roundtrip."""
        import base64
        import os
        import struct

        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        from runtime.api.endpoints.webhooks import _wechat_decrypt

        aes_key = os.urandom(32)
        # EncodingAESKey is 43-char base64 of aes_key
        encoding_aes_key = base64.b64encode(aes_key).decode()[:43]

        plain_xml = "<xml><ToUserName><![CDATA[corp123]]></ToUserName><FromUserName><![CDATA[user456]]></FromUserName><CreateTime>1234567890</CreateTime><MsgType><![CDATA[text]]></MsgType><Content><![CDATA[hello test]]></Content><MsgId>1</MsgId><AgentID>1000002</AgentID></xml>"
        plain_bytes = plain_xml.encode("utf-8")

        # Build buffer: random(16) + msg_len(4 big-endian) + msg + corpid
        random_bytes = os.urandom(16)
        msg_len = struct.pack(">I", len(plain_bytes))
        buffer = random_bytes + msg_len + plain_bytes + b"corp123"

        # PKCS#7 padding
        block_size = 32
        pad = block_size - len(buffer) % block_size
        buffer += bytes([pad]) * pad

        # AES-256-CBC encrypt
        iv = aes_key[:16]
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        encrypted = encryptor.update(buffer) + encryptor.finalize()
        encrypted_b64 = base64.b64encode(encrypted).decode()

        # Decrypt
        result = _wechat_decrypt(encrypted_b64, encoding_aes_key)
        assert result == plain_xml

    def test_parse_wechat_xml_text(self):
        from runtime.api.endpoints.webhooks import _parse_wechat_xml

        xml = """<xml>
<ToUserName><![CDATA[corp123]]></ToUserName>
<FromUserName><![CDATA[zhangsan]]></FromUserName>
<CreateTime>1234567890</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[run smoke test]]></Content>
<MsgId>100</MsgId>
<AgentID>1000002</AgentID>
</xml>"""
        parsed = _parse_wechat_xml(xml)
        assert parsed["from_user"] == "zhangsan"
        assert parsed["msg_type"] == "text"
        assert parsed["content"] == "run smoke test"
        assert parsed["agent_id"] == "1000002"


# ── DingTalk ──────────────────────────────────────────────────────────


class TestDingTalkCrypto:
    """Test DingTalk HMAC-SHA256 signature verification."""

    def test_valid_signature(self):
        import base64
        import hashlib
        import hmac
        import os
        import time

        from runtime.api.endpoints.webhooks import _verify_dingtalk_signature

        secret = "test_app_secret_123"
        os.environ["DINGTALK_APP_SECRET"] = secret
        ts = str(int(time.time() * 1000))
        message = ts + "\n" + secret
        expected = base64.b64encode(
            hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
        ).decode()
        try:
            assert _verify_dingtalk_signature(ts, expected) is True
        finally:
            os.environ.pop("DINGTALK_APP_SECRET", None)

    def test_invalid_signature(self):
        import os
        import time

        from runtime.api.endpoints.webhooks import _verify_dingtalk_signature

        os.environ["DINGTALK_APP_SECRET"] = "secret"
        try:
            ts = str(int(time.time() * 1000))
            assert _verify_dingtalk_signature(ts, "wrong_signature") is False
        finally:
            os.environ.pop("DINGTALK_APP_SECRET", None)

    def test_stale_timestamp_rejected(self):
        """Timestamp outside the 5-minute window must be rejected (replay protection)."""
        import base64
        import hashlib
        import hmac
        import os

        from runtime.api.endpoints.webhooks import _verify_dingtalk_signature

        secret = "test_app_secret_123"
        os.environ["DINGTALK_APP_SECRET"] = secret
        ts = "1680000000000"  # 2023 — far outside the 5-minute window
        message = ts + "\n" + secret
        expected = base64.b64encode(
            hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
        ).decode()
        try:
            assert _verify_dingtalk_signature(ts, expected) is False
        finally:
            os.environ.pop("DINGTALK_APP_SECRET", None)

    def test_non_numeric_timestamp_rejected(self):
        import os

        from runtime.api.endpoints.webhooks import _verify_dingtalk_signature

        os.environ["DINGTALK_APP_SECRET"] = "secret"
        try:
            assert _verify_dingtalk_signature("not-a-number", "any") is False
        finally:
            os.environ.pop("DINGTALK_APP_SECRET", None)

    def test_no_secret_rejected_even_in_dev(self):
        import os

        from runtime.api.endpoints.webhooks import _verify_dingtalk_signature

        old = os.environ.pop("DINGTALK_APP_SECRET", None)
        os.environ["TAGENT_ENV"] = "dev"
        try:
            assert _verify_dingtalk_signature("123", "any") is False
        finally:
            os.environ.pop("TAGENT_ENV", None)
            if old:
                os.environ["DINGTALK_APP_SECRET"] = old


# ── QQ Bot ────────────────────────────────────────────────────────────


class TestQQBotCrypto:
    """Test QQ Bot Ed25519 signature verification."""

    def test_no_public_key_rejected_even_in_dev(self):
        import os

        from runtime.api.endpoints.webhooks import _verify_qqbot_signature

        old = os.environ.pop("QQBOT_PUBLIC_KEY", None)
        os.environ["TAGENT_ENV"] = "dev"
        try:
            assert _verify_qqbot_signature(b"{}", "bad_sig", "123") is False
        finally:
            os.environ.pop("TAGENT_ENV", None)
            if old:
                os.environ["QQBOT_PUBLIC_KEY"] = old

    def test_invalid_signature_rejected(self):
        import os

        from runtime.api.endpoints.webhooks import _verify_qqbot_signature

        test_pubkey = "00" * 32  # 32 bytes hex
        os.environ["QQBOT_PUBLIC_KEY"] = test_pubkey
        try:
            result = _verify_qqbot_signature(b'{"op":0}', "00" * 64, "1234567890")
            assert result is False
        finally:
            os.environ.pop("QQBOT_PUBLIC_KEY", None)


# ── Payload extraction (new platforms) ────────────────────────────────


class TestPayloadExtractionNew:
    """Test _extract_text_from_payload for 钉钉 and QQ Bot."""

    def test_dingtalk_text(self):
        from runtime.api.endpoints.webhooks import _extract_text_from_payload

        payload = {
            "msg": {"text": {"content": "run regression test"}},
            "senderId": "user001",
        }
        assert _extract_text_from_payload("dingtalk", payload) == "run regression test"

    def test_dingtalk_empty(self):
        from runtime.api.endpoints.webhooks import _extract_text_from_payload

        payload = {"msg": {}, "senderId": "user001"}
        assert _extract_text_from_payload("dingtalk", payload) is None

    def test_qqbot_c2c_text(self):
        from runtime.api.endpoints.webhooks import _extract_text_from_payload

        payload = {
            "op": 0,
            "t": "C2C_MESSAGE_CREATE",
            "d": {
                "content": "test the login flow",
                "author": {"id": "openid_abc"},
            },
        }
        assert _extract_text_from_payload("qqbot", payload) == "test the login flow"

    def test_qqbot_no_content(self):
        from runtime.api.endpoints.webhooks import _extract_text_from_payload

        payload = {"op": 0, "t": "MESSAGE_CREATE", "d": {}}
        assert _extract_text_from_payload("qqbot", payload) is None

    def test_qqbot_attachment_content(self):
        from runtime.api.endpoints.webhooks import _extract_text_from_payload

        payload = {
            "op": 0,
            "t": "AT_MESSAGE_CREATE",
            "d": {
                "content": "",
                "attachments": [{"content": "check the API"}],
            },
        }
        assert _extract_text_from_payload("qqbot", payload) == "check the API"


# ── Webhook endpoint integration tests ────────────────────────────────


class TestWeChatWebhook:
    """Test 企微 webhook endpoint — GET/POST contract."""

    def test_get_missing_params_400(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        resp = client.get("/webhooks/wechat")
        assert resp.status_code == 400

    def test_post_missing_config_400(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        resp = client.post("/webhooks/wechat", content="<xml></xml>")
        assert resp.status_code == 400

    def test_get_valid_echostr_returns_plaintext(self):
        """Full URL verification flow with known keys."""
        import base64
        import hashlib
        import os
        import struct

        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        # Setup test keys
        token = "test_wx_token"
        aes_key = os.urandom(32)
        encoding_aes_key = base64.b64encode(aes_key).decode()[:43]
        echostr_plain = "verify_ok_123"

        # Encrypt echostr same way WeChat does
        random_bytes = os.urandom(16)
        msg_bytes = echostr_plain.encode("utf-8")
        msg_len = struct.pack(">I", len(msg_bytes))
        buffer = random_bytes + msg_len + msg_bytes + b"test_corp_id"

        # AES block size = 16 (not 32)
        block_size = 16
        pad = block_size - len(buffer) % block_size
        buffer += bytes([pad]) * pad

        iv = aes_key[:16]
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        encrypted = base64.b64encode(encryptor.update(buffer) + encryptor.finalize()).decode()

        ts = "1680000000"
        nonce = "test_nonce"
        # Use the original encrypted string for signature (before URL encoding)
        sig = hashlib.sha1(
            "".join(sorted([token, ts, nonce, encrypted])).encode()
        ).hexdigest()

        os.environ["WECHAT_TOKEN"] = token
        os.environ["WECHAT_ENCODING_AES_KEY"] = encoding_aes_key
        try:
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)
            # Use params= dict so httpx properly URL-encodes base64 chars (+ / =)
            resp = client.get("/webhooks/wechat", params={
                "msg_signature": sig,
                "timestamp": ts,
                "nonce": nonce,
                "echostr": encrypted,
            })
            assert resp.status_code == 200
            assert resp.text == echostr_plain
        finally:
            os.environ.pop("WECHAT_TOKEN", None)
            os.environ.pop("WECHAT_ENCODING_AES_KEY", None)

    def test_post_stale_timestamp_rejected(self):
        """Replayed POST callback with valid signature but stale timestamp must be 403."""
        import base64
        import hashlib
        import os
        import struct

        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        token = "test_wx_token"
        aes_key = os.urandom(32)
        encoding_aes_key = base64.b64encode(aes_key).decode()[:43]
        msg_bytes = b"<xml><MsgType><![CDATA[text]]></MsgType><Content><![CDATA[hi]]></Content></xml>"
        random_bytes = os.urandom(16)
        buffer = random_bytes + struct.pack(">I", len(msg_bytes)) + msg_bytes + b"test_corp_id"
        block_size = 16
        pad = block_size - len(buffer) % block_size
        buffer += bytes([pad]) * pad
        iv = aes_key[:16]
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        encrypted = base64.b64encode(encryptor.update(buffer) + encryptor.finalize()).decode()

        ts = "1680000000"  # 2023 — stale
        nonce = "test_nonce"
        sig = hashlib.sha1(
            "".join(sorted([token, ts, nonce, encrypted])).encode()
        ).hexdigest()

        os.environ["WECHAT_TOKEN"] = token
        os.environ["WECHAT_ENCODING_AES_KEY"] = encoding_aes_key
        try:
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)
            resp = client.post(
                "/webhooks/wechat",
                params={"msg_signature": sig, "timestamp": ts, "nonce": nonce},
                content=f"<xml><Encrypt><![CDATA[{encrypted}]]></Encrypt></xml>",
                headers={"Content-Type": "application/xml"},
            )
            assert resp.status_code == 403
        finally:
            os.environ.pop("WECHAT_TOKEN", None)
            os.environ.pop("WECHAT_ENCODING_AES_KEY", None)


class TestDingTalkWebhook:
    """Test 钉钉 webhook endpoint."""

    @staticmethod
    def _signed_headers(secret: str, ts: str) -> dict:
        import base64
        import hashlib
        import hmac

        message = ts + "\n" + secret
        sign = base64.b64encode(
            hmac.new(secret.encode(), message.encode(), hashlib.sha256).digest()
        ).decode()
        return {"timestamp": ts, "sign": sign}

    def test_missing_signature_rejected(self):
        import os

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        old = os.environ.pop("DINGTALK_APP_SECRET", None)
        try:
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)
            # No timestamp/sign headers → fail-closed even if secret unset
            resp = client.post("/webhooks/dingtalk", json={"msg": {}})
            assert resp.status_code == 401
        finally:
            if old:
                os.environ["DINGTALK_APP_SECRET"] = old

    def test_no_text_returns_ignored(self):
        import os
        import time

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        secret = "test_app_secret_123"
        os.environ["DINGTALK_APP_SECRET"] = secret
        try:
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)
            resp = client.post(
                "/webhooks/dingtalk",
                json={"msg": {}},
                headers=self._signed_headers(secret, str(int(time.time() * 1000))),
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "ignored"
        finally:
            os.environ.pop("DINGTALK_APP_SECRET", None)

    def test_text_accepted(self):
        import os
        import time

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        secret = "test_app_secret_123"
        os.environ["DINGTALK_APP_SECRET"] = secret
        try:
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)
            resp = client.post(
                "/webhooks/dingtalk",
                json={
                    "msg": {"text": {"content": "run smoke test"}},
                    "senderId": "user001",
                },
                headers=self._signed_headers(secret, str(int(time.time() * 1000))),
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "accepted"
        finally:
            os.environ.pop("DINGTALK_APP_SECRET", None)


class TestQQBotWebhook:
    """Test QQ Bot webhook endpoint."""

    @staticmethod
    def _sign(body: bytes) -> tuple[str, str]:
        """Return (public_key_hex, (signature, timestamp)) for a signed post."""
        import time

        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        key = Ed25519PrivateKey.generate()
        ts = str(int(time.time()))
        sig = key.sign(ts.encode() + body).hex()
        return key.public_key().public_bytes_raw().hex(), (sig, ts)

    def test_heartbeat_ack(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        resp = client.post("/webhooks/qqbot", json={"op": 10})
        assert resp.status_code == 200
        assert resp.json()["op"] == 11

    def test_hello_ack(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        resp = client.post("/webhooks/qqbot", json={"op": 1})
        assert resp.status_code == 200
        assert resp.json()["op"] == 1

    def test_unsigned_dispatch_rejected(self):
        import os

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        old = os.environ.pop("QQBOT_PUBLIC_KEY", None)
        try:
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)
            # op=0 without signature headers → fail-closed 401
            resp = client.post(
                "/webhooks/qqbot",
                json={"op": 0, "t": "GUILD_CREATE", "d": {}},
            )
            assert resp.status_code == 401
        finally:
            if old:
                os.environ["QQBOT_PUBLIC_KEY"] = old

    def test_non_message_event_ignored(self):
        import json as _json
        import os

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        payload = {"op": 0, "t": "GUILD_CREATE", "d": {}}
        body = _json.dumps(payload).encode()
        pubkey, (sig, ts) = self._sign(body)
        os.environ["QQBOT_PUBLIC_KEY"] = pubkey
        try:
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)
            resp = client.post(
                "/webhooks/qqbot",
                content=body,
                headers={"X-Signature-Ed25519": sig, "X-Signature-Timestamp": ts},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "ignored"
        finally:
            os.environ.pop("QQBOT_PUBLIC_KEY", None)

    def test_c2c_message_accepted(self):
        import json as _json
        import os

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        payload = {
            "op": 0,
            "t": "C2C_MESSAGE_CREATE",
            "d": {
                "content": "test login",
                "author": {"id": "openid_abc"},
            },
        }
        body = _json.dumps(payload).encode()
        pubkey, (sig, ts) = self._sign(body)
        os.environ["QQBOT_PUBLIC_KEY"] = pubkey
        try:
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)
            resp = client.post(
                "/webhooks/qqbot",
                content=body,
                headers={"X-Signature-Ed25519": sig, "X-Signature-Timestamp": ts},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "accepted"
        finally:
            os.environ.pop("QQBOT_PUBLIC_KEY", None)


class TestFeishuSignatureVerification:
    """Feishu callback verification — fail-closed like Discord."""

    def test_unconfigured_rejected_outside_dev(self):
        import os

        from runtime.api.endpoints.webhooks import _verify_feishu

        os.environ.pop("FEISHU_VERIFICATION_TOKEN", None)
        os.environ.pop("TAGENT_ENV", None)
        assert _verify_feishu({}) is False

    def test_token_mismatch_rejected(self):
        import os

        from runtime.api.endpoints.webhooks import _verify_feishu

        os.environ["FEISHU_VERIFICATION_TOKEN"] = "expected-token"
        os.environ.pop("TAGENT_ENV", None)
        try:
            assert _verify_feishu({"token": "wrong"}) is False
        finally:
            os.environ.pop("FEISHU_VERIFICATION_TOKEN", None)

    def test_token_match_accepted(self):
        import os

        from runtime.api.endpoints.webhooks import _verify_feishu

        os.environ["FEISHU_VERIFICATION_TOKEN"] = "expected-token"
        os.environ.pop("TAGENT_ENV", None)
        try:
            assert _verify_feishu({"token": "expected-token"}) is True
        finally:
            os.environ.pop("FEISHU_VERIFICATION_TOKEN", None)

    def test_encrypted_payload_decrypted_and_verified(self):
        """Feishu encrypt-mode payload (no token field) must decrypt, then verify."""
        import base64
        import hashlib
        import os

        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        encrypt_key = "test-encrypt-key"
        token = "expected-token"
        inner = {"token": token, "challenge": "challenge-123"}
        key = hashlib.sha256(encrypt_key.encode()).digest()
        iv = key[:16]
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        encryptor = cipher.encryptor()
        plain = json.dumps(inner).encode()
        pad = 16 - len(plain) % 16
        plain += bytes([pad]) * pad
        encrypted = base64.b64encode(encryptor.update(plain) + encryptor.finalize()).decode()

        os.environ["FEISHU_VERIFICATION_TOKEN"] = token
        os.environ["FEISHU_ENCRYPT_KEY"] = encrypt_key
        try:
            app = FastAPI()
            app.include_router(router)
            client = TestClient(app)
            resp = client.post("/webhooks/feishu", json={"encrypt": encrypted})
            assert resp.status_code == 200
            assert resp.json().get("challenge") == "challenge-123"
        finally:
            os.environ.pop("FEISHU_VERIFICATION_TOKEN", None)
            os.environ.pop("FEISHU_ENCRYPT_KEY", None)

    def test_endpoint_rejects_unverified_message(self):
        import os

        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from runtime.api.endpoints.webhooks import router

        os.environ.pop("FEISHU_VERIFICATION_TOKEN", None)
        os.environ.pop("TAGENT_ENV", None)
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        response = client.post(
            "/webhooks/feishu",
            json={"header": {"event_type": "im.message.receive_v1"}, "event": {}},
        )
        assert response.status_code == 403
