"""env-manager · LLM 读 PRD + 上游需求摘要 → 环境检查清单 + 准备步骤.

V1.15.0-alpha minimum viable (ROADMAP rollout #1 落地):
- 仅生成 env checklist + prep steps 结构化 markdown/JSON
- 不实装 04-环境管理.md 全 5 节 (Docker / 异常退避 / 清理等留 V1.x 深化)
- 输出消费者: data-preparer / automation-engineer / test-executor
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register


@register("env-manager")
class EnvManager(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 Test-Agent 项目内 env-manager 专家(02-专家定义/04-环境管理.md)。\n"
            "职责:基于 PRD 与上游需求摘要,生成测试环境检查清单 + 准备步骤。\n"
            "原则:\n"
            "1) 仅针对 test / staging 环境,prod 严禁\n"
            "2) 列出可执行的健康检查命令(curl / pg_isready / docker ps / TCP probe 等)\n"
            "3) 准备步骤按依赖顺序排序,每步给 rollback 描述\n"
            "4) 列出关键依赖(DB / 中间件 / 第三方服务)+ 风险点\n"
            "5) 不假设凭据,引用 .env / conftest.py 变量名,不写实值\n"
            "输出严格 JSON,不要 markdown 代码块包裹。"
        )

    def user_prompt(self, ctx: RunnerContext) -> str:
        req_summary = ctx.upstream.get("requirements-analyst", {})
        features = req_summary.get("features", [])
        non_functional = req_summary.get("non_functional", {})
        deps_hint = req_summary.get("business_rules", [])
        return (
            f"## 原始 PRD(截断 4000 字符)\n```\n{ctx.artifact_text[:4000]}\n```\n\n"
            f"## 上游 requirements-analyst 摘要\n"
            f"- 功能数: {len(features)} (P0={sum(1 for f in features if f.get('priority') == 'P0')})\n"
            f"- 非功能要求: {non_functional}\n"
            f"- 业务规则提示: {deps_hint[:3] if isinstance(deps_hint, list) else []}\n\n"
            "## 输出 schema\n"
            "{\n"
            '  "project_name": "string,简短项目名",\n'
            '  "target_env": "test|staging",\n'
            '  "env_checks": [\n'
            '    {"name": "string,检查项名", "command": "string,可执行 shell 命令", "expected": "string,预期结果"}\n'
            "  ],\n"
            '  "prep_steps": [\n'
            '    {"order": 1, "action": "string,准备动作描述", "rollback": "string,回滚步骤"}\n'
            "  ],\n"
            '  "dependencies": ["string,依赖服务/中间件名"],\n'
            '  "risks": ["string,环境层风险描述"],\n'
            '  "confidence": "high|medium|low"\n'
            "}"
        )

    def mock_output(self, ctx: RunnerContext) -> dict[str, Any]:  # noqa: ARG002
        return {
            "project_name": "selftest-fixture",
            "target_env": "test",
            "env_checks": [
                {
                    "name": "应用 API 可达性",
                    "command": "curl -s -o /dev/null -w \"%{http_code}\" --max-time 5 \"$TEST_API_URL/health\"",
                    "expected": "HTTP 2xx",
                },
                {
                    "name": "数据库 TCP 探活",
                    "command": "pg_isready -h \"$TEST_DB_HOST\" -p \"$TEST_DB_PORT\" -t 5",
                    "expected": "accepting connections",
                },
            ],
            "prep_steps": [
                {
                    "order": 1,
                    "action": "加载 .env 配置(TEST_API_URL / TEST_DB_HOST 等)",
                    "rollback": "无需回滚(只读)",
                },
                {
                    "order": 2,
                    "action": "执行 health_check.sh 验证 API + DB 可达",
                    "rollback": "若失败检查 .env 与目标环境真实状态",
                },
            ],
            "dependencies": ["PostgreSQL", "Redis(if 业务规则含 session 续期)"],
            "risks": [
                "test 与 staging 环境数据漂移导致用例假阳性",
                "数据库 TCP 通但应用未启动 → 健康检查需 API + DB 双探活",
            ],
            "confidence": "medium",
            "_mode": "mock(stub provider)",
        }

    def output_file(self, ctx: RunnerContext) -> Path | None:
        return ctx.workspace / "执行日志" / "env_checklist.json"

    def summary(self, output: dict[str, Any]) -> str:
        checks = len(output.get("env_checks", []))
        steps = len(output.get("prep_steps", []))
        deps = len(output.get("dependencies", []))
        risks = len(output.get("risks", []))
        return f"环境检查 {checks} 项 / 准备步骤 {steps} / 依赖 {deps} / 风险 {risks}"
