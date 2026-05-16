"""mobile-test skill · LLM 读上游 mobile-tester 产物 → 6 阶段移动端执行编排.

V1.23.0 minimum viable (ROADMAP skill rollout #2 落地):
- LLM 读 PRD + 上游 mobile-tester expert 产物 → 6 阶段执行计划
  (设备就绪 / Appium / 用例批次 / 性能采集 / Monkey / 报告归档)
  + 质量门禁 + 跨平台并行策略
- 不实装 03-技能定义/mobile-test.md 全部职责 (Appium driver 真跑 / 云真机
  / 弱网注入 / 小程序开发者工具 CLI 等留后续深化)
- 输出执行计划 JSON, 真执行守护在 utils 层 (mobile_driver.py / miniprogram_runner)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register_skill


@register_skill("mobile-test")
class MobileTest(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 Test-Agent 项目内 mobile-test skill(03-技能定义/mobile-test.md)。\n"
            "职责:基于 PRD + 上游 mobile-tester expert 产物,编排移动端测试 6 阶段执行计划。\n"
            "原则:\n"
            "1) 识别目标平台:Android / iOS / 微信/支付宝/抖音 小程序 / 混合 H5\n"
            "2) 设备就绪检查优先:adb devices / xcrun simctl / Appium status\n"
            "3) 测试用例按平台+优先级分批(先 P0 冒烟,后 P1-P3 完整)\n"
            "4) 移动专属场景必覆盖:弱网 / 后台 / 横竖屏 / 权限弹窗 / 网络切换\n"
            "5) 性能采集可选(冷启动 / FPS / 内存 / CPU)\n"
            "6) Monkey 稳定性可选(Android 1 万事件,crash=0 / anr=0)\n"
            "7) 不假设具体设备型号,引用 env 变量名(TEST_ANDROID_DEVICE / TEST_IOS_UDID)\n"
            "8) 云真机集成可选(Sauce Labs / BrowserStack),配置在 .env\n"
            "输出严格 JSON,不要 markdown 代码块包裹。"
        )

    def user_prompt(self, ctx: RunnerContext) -> str:
        req_summary = ctx.upstream.get("requirements-analyst", {})
        mobile_plan = ctx.upstream.get("mobile-tester", {})
        features = req_summary.get("features", [])
        test_cases = mobile_plan.get("test_cases", [])
        device_cmds = mobile_plan.get("device_commands", [])
        target_platform = mobile_plan.get("target_platform", "multi")
        mobile_specific = mobile_plan.get("mobile_specific", [])
        p0_count = sum(1 for tc in test_cases if tc.get("priority") == "P0")
        return (
            f"## 原始 PRD(截断 3000 字符)\n```\n{ctx.artifact_text[:3000]}\n```\n\n"
            f"## 上游 requirements-analyst 摘要\n"
            f"- 功能数: {len(features)} (P0={sum(1 for f in features if f.get('priority') == 'P0')})\n\n"
            f"## 上游 mobile-tester expert 产物\n"
            f"- 目标平台: {target_platform}\n"
            f"- 用例总数: {len(test_cases)} (P0={p0_count})\n"
            f"- 设备命令数: {len(device_cmds)}\n"
            f"- 移动专属大类: {len(mobile_specific)}\n\n"
            "## 输出 schema\n"
            "{\n"
            '  "project_name": "string,简短项目名",\n'
            '  "run_id": "string,UUID/timestamp 任务 id",\n'
            '  "target_platform": "android|ios|wechat-mp|alipay-mp|douyin-mp|hybrid|multi",\n'
            '  "phases": [\n'
            '    {"phase": 1, "name": "device_readiness", "estimated_min": 5, "commands": ["string,shell 命令"], "depends_on": []},\n'
            '    {"phase": 2, "name": "appium_setup", "estimated_min": 3, "commands": ["string"], "depends_on": ["device_readiness"]},\n'
            '    {"phase": 3, "name": "test_execution", "estimated_min": 30, "batches": [{"platform": "string", "priority": "P0|P1|P2|P3", "case_count": 0, "pytest_marker": "string"}], "depends_on": ["appium_setup"]},\n'
            '    {"phase": 4, "name": "performance_collection", "estimated_min": 10, "optional": true, "metrics": ["cold_start_ms", "fps", "memory_mb", "cpu_percent"], "depends_on": ["test_execution"]},\n'
            '    {"phase": 5, "name": "monkey_stability", "estimated_min": 30, "optional": true, "events": 10000, "throttle_ms": 200, "crash_threshold": 0, "anr_threshold": 0, "depends_on": ["test_execution"]},\n'
            '    {"phase": 6, "name": "report_archive", "estimated_min": 5, "outputs": ["string,路径"], "depends_on": ["test_execution"]}\n'
            "  ],\n"
            '  "quality_gates": {\n'
            '    "p0_pass_rate": 0.95,\n'
            '    "crash_rate_max": 0.001,\n'
            '    "anr_rate_max": 0.0005,\n'
            '    "cold_start_ms_max": 3000,\n'
            '    "fps_min": 55,\n'
            '    "monkey_crash": 0,\n'
            '    "monkey_anr": 0\n'
            "  },\n"
            '  "cross_platform": {\n'
            '    "parallel_enabled": true,\n'
            '    "workers": 2,\n'
            '    "strategy": "loadgroup (android/ios 各自 worker)"\n'
            "  },\n"
            '  "cloud_device": {\n'
            '    "enabled": false,\n'
            '    "providers": ["Sauce Labs", "BrowserStack"],\n'
            '    "fallback": "local emulator"\n'
            "  },\n"
            '  "mobile_specific_checks": ["string,如 弱网 WiFi→4G / 后台 5min / 横竖屏 / 权限弹窗"],\n'
            '  "outputs": {\n'
            '    "test_scripts_dir": "workspace/自动化脚本/python/mobile/",\n'
            '    "miniprogram_dir": "workspace/自动化脚本/python/miniprogram/",\n'
            '    "perf_dir": "workspace/执行日志/mobile-perf/",\n'
            '    "logcat_dir": "workspace/执行日志/logcat/",\n'
            '    "ios_syslog_dir": "workspace/执行日志/ios-syslog/",\n'
            '    "screenshot_dir": "workspace/执行日志/截图/",\n'
            '    "monkey_dir": "workspace/执行日志/monkey/",\n'
            '    "allure_dir": "workspace/Allure/mobile/{run_id}/"\n'
            "  },\n"
            '  "risks": ["string,如 设备断连 / Appium session 超时 / 云真机 API 限速"],\n'
            '  "confidence": "high|medium|low"\n'
            "}"
        )

    def mock_output(self, ctx: RunnerContext) -> dict[str, Any]:  # noqa: ARG002
        return {
            "project_name": "selftest-fixture",
            "run_id": "selftest-20260516-000002",
            "target_platform": "multi",
            "phases": [
                {
                    "phase": 1,
                    "name": "device_readiness",
                    "estimated_min": 5,
                    "commands": [
                        "adb devices",
                        "xcrun simctl list booted",
                        "curl http://localhost:4723/status",
                    ],
                    "depends_on": [],
                },
                {
                    "phase": 2,
                    "name": "appium_setup",
                    "estimated_min": 3,
                    "commands": [
                        "appium --port 4723 &",
                    ],
                    "depends_on": ["device_readiness"],
                },
                {
                    "phase": 3,
                    "name": "test_execution",
                    "estimated_min": 30,
                    "batches": [
                        {
                            "platform": "android",
                            "priority": "P0",
                            "case_count": 4,
                            "pytest_marker": "mobile and android and p0",
                        },
                        {
                            "platform": "ios",
                            "priority": "P0",
                            "case_count": 3,
                            "pytest_marker": "mobile and ios and p0",
                        },
                        {
                            "platform": "android",
                            "priority": "P1",
                            "case_count": 6,
                            "pytest_marker": "mobile and android and p1",
                        },
                    ],
                    "depends_on": ["appium_setup"],
                },
                {
                    "phase": 4,
                    "name": "performance_collection",
                    "estimated_min": 10,
                    "optional": True,
                    "metrics": ["cold_start_ms", "fps", "memory_mb", "cpu_percent"],
                    "depends_on": ["test_execution"],
                },
                {
                    "phase": 5,
                    "name": "monkey_stability",
                    "estimated_min": 30,
                    "optional": True,
                    "events": 10000,
                    "throttle_ms": 200,
                    "crash_threshold": 0,
                    "anr_threshold": 0,
                    "depends_on": ["test_execution"],
                },
                {
                    "phase": 6,
                    "name": "report_archive",
                    "estimated_min": 5,
                    "outputs": [
                        "workspace/Allure/mobile/selftest-20260516-000002/",
                        "workspace/执行日志/mobile-perf/",
                        "workspace/执行日志/logcat/",
                        "workspace/执行日志/截图/",
                    ],
                    "depends_on": ["test_execution"],
                },
            ],
            "quality_gates": {
                "p0_pass_rate": 0.95,
                "crash_rate_max": 0.001,
                "anr_rate_max": 0.0005,
                "cold_start_ms_max": 3000,
                "fps_min": 55,
                "monkey_crash": 0,
                "monkey_anr": 0,
            },
            "cross_platform": {
                "parallel_enabled": True,
                "workers": 2,
                "strategy": "loadgroup (android/ios 各自 worker)",
            },
            "cloud_device": {
                "enabled": False,
                "providers": ["Sauce Labs", "BrowserStack"],
                "fallback": "local emulator",
            },
            "mobile_specific_checks": [
                "弱网 WiFi→4G 切换 session 续期",
                "后台 5min 后 session 保活",
                "横竖屏切换 UI 不错位",
                "首次启动相机/位置权限弹窗自动允许",
                "飞行模式恢复后网络重试",
            ],
            "outputs": {
                "test_scripts_dir": "workspace/自动化脚本/python/mobile/",
                "miniprogram_dir": "workspace/自动化脚本/python/miniprogram/",
                "perf_dir": "workspace/执行日志/mobile-perf/",
                "logcat_dir": "workspace/执行日志/logcat/",
                "ios_syslog_dir": "workspace/执行日志/ios-syslog/",
                "screenshot_dir": "workspace/执行日志/截图/",
                "monkey_dir": "workspace/执行日志/monkey/",
                "allure_dir": "workspace/Allure/mobile/selftest-20260516-000002/",
            },
            "risks": [
                "设备 USB 断连致 adb/xcrun 丢失 (建议 wifi adb 备路)",
                "Appium session 超时致用例中断 (建议 per-batch restart)",
                "云真机 API 速率限制 (建议 fallback 本地模拟器)",
                "iOS 真机需开发者证书 + provisioning profile (建议 CI 预置)",
                "小程序开发者工具 CLI 版本不兼容 (建议锁定版本号)",
            ],
            "confidence": "medium",
            "_mode": "mock(stub provider)",
        }

    def output_file(self, ctx: RunnerContext) -> Path | None:
        return ctx.workspace / "执行日志" / "mobile_test_plan.json"

    def summary(self, output: dict[str, Any]) -> str:
        phases = len(output.get("phases", []))
        platform = output.get("target_platform", "?")
        batches = sum(
            len(b.get("batches", [])) if isinstance(b, dict) else 0
            for b in output.get("phases", [])
        )
        parallel = output.get("cross_platform", {}).get("parallel_enabled", False)
        cloud = output.get("cloud_device", {}).get("enabled", False)
        return (
            f"移动执行编排 {phases} 阶段 / 平台={platform} / "
            f"用例批次 {batches} / 并行={'on' if parallel else 'off'}"
            f"{' / 云真机' if cloud else ''}"
        )
