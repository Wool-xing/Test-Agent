"""test-executor · 跑测试 / 分类失败 / 标 Flaky."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register


@register("test-executor")
class TestExecutor(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 Test-Agent 项目内 test-executor 专家(02-专家定义/07-测试执行.md)。\n"
            "职责:接 automation-engineer 的脚本规划 → 输出执行计划 + 失败分类策略 + Flaky 标记规则。\n"
            "原则:\n"
            "1) 四阶段执行:冒烟(P0) → 回归(P0+P1) → 全量 → 性能\n"
            "2) 失败 4 类:product_bug / test_code_bug / env_issue / flaky\n"
            "3) Flaky 检测:连续 3 跑 2 过即标 flaky 隔离(主宪章 §21)\n"
            "4) 不真跑 sandbox,产**执行计划 JSON**(由 utils 真执行)\n"
            "输出严格 JSON,不 markdown 包裹。"
        )

    def user_prompt(self, ctx: RunnerContext) -> str:
        auto = ctx.upstream.get("automation-engineer", {})
        return (
            f"## 上游脚本规划\n{auto}\n\n"
            "## 输出 schema\n"
            "{\n"
            '  "execution_plan": [{"phase": "smoke|regression|full|perf", "scripts": ["string"], '
            '"timeout_minutes": int, "gate_pass_rate_min": float}],\n'
            '  "failure_classification_rules": {"product_bug": "string", "test_code_bug": "string", '
            '"env_issue": "string", "flaky": "string"},\n'
            '  "flaky_detection": {"window": int, "threshold": int, "action": "string"},\n'
            '  "estimated_total_minutes": int\n'
            "}"
        )

    def mock_output(self, ctx: RunnerContext) -> dict[str, Any]:
        return {
            "execution_plan": [
                {"phase": "smoke", "scripts": ["test_login_p0.py"], "timeout_minutes": 10, "gate_pass_rate_min": 0.95},
                {"phase": "regression", "scripts": ["test_login_p0.py", "test_login_api.py"], "timeout_minutes": 30, "gate_pass_rate_min": 0.90},
                {"phase": "full", "scripts": ["全部"], "timeout_minutes": 60, "gate_pass_rate_min": 0.85},
            ],
            "failure_classification_rules": {
                "product_bug": "assertion 失败 + reproducible 3/3",
                "test_code_bug": "Python AttributeError / locator NotFound / fixture setup err",
                "env_issue": "ConnectionError / Timeout / 503 / db unreachable",
                "flaky": "同脚本 3 跑通过率 < 100% 且 > 0%",
            },
            "flaky_detection": {"window": 3, "threshold": 2, "action": "隔离至 workspace/flaky_隔离/"},
            "estimated_total_minutes": 100,
            "_mode": "mock(stub provider)",
        }

    def output_file(self, ctx: RunnerContext) -> Path | None:
        return ctx.workspace / "执行日志" / "execution_plan.json"

    def summary(self, output: dict[str, Any]) -> str:
        plan = output.get("execution_plan", [])
        return f"{len(plan)} 阶段执行 · est {output.get('estimated_total_minutes', '?')} 分钟"
