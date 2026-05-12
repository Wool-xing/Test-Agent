"""automation-engineer · 产 pytest UI/API 脚本骨架."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register


@register("automation-engineer")
class AutomationEngineer(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 Test-Agent 项目内 automation-engineer 专家(02-专家定义/06-自动化脚本.md)。\n"
            "职责:把 testcase-designer 给的用例转为 pytest + Playwright(UI)/ requests(API)脚本骨架。\n"
            "原则:\n"
            "1) Page Object 模式(UI)/ 数据驱动(API)\n"
            "2) fixture 复用 + parametrize 表驱动\n"
            "3) 失败截图 / 请求重放(由 utils/api_retry_util 兜)\n"
            "4) 不产可执行代码,产**骨架描述**(避免 sandbox 跑真代码风险)\n"
            "输出严格 JSON,不 markdown 包裹。"
        )

    def user_prompt(self, ctx: RunnerContext) -> str:
        req = ctx.upstream.get("requirements-analyst", {})
        return (
            f"## 上游需求摘要\n{req}\n\n"
            "## 输出 schema\n"
            "{\n"
            '  "scripts": [{"name": "test_login_p0.py", "type": "UI|API", "page_object": "string", '
            '"test_count": int, "fixtures": ["string"], "parametrize_table": "string"}],\n'
            '  "fixtures_shared": ["string"],\n'
            '  "estimated_effort_hours": int,\n'
            '  "skip_reasons": ["string"]\n'
            "}"
        )

    def mock_output(self, ctx: RunnerContext) -> dict[str, Any]:
        return {
            "scripts": [
                {
                    "name": "test_login_p0.py",
                    "type": "UI",
                    "page_object": "LoginPage(url_input, pwd_input, submit_btn)",
                    "test_count": 5,
                    "fixtures": ["browser", "test_user", "session"],
                    "parametrize_table": "[(valid_user, ok), (wrong_pwd, fail), (empty, validation_err)]",
                },
                {
                    "name": "test_login_api.py",
                    "type": "API",
                    "page_object": "(N/A)",
                    "test_count": 3,
                    "fixtures": ["api_client", "test_user"],
                    "parametrize_table": "[(valid, 200), (locked, 423), (expired_otp, 400)]",
                },
            ],
            "fixtures_shared": ["browser", "api_client", "test_user", "session"],
            "estimated_effort_hours": 4,
            "skip_reasons": [],
            "_mode": "mock(stub provider)",
        }

    def output_file(self, ctx: RunnerContext) -> Path | None:
        return ctx.workspace / "执行日志" / "automation_scripts_plan.json"

    def summary(self, output: dict[str, Any]) -> str:
        scripts = output.get("scripts", [])
        cnt = sum(s.get("test_count", 0) for s in scripts)
        return f"规划 {len(scripts)} 文件 · {cnt} 用例 · est {output.get('estimated_effort_hours', '?')}h"
