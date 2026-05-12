"""test-lead · 看全链路上游产物 → 出最终上线决策."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register


@register("test-lead")
class TestLead(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 Test-Agent 项目内 test-lead 专家(02-专家定义/01-测试主管.md)。\n"
            "职责:看上游所有专家产物 → 出**上线决策**(go / no-go / conditional)。\n"
            "原则:\n"
            "1) 看 requirements / scripts / execution_plan / bug_drafts 完整链路\n"
            "2) 决策标准:P0 Bug=0 + 回归通过率 ≥ 90% + 性能门禁过 = go;否则 conditional / no-go\n"
            "3) 业务语言(主宪章 §10 五铭文 #5):管理层 / 开发都能秒懂\n"
            "4) 标 skin-in-the-game:本决策**人类签字**,Agent 仅给建议(主宪章 §10 第 5 铭文)\n"
            "5) 列出已知遗留 + 兜底方案\n"
            "输出严格 JSON,不 markdown 包裹。"
        )

    def user_prompt(self, ctx: RunnerContext) -> str:
        return (
            f"## 上游全链路产物\n"
            f"- requirements-analyst: {ctx.upstream.get('requirements-analyst', {})}\n\n"
            f"- automation-engineer: {ctx.upstream.get('automation-engineer', {})}\n\n"
            f"- test-executor: {ctx.upstream.get('test-executor', {})}\n\n"
            f"- bug-manager: {ctx.upstream.get('bug-manager', {})}\n\n"
            "## 输出 schema\n"
            "{\n"
            '  "verdict": "go|no-go|conditional",\n'
            '  "summary_zh": "string,1 句话给管理层",\n'
            '  "rationale": "string,3-5 句解释",\n'
            '  "metrics": {"smoke_pass_rate": float, "regression_pass_rate": float, "p0_bug_count": int},\n'
            '  "known_risks": ["string"],\n'
            '  "fallback_plan": "string",\n'
            '  "requires_human_signoff": true,\n'
            '  "signoff_owner": "test-lead 负责人姓名(占位)"\n'
            "}"
        )

    def mock_output(self, ctx: RunnerContext) -> dict[str, Any]:
        bug = ctx.upstream.get("bug-manager", {}).get("summary", {})
        p0 = bug.get("p0", 0) if isinstance(bug, dict) else 0
        verdict = "go" if p0 == 0 else "no-go"
        return {
            "verdict": verdict,
            "summary_zh": f"selftest mock 验证 · {verdict.upper()}",
            "rationale": (
                "本次为 selftest fixture mock 运行 · 主流程编排链路全通 · "
                f"P0 Bug={p0},自动判 {verdict} · 真生产环境请填真 PRD + 真 LLM 再判。"
            ),
            "metrics": {"smoke_pass_rate": 1.0, "regression_pass_rate": 1.0, "p0_bug_count": p0},
            "known_risks": ["此为 stub LLM 输出,非真测试数据"],
            "fallback_plan": "若真生产环境出 no-go,回滚到上版本 + bug-manager 提单",
            "requires_human_signoff": True,
            "signoff_owner": "<填测试主管姓名>",
            "_mode": "mock(stub provider)",
        }

    def output_file(self, ctx: RunnerContext) -> Path | None:
        return ctx.workspace / "执行日志" / "decisions" / f"final_verdict_{int(ctx.workspace.stat().st_mtime if ctx.workspace.exists() else 0)}.json"

    def summary(self, output: dict[str, Any]) -> str:
        return f"决策:{output.get('verdict', '?').upper()} · {output.get('summary_zh', '')[:60]}"
