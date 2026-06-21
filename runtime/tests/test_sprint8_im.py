"""TDD: Sprint 8 — IM Bot 适配层 (微信/飞书/钉钉)."""

from __future__ import annotations

import pytest


class TestIMBot:
    """IM Bot message routing and permission control."""

    def test_im_bot_imports(self):
        """IM Bot module should be importable."""
        from runtime.gateway.im_bot import IMBotRouter, IMBotConfig, IMMessage, IMResponse
        assert IMBotRouter is not None

    def test_command_whitelist_allows_valid(self):
        """Whitelisted commands should pass permission check."""
        from runtime.gateway.im_bot import IMBotRouter, IMMessage
        router = IMBotRouter()
        msg = IMMessage(platform="wechat", user_id="user1", text="tagent status")
        assert router.check_permission(msg) is True

    def test_command_whitelist_blocks_invalid(self):
        """Non-whitelisted commands should be rejected."""
        from runtime.gateway.im_bot import IMBotRouter, IMMessage
        router = IMBotRouter()
        msg = IMMessage(platform="wechat", user_id="user1", text="rm -rf /")
        assert router.check_permission(msg) is False

    def test_route_status_command(self):
        """tagent status via IM should return running status."""
        from runtime.gateway.im_bot import IMBotRouter, IMMessage
        router = IMBotRouter()
        msg = IMMessage(platform="wechat", user_id="u1", text="tagent status")
        resp = router.route(msg)
        assert resp.ok is True
        assert "Test-Agent" in resp.text or "运行中" in resp.text

    def test_route_permission_denied(self):
        """Non-whitelisted command should return permission denied."""
        from runtime.gateway.im_bot import IMBotRouter, IMMessage
        router = IMBotRouter()
        msg = IMMessage(platform="wechat", user_id="u1", text="delete everything")
        resp = router.route(msg)
        assert resp.ok is False
        assert "权限不足" in resp.text or "denied" in resp.text.lower()

    def test_disabled_platform_blocked(self):
        """Disabled platform should be blocked even with valid command."""
        from runtime.gateway.im_bot import IMBotRouter, IMMessage
        router = IMBotRouter()
        msg = IMMessage(platform="telegram", user_id="u1", text="tagent status")
        assert router.check_permission(msg) is False

    def test_route_run_command(self):
        """tagent run via IM should acknowledge receipt."""
        from runtime.gateway.im_bot import IMBotRouter, IMMessage
        router = IMBotRouter()
        msg = IMMessage(platform="dingtalk", user_id="u1", text="tagent run http-check")
        resp = router.route(msg)
        assert resp.ok is True
        assert "http-check" in resp.text

    def test_route_skill_list(self):
        """tagent skill list via IM should return skills."""
        from runtime.gateway.im_bot import IMBotRouter, IMMessage
        router = IMBotRouter()
        msg = IMMessage(platform="feishu", user_id="u1", text="tagent skill list")
        resp = router.route(msg)
        assert resp.ok is True
        assert "37" in resp.text or "Skill" in resp.text
