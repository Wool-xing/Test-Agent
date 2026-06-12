"""visual-tester · LLM 读 PRD + UI 描述 → 视觉测试点 + 视觉对比脚本片段.

minimum viable (ROADMAP rollout #3 落地):
- 仅生成 visual test points + comparison scripts + tolerance + baseline_strategy 结构化 JSON
- 不实装 12-视觉游戏测试.md 全部职责 (Airtest 真跑 / OCR 调用 / SSIM 像素对比执行
  等留 深化)
- 覆盖 Web Canvas/WebGL + 手游/PC 游戏 + OCR + 视觉回归
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register


@register("visual-tester")
class VisualTester(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 Test-Agent 项目内 visual-tester 专家(agents/12-视觉游戏测试.md)。\n"
            "职责:基于 PRD + UI 描述,生成视觉测试点 + 视觉对比脚本片段 + 容差配置。\n"
            "原则:\n"
            "1) 识别视觉目标类型:web-canvas / webgl / unity / unreal / mobile-game / ocr / visual-regression\n"
            "2) 测试点针对无 DOM/可访问性树场景 (Canvas / WebGL / 游戏 UI / PDF 图片)\n"
            "3) 视觉对比脚本优先 Airtest (跨平台) / Playwright screenshot + SSIM\n"
            "4) 容差配置区分像素差 (PSNR > 30dB) vs SSIM (> 0.95) vs 模板匹配 (> 0.85)\n"
            "5) 基线管理:主分支生成 baseline + PR 跑对比 + 真改动 update baseline\n"
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
            '  "visual_target_type": "web-canvas|webgl|unity|unreal|mobile-game|ocr|visual-regression|multi",\n'
            '  "visual_test_points": [\n'
            '    {"name": "string", "priority": "P0|P1|P2|P3", "target_element": "string,视觉元素描述", "verification": "string,验证点"}\n'
            "  ],\n"
            '  "comparison_scripts": [\n'
            '    {"framework": "airtest|playwright|opencv|paddleocr", "snippet": "string,可执行脚本片段", "purpose": "string"}\n'
            "  ],\n"
            '  "tolerance": {\n'
            '    "pixel_diff_psnr_min_db": 30,\n'
            '    "ssim_min": 0.95,\n'
            '    "template_match_min": 0.85\n'
            "  },\n"
            '  "baseline_strategy": {\n'
            '    "storage": "string,如 workspace/视觉基线/<feature_name>/<version>.png",\n'
            '    "trigger": "string,如 main 分支自动生成 / PR 跑对比 / 真改动手动 update",\n'
            '    "rollback": "string,基线错时回滚步骤"\n'
            "  },\n"
            '  "risks": ["string,视觉测试风险,如分辨率差异/动画时序/字体渲染差"],\n'
            '  "confidence": "high|medium|low"\n'
            "}"
        )

    def mock_output(self, ctx: RunnerContext) -> dict[str, Any]:  # noqa: ARG002
        return {
            "project_name": "selftest-fixture",
            "visual_target_type": "visual-regression",
            "visual_test_points": [
                {
                    "name": "登录页主视觉元素位置",
                    "priority": "P0",
                    "target_element": "Logo + 输入框 + 登录按钮 layout",
                    "verification": "截图与 baseline 像素差 PSNR > 30dB",
                },
                {
                    "name": "Canvas 图表渲染正确性",
                    "priority": "P1",
                    "target_element": "首页折线图 Canvas (无 DOM)",
                    "verification": "SSIM 与 baseline > 0.95 (允许抗锯齿差)",
                },
            ],
            "comparison_scripts": [
                {
                    "framework": "playwright",
                    "snippet": "await page.screenshot({path: 'current.png'}); await expect(page).toHaveScreenshot('baseline.png', {maxDiffPixels: 100});",
                    "purpose": "Web UI 视觉回归",
                },
                {
                    "framework": "airtest",
                    "snippet": "from airtest.core.api import *; touch(Template(r\"login_btn.png\", record_pos=(0.1, 0.2)))",
                    "purpose": "Canvas / 游戏 UI 元素定位 + 操作",
                },
            ],
            "tolerance": {
                "pixel_diff_psnr_min_db": 30,
                "ssim_min": 0.95,
                "template_match_min": 0.85,
            },
            "baseline_strategy": {
                "storage": "workspace/视觉基线/<feature_name>/<version>.png",
                "trigger": "main 分支自动生成 baseline + PR 跑对比 + 真改动手动 update",
                "rollback": "git revert baseline commit + CI 重生成",
            },
            "risks": [
                "分辨率差异致 baseline 不通用 (CI vs 本地 vs 真机)",
                "字体渲染差异跨 OS (Linux vs macOS vs Windows)",
                "动画时序导致截图不稳定 (需 waitForAnimationsToFinish)",
            ],
            "confidence": "medium",
            "_mode": "mock(stub provider)",
        }

    def output_file(self, ctx: RunnerContext) -> Path | None:
        return ctx.workspace / "测试报告" / "visual_test_plan.json"

    def summary(self, output: dict[str, Any]) -> str:
        points = len(output.get("visual_test_points", []))
        scripts = len(output.get("comparison_scripts", []))
        target = output.get("visual_target_type", "?")
        return f"视觉测试点 {points} 项 / 对比脚本 {scripts} / 目标类型={target}"
