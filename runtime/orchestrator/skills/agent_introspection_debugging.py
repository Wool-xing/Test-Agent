"""agent-introspection-debugging skill · 五维自省分析 (V1.x).

职责: 对 agent 行为做五维自省 (决策回放/工具调用/token/上下文/状态机) → 结构化报告。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register_skill


@register_skill("agent-introspection-debugging")
class AgentIntrospectionDebugging(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 agent-introspection-debugging skill,负责对 agent 行为做五维自省分析: "
            "决策回放 / 工具调用 / token 消耗 / 上下文管理 / 状态机。"
            "输出严格 JSON,字段: project_name, run_id, target_run_id, "
            "dimensions{decision_replay[], tool_calls[], token_consumption{}, context{}, state_machine{}}, "
            "findings[{severity,category,description}], recommendations[], outputs{}, confidence。"
        )

    def user_prompt(self, ctx: RunnerContext) -> str:
        upstream_brief = "; ".join(
            f"{name}:{str(out)[:60]}" for name, out in list(ctx.upstream.items())[:8]
        ) or "(无上游产物)"
        return (
            f"## 被分析 run / 异常描述\n```\n{ctx.artifact_text[:2000]}\n```\n\n"
            f"## 上游产物摘要\n{upstream_brief}\n\n"
            "请输出五维自省 JSON,标注卡住状态、异常 token 消耗、失败工具调用,"
            "并给出 3-6 条 recommendations。confidence 取 low|medium|high。"
        )

    def mock_output(self, ctx: RunnerContext) -> dict[str, Any]:  # noqa: ARG002
        return {
            "project_name": "selftest",
            "run_id": "selftest-introspect-000001",
            "target_run_id": "selftest-target-000001",
            "dimensions": {
                "decision_replay": [
                    {"decision_id": "d1", "input_snapshot": "prd_v1", "output": "approved", "judgment": "consistent"}
                ],
                "tool_calls": [{"tool": "search", "span_id": "s1", "duration_ms": 120, "status": "ok"}],
                "token_consumption": {"total_in": 0, "total_out": 0, "per_call_max": 0, "anomalies": []},
                "context": {"prompt_length_max": 0, "truncation_points": [], "session_isolation_ok": True},
                "state_machine": {
                    "flow_run_id": "selftest-target-000001",
                    "transitions": ["start", "prd", "done"],
                    "stuck_at": None,
                },
            },
            "findings": [{"severity": "info", "category": "baseline", "description": "mock baseline self-check"}],
            "recommendations": ["配置 LLM_PROVIDER 以启用真实自省分析"],
            "outputs": {"report": "workspace/自省/agent_report.json"},
            "confidence": "low",
            "_mode": "mock",
        }

    def output_file(self, ctx: RunnerContext) -> Path:
        return ctx.workspace / "自省" / "agent_introspection.json"

    def summary(self, output: dict[str, Any]) -> str:
        return f"自省 {len(output.get('findings', []))} 发现 / {len(output.get('recommendations', []))} 建议"
