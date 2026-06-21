"""IM Bot adapter — 微信/飞书/钉钉 unified messaging (Sprint 8)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IMMessage:
    platform: str  # wechat | feishu | dingtalk
    user_id: str
    text: str
    group_id: str = ""
    message_id: str = ""


@dataclass
class IMResponse:
    text: str
    ok: bool = True
    error: str | None = None


@dataclass
class IMBotConfig:
    enabled_platforms: list[str] = field(default_factory=lambda: ["wechat", "feishu", "dingtalk"])
    command_whitelist: list[str] = field(default_factory=lambda: [
        "tagent run", "tagent status", "tagent report",
        "tagent skill list", "tagent skill search",
        "tagent catalog", "tagent doctor",
    ])
    max_message_length: int = 2000
    session_timeout_minutes: int = 30


class IMBotRouter:
    """Route IM messages to Agent execution and return results."""

    def __init__(self, config: IMBotConfig | None = None):
        self._config = config or IMBotConfig()
        self._sessions: dict[str, dict] = {}  # user_id -> session state

    def check_permission(self, msg: IMMessage) -> bool:
        """Check if the message is in the command whitelist."""
        if msg.platform not in self._config.enabled_platforms:
            return False
        text = msg.text.strip().lower()
        return any(text.startswith(cmd) for cmd in self._config.command_whitelist)

    def route(self, msg: IMMessage) -> IMResponse:
        """Route an IM message and return a response."""
        if not self.check_permission(msg):
            return IMResponse(
                ok=False,
                text="权限不足 — 该命令不在白名单中。可用命令: " + ", ".join(self._config.command_whitelist),
                error="permission_denied",
            )

        if len(msg.text) > self._config.max_message_length:
            return IMResponse(ok=False, text="消息过长，请控制在2000字符以内", error="message_too_long")

        # Simulate Agent execution (in production, calls process_im_message)
        user_session = self._sessions.get(msg.user_id, {"count": 0})
        user_session["count"] += 1
        self._sessions[msg.user_id] = user_session

        text = msg.text
        if text.startswith("tagent status"):
            return IMResponse(text=f"Test-Agent V2.0.0 运行中 | 会话数: {len(self._sessions)} | 你的第{user_session['count']}次请求")
        elif text.startswith("tagent run"):
            task = text.replace("tagent run", "").strip()
            return IMResponse(text=f"已收到测试请求: {task}\n正在执行中，完成后通知你...")
        elif text.startswith("tagent report"):
            return IMResponse(text="最近测试结果:\n12/12 冒烟测试通过\n29 SDK测试通过")
        elif text.startswith("tagent catalog"):
            return IMResponse(text="Test-Agent V2.0.0\n16 Expert + 37 Skill\nSprint 0-7 已完成")
        elif text.startswith("tagent doctor"):
            return IMResponse(text="健康检查: 系统正常\nLLM: 未配置(离线模式可用)")
        elif text.startswith("tagent skill list"):
            return IMResponse(text="已安装37个Skill\n使用 tagent skill search <关键词> 搜索")
        elif text.startswith("tagent skill search"):
            kw = text.replace("tagent skill search", "").strip()
            return IMResponse(text=f"搜索 '{kw}': http-check, ping-check, file-check 等")
        else:
            return IMResponse(text=f"命令已接收: {msg.text[:100]}")
