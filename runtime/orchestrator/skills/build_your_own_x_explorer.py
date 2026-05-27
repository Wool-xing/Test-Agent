"""build-your-own-x-explorer skill · 教学层 byox deep-dive 推荐 (V1.32.0).

职责: 据用户当前测试场景 + 时间预算, 从 13 类 byox KB 推 deep-dive 路径。
铁律: 1) 必问时间预算 2) 不强推 3) 不复制全文。
"""

from __future__ import annotations

from pathlib import Path

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register_skill


@register_skill("build-your-own-x-explorer")
class BuildYourOwnXExplorer(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 build-your-own-x-explorer skill。职责: 按用户测试场景从 13 类 byox "
            "(database/network-stack/web-server/git/search-engine/shell/regex-engine/"
            "programming-language/web-browser/bot/...) KB 推 deep-dive 学习路径, "
            "每条带 estimated_hours + why。\n"
            "铁律: 1) 必问时间预算 (无预算→拒推) 2) 不强推 (用户测试主线优先) 3) 不复制 tutorial 全文。\n"
            "输出严格 JSON。"
        )

    def user_prompt(self, ctx: RunnerContext) -> str:
        return (
            f"## 上游/场景\n```\n{ctx.artifact_text[:3000]}\n```\n\n"
            f"## schema\n"
            "{\n"
            '  "project_name":"string","run_id":"string",\n'
            '  "user_scenario":"string","detected_concepts":["string"],\n'
            '  "time_budget_hours":null,\n'
            '  "recommendations":[{"byox_card":"byox-database","estimated_hours":30,"why":"string","priority":"P0"}],\n'
            '  "warnings":["string"],"alternative_paths":["string"],\n'
            '  "outputs":{"progress":"workspace/learning/byox_progress/{user}.json"},\n'
            '  "confidence":"low|medium|high"\n'
            "}"
        )

    def mock_output(self, ctx: RunnerContext) -> dict:
        return {
            "project_name": "selftest",
            "run_id": "selftest-byox-000001",
            "user_scenario": "SQL injection 防御边界测试",
            "detected_concepts": ["SQL parser", "sanitize", "prepared statement"],
            "time_budget_hours": None,
            "recommendations": [
                {
                    "byox_card": "byox-database",
                    "estimated_hours": 30,
                    "why": "懂 parser → 知道注入点 / 懂 query plan → 知道死锁",
                    "priority": "P0",
                },
                {
                    "byox_card": "byox-regex-engine",
                    "estimated_hours": 15,
                    "why": "懂 sanitize 边界 / ReDoS 模式",
                    "priority": "P1",
                },
            ],
            "warnings": [
                "时间投入 ≥30h, 不是必经; 测试主线优先",
                "未提供 time_budget_hours, 默认按全栈推; 建议先确认预算",
            ],
            "alternative_paths": [
                "短路径: 仅读 byox-database 的 parser 章节 (~6h)",
            ],
            "outputs": {"progress": "workspace/learning/byox_progress/{user}.json"},
            "confidence": "medium",
            "_mode": "mock",
        }

    def output_file(self, ctx: RunnerContext) -> Path:
        return ctx.workspace / "learning" / "byox_recommendation.json"

    def summary(self, output: dict) -> str:
        recs = output.get("recommendations", [])
        total_h = sum(int(r.get("estimated_hours", 0) or 0) for r in recs)
        return f"byox 推荐 {len(recs)} 条 / 预估 {total_h}h"
