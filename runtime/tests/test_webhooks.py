"""TDD: IM webhook endpoints — payload parsing, verification, response formatting."""

from __future__ import annotations

import json

import pytest


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

    def test_no_public_key_allows_in_dev(self):
        from runtime.api.endpoints.webhooks import _verify_discord_signature
        import os
        # Ensure no public key set
        old_key = os.environ.pop("DISCORD_PUBLIC_KEY", None)
        try:
            assert _verify_discord_signature(b"{}", "bad_sig", "123") is True
        finally:
            if old_key:
                os.environ["DISCORD_PUBLIC_KEY"] = old_key

    def test_invalid_signature_rejected(self):
        from runtime.api.endpoints.webhooks import _verify_discord_signature
        import os

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
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from runtime.api.endpoints.webhooks import router

        # Isolated app — avoids cross-test event loop pollution in full suite
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        response = client.post(
            "/webhooks/feishu",
            json={"challenge": "verify_me_abc123", "token": "x"},
        )
        assert response.status_code == 200
        assert response.json()["challenge"] == "verify_me_abc123"


class TestTelegramWebhook:
    """Test Telegram webhook endpoint."""

    def test_no_text_returns_ignored(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from runtime.api.endpoints.webhooks import router

        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        response = client.post("/webhooks/telegram", json={"message": {}})
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    def test_text_accepted(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from runtime.api.endpoints.webhooks import router

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
        )
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"


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
