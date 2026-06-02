"""visual-test skill · LLM 读上游 visual-tester 产物 → 5 阶段视觉测试执行编排.

V1.24.0 minimum viable (ROADMAP skill rollout #3 落地):
- LLM 读 PRD + 上游 visual-tester expert 产物 → 5 阶段执行计划
  (环境检查 / 模板图准备 / 视觉冒烟 / 视觉回归 / 报告归档)
  + 质量门禁 + 多分辨率策略
- 不实装 skills/visual-test.md 全部职责 (Airtest 真跑 / OCR 引擎
  / SSIM 像素对比 / 多设备矩阵 等留后续深化)
- 输出执行计划 JSON, 真执行守护在 utils 层 (visual_helper.py)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register_skill


@register_skill("visual-test")
class VisualTest(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 Test-Agent 项目内 visual-test skill(skills/visual-test.md)。\n"
            "职责:基于 PRD + 上游 visual-tester expert 产物,编排视觉/游戏测试 5 阶段执行计划。\n"
            "原则:\n"
            "1) 识别目标类型:手游 / PC游戏 / 网页游戏 / Canvas/WebGL / 富图形界面 / 3D 工具\n"
            "2) 环境检查优先:Airtest SDK + Tesseract OCR + OpenCV + 设备连接\n"
            "3) 模板图规范:语义命名(login_btn.png),多分辨率(720p/1080p),关键 UI 元素全覆盖\n"
            "4) 视觉冒烟用 Airtest 模板匹配(threshold≥0.8) + OCR 文字校验\n"
            "5) 视觉回归用 SSIM(阈值≥0.95) + pixel-diff 高亮(threshold>200/255)\n"
            "6) 游戏专项:帧率(FPS≥30)/渲染开销/贴图完整性/场景跳转不黑屏\n"
            "7) 多分辨率策略:优先 1080p baseline,720p 降级对比允许容差±5%\n"
            "8) 不假设具体设备,引用 env 变量名(AIRTEST_DEVICE_URI / TESSERACT_CMD)\n"
            "输出严格 JSON,不要 markdown 代码块包裹。"
        )

    def user_prompt(self, ctx: RunnerContext) -> str:
        req_summary = ctx.upstream.get("requirements-analyst", {})
        visual_plan = ctx.upstream.get("visual-tester", {})
        features = req_summary.get("features", [])
        test_points = visual_plan.get("visual_test_points", [])
        target_type = visual_plan.get("visual_target_type", "game")
        comparison_scripts = visual_plan.get("comparison_scripts", [])
        tolerance = visual_plan.get("tolerance", {})
        baseline_strategy = visual_plan.get("baseline_strategy", {})
        p0_count = sum(1 for tp in test_points if tp.get("priority") == "P0")
        return (
            f"## 原始 PRD(截断 3000 字符)\n```\n{ctx.artifact_text[:3000]}\n```\n\n"
            f"## 上游 requirements-analyst 摘要\n"
            f"- 功能数: {len(features)} (P0={sum(1 for f in features if f.get('priority') == 'P0')})\n\n"
            f"## 上游 visual-tester expert 产物\n"
            f"- 目标类型: {target_type}\n"
            f"- 视觉测试点数: {len(test_points)} (P0={p0_count})\n"
            f"- 对比脚本数: {len(comparison_scripts)}\n"
            f"- 容差配置: {tolerance}\n"
            f"- Baseline 策略: {baseline_strategy}\n\n"
            "## 输出 schema\n"
            "{\n"
            '  "project_name": "string,简短项目名",\n'
            '  "run_id": "string,UUID/timestamp 任务 id",\n'
            '  "visual_target_type": "mobile_game|pc_game|web_game|canvas_webgl|rich_gui|3d_tool|video_editor|other",\n'
            '  "phases": [\n'
            '    {"phase": 1, "name": "env_check", "estimated_min": 3, "checks": ["airtest_version", "tesseract_version", "opencv_version", "device_connected"], "depends_on": []},\n'
            '    {"phase": 2, "name": "template_prep", "estimated_min": 10, "templates": [{"name": "string,如 login_btn", "resolutions": ["1080p", "720p"], "source": "workspace/自动化脚本/python/visual/images/"}], "depends_on": ["env_check"]},\n'
            '    {"phase": 3, "name": "visual_smoke", "estimated_min": 15, "cases": [{"test_point": "string", "method": "template_match|ocr|color_histogram", "threshold": 0.8, "priority": "P0|P1|P2|P3"}], "depends_on": ["template_prep"]},\n'
            '    {"phase": 4, "name": "visual_regression", "estimated_min": 20, "ssim_threshold": 0.95, "pixel_diff_threshold": 200, "baseline_dir": "workspace/自动化脚本/python/visual/baselines/", "depends_on": ["visual_smoke"]},\n'
            '    {"phase": 5, "name": "report_archive", "estimated_min": 5, "outputs": ["string,路径"], "depends_on": ["visual_regression"]}\n'
            "  ],\n"
            '  "quality_gates": {\n'
            '    "p0_pass_rate": 0.95,\n'
            '    "template_match_threshold": 0.80,\n'
            '    "ssim_min": 0.95,\n'
            '    "fps_min": 30,\n'
            '    "ocr_accuracy_min": 0.90,\n'
            '    "max_diff_regions": 5\n'
            "  },\n"
            '  "multi_resolution": {\n'
            '    "baseline": "1080p",\n'
            '    "fallback": "720p",\n'
            '    "tolerance_pct": 5\n'
            "  },\n"
            '  "game_specific": {\n'
            '    "enabled": false,\n'
            '    "checks": ["fps_stability", "render_overdraw", "texture_integrity", "scene_transition"]\n'
            "  },\n"
            '  "outputs": {\n'
            '    "template_dir": "workspace/自动化脚本/python/visual/images/",\n'
            '    "baseline_dir": "workspace/自动化脚本/python/visual/baselines/",\n'
            '    "diff_dir": "workspace/测试报告/visual-diffs/",\n'
            '    "ocr_dir": "workspace/测试报告/visual-ocr/",\n'
            '    "screenshot_dir": "workspace/测试报告/screenshots/visual/",\n'
            '    "allure_dir": "workspace/Allure/visual/{run_id}/"\n'
            "  },\n"
            '  "risks": ["string,如 设备断连 / 分辨率差异致误报 / OCR 字体缺失 / 动态内容 false positive"],\n'
            '  "confidence": "high|medium|low"\n'
            "}"
        )

    def mock_output(self, ctx: RunnerContext) -> dict[str, Any]:  # noqa: ARG002
        return {
            "project_name": "selftest-fixture",
            "run_id": "selftest-20260516-000003",
            "visual_target_type": "web_game",
            "phases": [
                {
                    "phase": 1,
                    "name": "env_check",
                    "estimated_min": 3,
                    "checks": [
                        "python -c 'import airtest; print(airtest.__version__)'",
                        "python -c 'import pytesseract; print(pytesseract.get_tesseract_version())'",
                        "python -c 'import cv2; print(cv2.__version__)'",
                        "python -c 'from airtest.core.api import connect_device; connect_device(\"Android://\")'",
                    ],
                    "depends_on": [],
                },
                {
                    "phase": 2,
                    "name": "template_prep",
                    "estimated_min": 10,
                    "templates": [
                        {"name": "main_menu", "resolutions": ["1080p", "720p"], "source": "workspace/自动化脚本/python/visual/images/"},
                        {"name": "start_btn", "resolutions": ["1080p", "720p"], "source": "workspace/自动化脚本/python/visual/images/"},
                        {"name": "settings_icon", "resolutions": ["1080p", "720p"], "source": "workspace/自动化脚本/python/visual/images/"},
                        {"name": "hud_bar", "resolutions": ["1080p"], "source": "workspace/自动化脚本/python/visual/images/"},
                    ],
                    "depends_on": ["env_check"],
                },
                {
                    "phase": 3,
                    "name": "visual_smoke",
                    "estimated_min": 15,
                    "cases": [
                        {"test_point": "主菜单加载完整", "method": "template_match", "threshold": 0.85, "priority": "P0"},
                        {"test_point": "开始按钮可见可点", "method": "template_match", "threshold": 0.80, "priority": "P0"},
                        {"test_point": "HUD 血条/分数正确显示", "method": "ocr", "threshold": 0.90, "priority": "P1"},
                        {"test_point": "设置图标颜色不偏色", "method": "color_histogram", "threshold": 0.85, "priority": "P1"},
                        {"test_point": "场景切换无黑屏", "method": "template_match", "threshold": 0.70, "priority": "P0"},
                        {"test_point": "贴图完整性(无白块/撕裂)", "method": "template_match", "threshold": 0.75, "priority": "P1"},
                    ],
                    "depends_on": ["template_prep"],
                },
                {
                    "phase": 4,
                    "name": "visual_regression",
                    "estimated_min": 20,
                    "ssim_threshold": 0.95,
                    "pixel_diff_threshold": 200,
                    "baseline_dir": "workspace/自动化脚本/python/visual/baselines/",
                    "depends_on": ["visual_smoke"],
                },
                {
                    "phase": 5,
                    "name": "report_archive",
                    "estimated_min": 5,
                    "outputs": [
                        "workspace/Allure/visual/selftest-20260516-000003/",
                        "workspace/测试报告/visual-diffs/",
                        "workspace/测试报告/screenshots/visual/",
                    ],
                    "depends_on": ["visual_regression"],
                },
            ],
            "quality_gates": {
                "p0_pass_rate": 0.95,
                "template_match_threshold": 0.80,
                "ssim_min": 0.95,
                "fps_min": 30,
                "ocr_accuracy_min": 0.90,
                "max_diff_regions": 5,
            },
            "multi_resolution": {
                "baseline": "1080p",
                "fallback": "720p",
                "tolerance_pct": 5,
            },
            "game_specific": {
                "enabled": True,
                "checks": ["fps_stability", "render_overdraw", "texture_integrity", "scene_transition"],
            },
            "outputs": {
                "template_dir": "workspace/自动化脚本/python/visual/images/",
                "baseline_dir": "workspace/自动化脚本/python/visual/baselines/",
                "diff_dir": "workspace/测试报告/visual-diffs/",
                "ocr_dir": "workspace/测试报告/visual-ocr/",
                "screenshot_dir": "workspace/测试报告/screenshots/visual/",
                "allure_dir": "workspace/Allure/visual/selftest-20260516-000003/",
            },
            "risks": [
                "设备断连致 Airtest 截图失败 (建议重试 3 次 + 5s 间隔)",
                "分辨率差异致模板匹配 false negative (建议多分辨率模板 + 容差)",
                "Tesseract 字体缺失 OCR 不准 (建议先装中文字体包 chi_sim)",
                "动态内容(动画/粒子) 致 SSIM 连续 false positive (建议 mask 动态区域)",
                "GPU 渲染差异致 pixel-diff 偏高 (建议 ±5% 容差)",
            ],
            "confidence": "medium",
            "_mode": "mock(stub provider)",
        }

    def output_file(self, ctx: RunnerContext) -> Path | None:
        return ctx.workspace / "测试报告" / "visual_test_plan.json"

    def summary(self, output: dict[str, Any]) -> str:
        phases = len(output.get("phases", []))
        target = output.get("visual_target_type", "?")
        cases = sum(
            len(p.get("cases", [])) if isinstance(p, dict) else 0
            for p in output.get("phases", [])
        )
        ssim = output.get("quality_gates", {}).get("ssim_min", "?")
        return (
            f"视觉测试编排 {phases} 阶段 / 类型={target} / "
            f"用例 {cases} / SSIM≥{ssim}"
        )
