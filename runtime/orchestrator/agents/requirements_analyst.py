"""requirements-analyst · 把多格式 PRD 解析为结构化测试需求."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register


@register("requirements-analyst")
class RequirementsAnalyst(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 Test-Agent 项目内 requirements-analyst 专家(agents/02-需求分析.md)。\n"
            "职责:把任意格式 PRD(md/pdf/docx/url/口头)解析为结构化测试需求摘要。\n"
            "原则:\n"
            "1) 识别核心功能 + 边界场景 + 高风险区\n"
            "2) 标优先级:P0(核心流程)/P1(主要功能)/P2(次要)/P3(边角)\n"
            "3) 列出业务规则 + 数据约束 + 集成依赖\n"
            "4) 识别非功能要求(性能/安全/合规)\n"
            "输出严格 JSON,不要 markdown 代码块包裹。"
        )

    def user_prompt(self, ctx: RunnerContext) -> str:
        return (
            f"## 原始 PRD(截断 8000 字符)\n```\n{ctx.artifact_text[:8000]}\n```\n\n"
            "## 输出 schema\n"
            "{\n"
            '  "project_name": "string,简短项目名",\n'
            '  "features": [{"name": "string", "priority": "P0|P1|P2|P3", "description": "string"}],\n'
            '  "business_rules": ["string"],\n'
            '  "risk_areas": ["string,高风险区描述"],\n'
            '  "non_functional": {"performance": "string", "security": "string", "compliance": "string"},\n'
            '  "out_of_scope": ["string"],\n'
            '  "confidence": "high|medium|low"\n'
            "}"
        )

    def mock_output(self, ctx: RunnerContext) -> dict[str, Any]:
        text = ctx.artifact_text[:500] or "(无 PRD)"
        return {
            "project_name": "selftest-fixture",
            "features": [
                {"name": "登录主流程", "priority": "P0", "description": "账密 + 验证码 + Cookie"},
                {"name": "短信验证码", "priority": "P1", "description": "60s 过期 + 5 次锁定"},
            ],
            "business_rules": ["错误 5 次锁定 10 分钟", "session 24h 过期"],
            "risk_areas": ["登录失败风控规则", "session 续期边界"],
            "non_functional": {"performance": "P99 < 300ms", "security": "HTTPS + 加密传输", "compliance": "PIPL"},
            "out_of_scope": ["注册", "找回密码"],
            "confidence": "medium",
            "_source_excerpt": text[:200],
            "_mode": "mock(stub provider)",
        }

    def output_file(self, ctx: RunnerContext) -> Path | None:
        return ctx.workspace / "执行日志" / "requirements_summary.json"

    def summary(self, output: dict[str, Any]) -> str:
        feats = output.get("features", [])
        p0 = sum(1 for f in feats if f.get("priority") == "P0")
        return f"识别 {len(feats)} 功能点(P0={p0}),风险区 {len(output.get('risk_areas', []))}"
