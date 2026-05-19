"""test-lead · 看全链路上游产物 → 出最终上线决策."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register


@register("test-lead")
class TestLead(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 Test-Agent 项目内 test-lead 专家(agents/01-测试主管.md)。\n"
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
        # 防 mock 闭环 (W3-3): 真 LLM 路径也告知上游 degraded
        # 让 LLM 看到 degraded 信号后强制 verdict 降级 conditional/no-go,不能输出 go
        degraded_upstream = [
            name for name, meta in ctx.upstream_meta.items()
            if meta.get("degraded")
        ]
        degraded_block = ""
        if degraded_upstream:
            degraded_block = (
                f"\n## ⚠ 上游 degraded 警示 (强制约束)\n"
                f"以下上游 expert 输出降级 (mock 兜底 / LLM 失败 fallback / 未实装 V1.x rollout):\n"
                f"{degraded_upstream}\n\n"
                f"**强制要求**:\n"
                f"1. `verdict` **绝不能输出 'go'** — 因为本次测试数据不完整\n"
                f"2. `verdict` 应输出 `conditional`(部分数据可信) 或 `no-go`(P0 缺失维度过多)\n"
                f"3. `known_risks` **必须列出每个 degraded expert 名**及对应未覆盖维度\n"
                f"4. `rationale` 必须包含「测试数据不完整,基于 {len(degraded_upstream)} 个降级 expert 无法做发版决策」\n"
                f"5. `fallback_plan` 必须包含「等 V1.x rollout 完成后重跑」\n"
            )

        return (
            f"## 上游全链路产物\n"
            f"- requirements-analyst: {ctx.upstream.get('requirements-analyst', {})}\n\n"
            f"- automation-engineer: {ctx.upstream.get('automation-engineer', {})}\n\n"
            f"- test-executor: {ctx.upstream.get('test-executor', {})}\n\n"
            f"- bug-manager: {ctx.upstream.get('bug-manager', {})}\n\n"
            f"{degraded_block}\n"
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

        # V1.14 防 mock 闭环: 检查上游是否有 degraded 信号
        # (mock 兜底 / LLM 失败 fallback / JSON 解析错 / rollout expert 被路由)
        degraded_upstream = [
            name for name, meta in ctx.upstream_meta.items()
            if meta.get("degraded")
        ]
        upstream_errors = [
            f"{name}: {meta.get('error', '')}"
            for name, meta in ctx.upstream_meta.items()
            if not meta.get("ok") and meta.get("error")
        ]

        if degraded_upstream:
            # 任一上游 degraded → 决策不能输出 go,强制降级 conditional
            verdict = "conditional"
            summary_zh = (
                f"⚠ {len(degraded_upstream)} 个上游 expert 输出 degraded · {verdict.upper()}"
            )
            rationale = (
                f"防 mock 闭环触发: 上游 expert {degraded_upstream} 输出 degraded "
                f"(mock 兜底 / LLM 失败 / 未实装 V1.x rollout)。"
                f"不能基于不完整数据输出 GO,降级 conditional 等人审。"
            )
            known_risks = [
                f"上游 expert '{name}' 输出 degraded — 真测覆盖度不足"
                for name in degraded_upstream
            ] + upstream_errors
        elif p0 > 0:
            verdict = "no-go"
            summary_zh = f"selftest mock 验证 · P0 Bug={p0} · NO-GO"
            rationale = (
                f"本次为 selftest fixture mock 运行 · 主流程编排链路全通 · "
                f"P0 Bug={p0},自动判 no-go · 真生产环境请填真 PRD + 真 LLM 再判。"
            )
            known_risks = ["此为 stub LLM 输出,非真测试数据"]
        else:
            verdict = "go"
            summary_zh = f"selftest mock 验证 · GO"
            rationale = (
                "本次为 selftest fixture mock 运行 · 主流程编排链路全通 · "
                "P0 Bug=0,自动判 go · 真生产环境请填真 PRD + 真 LLM 再判。"
            )
            known_risks = ["此为 stub LLM 输出,非真测试数据"]

        return {
            "verdict": verdict,
            "summary_zh": summary_zh,
            "rationale": rationale,
            "metrics": {"smoke_pass_rate": 1.0, "regression_pass_rate": 1.0, "p0_bug_count": p0},
            "known_risks": known_risks,
            "fallback_plan": "若真生产环境出 no-go,回滚到上版本 + bug-manager 提单",
            "requires_human_signoff": True,
            "signoff_owner": "<填测试主管姓名>",
            "_mode": "mock(stub provider)",
            "_degraded_upstream": degraded_upstream,
        }

    def output_file(self, ctx: RunnerContext) -> Path | None:
        return ctx.workspace / "执行日志" / "decisions" / f"final_verdict_{int(ctx.workspace.stat().st_mtime if ctx.workspace.exists() else 0)}.json"

    def summary(self, output: dict[str, Any]) -> str:
        return f"决策:{output.get('verdict', '?').upper()} · {output.get('summary_zh', '')[:60]}"
