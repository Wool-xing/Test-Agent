"""bug-manager · 分类失败 → 产 BugTracker-ready Bug 列表(主宪章 §37)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register


@register("bug-manager")
class BugManager(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 Test-Agent 项目内 bug-manager 专家(agents/08-Bug管理.md)。\n"
            "职责:把 test-executor 的失败列表转 BugTracker-ready Bug(默认 zentao,可换 Jira/GitHub Issues 等,主宪章 §37)。\n"
            "原则:\n"
            "1) severity 权威映射:1=P0(阻塞)/ 2=P1(高)/ 3=P2(中)/ 4=P3(低)\n"
            "2) STAR 格式:Situation / Task / Action / Result\n"
            "3) 提供 reproduction steps + expected vs actual + 影响范围\n"
            "4) 不真提交 BugTracker(由 utils/<tracker>_bug_manager.py 兜),产**Bug 草案 JSON**\n"
            "输出严格 JSON,不 markdown 包裹。"
        )

    def user_prompt(self, ctx: RunnerContext) -> str:
        exe = ctx.upstream.get("test-executor", {})

        # 防 mock 闭环: 真 LLM 路径也告知上游 degraded
        degraded_upstream = [
            name for name, meta in ctx.upstream_meta.items()
            if meta.get("degraded")
        ]
        degraded_warning = ""
        if degraded_upstream:
            degraded_warning = (
                f"\n## ⚠ 上游 degraded 警示\n"
                f"以下上游 expert 输出降级 (mock/fallback/未实装): {degraded_upstream}\n"
                f"请在 bugs 列表**最前面插入一条 P0 警示 bug**,"
                f"提示「测试数据不完整,不应作为发版决策」,"
                f"`labels` 含 `degraded` 与 `test-coverage-insufficient`。\n"
            )

        return (
            f"## 上游执行计划 + 失败(若有)\n{exe}\n"
            f"{degraded_warning}\n"
            "## 输出 schema\n"
            "{\n"
            '  "bugs": [{"title": "string", "severity": 1, "pri": 1, '
            '"steps": ["string"], "expected": "string", "actual": "string", '
            '"impact": "string", "labels": ["string"]}],\n'
            '  "tracker": "zentao|jira|github|gitlab|linear|webhook",\n'
            '  "submit_strategy": "string,如批量/单条",\n'
            '  "summary": {"p0": 0, "p1": 0, "p2": 0, "p3": 0}\n'
            "}"
        )

    def mock_output(self, ctx: RunnerContext) -> dict[str, Any]:
        # 防 mock 闭环: 检查上游 degraded
        degraded_upstream = [
            name for name, meta in ctx.upstream_meta.items()
            if meta.get("degraded")
        ]

        bugs = []
        # 若上游 degraded → 在 bug 列表最前插入 P0 警示 bug
        if degraded_upstream:
            bugs.append({
                "title": f"⚠ [degraded] 测试数据不完整 · {len(degraded_upstream)} 个 expert 输出降级",
                "severity": 1,  # P0 阻塞 — 不应作为发版决策依据
                "pri": 1,
                "steps": [
                    "检查上游 expert 实装状态 (ROADMAP.md V1.15-V1.20 rollout)",
                    "确认 LLM provider 不在 stub mode (settings.llm_provider)",
                    "若 expert 处于 rollout,等待对应版本完成实装",
                ],
                "expected": f"所有 {len(ctx.upstream_meta) or '上游'} expert 输出真 LLM/script 结果",
                "actual": f"degraded expert: {degraded_upstream}",
                "impact": "本次 Bug 草案基于不完整数据,不应作为发版决策依据",
                "labels": ["degraded", "test-coverage-insufficient"],
            })

        bugs.append({
            "title": "[selftest mock] 登录连续失败 5 次未触发锁定",
            "severity": 2,
            "pri": 2,
            "steps": ["输入错误密码 5 次", "观察账号状态"],
            "expected": "第 5 次返回 423 + 锁定 10 分钟",
            "actual": "未实际跑 - mock data",
            "impact": "风控规则失效,潜在暴力破解风险",
            "labels": ["security", "regression"],
        })

        # summary: degraded 警示 bug 计入 p0
        summary = {"p0": 1 if degraded_upstream else 0, "p1": 1, "p2": 0, "p3": 0}

        return {
            "bugs": bugs,
            "tracker": "zentao",
            "submit_strategy": "批量,单次 max 50",
            "summary": summary,
            "_mode": "mock(stub provider)",
            "_degraded_upstream": degraded_upstream,
        }

    def output_file(self, ctx: RunnerContext) -> Path | None:
        return ctx.workspace / "执行日志" / "bug_drafts.json"

    def summary(self, output: dict[str, Any]) -> str:
        s = output.get("summary", {})
        total = sum(s.values()) if s else len(output.get("bugs", []))
        return f"{total} Bug 草案 · P0={s.get('p0', 0)} P1={s.get('p1', 0)} → {output.get('tracker', '?')}"
