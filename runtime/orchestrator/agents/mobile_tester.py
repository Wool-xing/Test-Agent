"""mobile-tester · LLM 读 PRD + 上游摘要 → 移动测试用例 + ADB/Xcode 命令清单.

V1.16.0 minimum viable (ROADMAP rollout #2 落地):
- 仅生成 mobile test cases + device commands + test_environment 结构化 JSON
- 不实装 10-移动测试.md 全部职责 (Appium driver 真跑 / 云真机集成 / 弱网 / 权限弹窗
  等留 V1.x 深化)
- 覆盖 Android / iOS 原生 + 微信/支付宝/抖音 小程序
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register


@register("mobile-tester")
class MobileTester(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 Test-Agent 项目内 mobile-tester 专家(agents/10-移动测试.md)。\n"
            "职责:基于 PRD + 上游摘要,生成移动端测试用例 + ADB/Xcode 命令清单。\n"
            "原则:\n"
            "1) 识别目标平台:Android / iOS / 微信/支付宝/抖音 小程序 / 混合 H5\n"
            "2) 测试用例覆盖移动专属:网络切换 / 弱网 / 后台 / 横竖屏 / 权限弹窗\n"
            "3) 设备命令优先 ADB(Android)/ xcrun(iOS),小程序用开发者工具 CLI\n"
            "4) 区分真机 / 模拟器 / 云真机(Sauce Labs / BrowserStack)适用场景\n"
            "5) 不假设具体设备型号,引用 env 变量名(TEST_ANDROID_DEVICE / TEST_IOS_UDID)\n"
            "输出严格 JSON,不要 markdown 代码块包裹。"
        )

    def user_prompt(self, ctx: RunnerContext) -> str:
        req_summary = ctx.upstream.get("requirements-analyst", {})
        features = req_summary.get("features", [])
        non_functional = req_summary.get("non_functional", {})
        return (
            f"## 原始 PRD(截断 4000 字符)\n```\n{ctx.artifact_text[:4000]}\n```\n\n"
            f"## 上游 requirements-analyst 摘要\n"
            f"- 功能数: {len(features)} (P0={sum(1 for f in features if f.get('priority') == 'P0')})\n"
            f"- 非功能要求: {non_functional}\n\n"
            "## 输出 schema\n"
            "{\n"
            '  "project_name": "string,简短项目名",\n'
            '  "target_platform": "android|ios|wechat-mp|alipay-mp|douyin-mp|hybrid|multi",\n'
            '  "test_cases": [\n'
            '    {"name": "string", "platform": "string", "priority": "P0|P1|P2|P3", "scenario": "string,场景描述含步骤"}\n'
            "  ],\n"
            '  "device_commands": [\n'
            '    {"platform": "android|ios|miniprogram", "cmd": "string,可执行 shell 命令", "purpose": "string"}\n'
            "  ],\n"
            '  "test_environment": {\n'
            '    "device_type": "real|emulator|cloud",\n'
            '    "os_versions": ["string,如 Android 13 / iOS 17"],\n'
            '    "tools": ["string,如 Appium 2.x / xcrun"]\n'
            "  },\n"
            '  "mobile_specific": [\n'
            '    {"category": "网络切换|弱网|后台|横竖屏|权限弹窗", "test_points": ["string"]}\n'
            "  ],\n"
            '  "risks": ["string,移动专属风险"],\n'
            '  "confidence": "high|medium|low"\n'
            "}"
        )

    def mock_output(self, ctx: RunnerContext) -> dict[str, Any]:  # noqa: ARG002
        return {
            "project_name": "selftest-fixture",
            "target_platform": "multi",
            "test_cases": [
                {
                    "name": "登录主流程(Android 真机)",
                    "platform": "android",
                    "priority": "P0",
                    "scenario": "启动 APP → 输入账密 → 点登录 → 验首页加载",
                },
                {
                    "name": "登录主流程(iOS 模拟器)",
                    "platform": "ios",
                    "priority": "P0",
                    "scenario": "同上,验 iOS 端 keychain session 持久化",
                },
            ],
            "device_commands": [
                {
                    "platform": "android",
                    "cmd": "adb -s \"$TEST_ANDROID_DEVICE\" shell pm list packages -3",
                    "purpose": "列已装第三方 APP 验环境干净",
                },
                {
                    "platform": "ios",
                    "cmd": "xcrun simctl list devices booted",
                    "purpose": "列已启动 iOS 模拟器",
                },
            ],
            "test_environment": {
                "device_type": "emulator",
                "os_versions": ["Android 13", "iOS 17"],
                "tools": ["Appium 2.x", "xcrun simctl", "adb"],
            },
            "mobile_specific": [
                {"category": "网络切换", "test_points": ["WiFi → 4G 切换 session 续期", "飞行模式恢复网络后重试"]},
                {"category": "后台", "test_points": ["APP 进入后台 5 min 后台 session 保活"]},
                {"category": "权限弹窗", "test_points": ["首次启动相机/位置权限弹窗自动允许"]},
            ],
            "risks": [
                "Android / iOS 行为差异需双平台同步用例",
                "云真机厂商 API 速率限制需 fallback 本地模拟器",
            ],
            "confidence": "medium",
            "_mode": "mock(stub provider)",
        }

    def output_file(self, ctx: RunnerContext) -> Path | None:
        return ctx.workspace / "执行日志" / "mobile_test_plan.json"

    def summary(self, output: dict[str, Any]) -> str:
        cases = len(output.get("test_cases", []))
        cmds = len(output.get("device_commands", []))
        specific = len(output.get("mobile_specific", []))
        platform = output.get("target_platform", "?")
        return f"移动用例 {cases} 条 / 设备命令 {cmds} / 移动专属 {specific} 大类 / 平台={platform}"
