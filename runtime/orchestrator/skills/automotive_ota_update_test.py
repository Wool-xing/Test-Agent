"""automotive-ota-update-test · OTA 升级测试编排 ."""
from __future__ import annotations

from pathlib import Path

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register_skill


@register_skill("automotive-ota-update-test")
class AutomotiveOtaUpdateTest(AgentRunner):
    def system_prompt(self) -> str: return "你是 automotive-ota-update-test skill。7 项必测: 包签名 + 差分 + A/B分区 + 断电恢复 + 行车安全 + DTC + 回退。UN R156 + GB 44496-2024 合规。输出严格 JSON。"
    def user_prompt(self, ctx: RunnerContext) -> str:
        return f"## PRD\n```\n{ctx.artifact_text[:3000]}\n```\n\n## schema\n{{\n  \"project_name\":\"string\",\"run_id\":\"string\",\n  \"checks\":[\"pkg_signature\",\"delta\",\"ab_partition\",\"power_loss\",\"driving_safety\",\"dtc\",\"rollback\"],\n  \"compliance\":[\"UN_R156\",\"GB_44496_2024\"],\n  \"outputs\":{{\"ota_dir\":\"workspace/automotive/ota/\"}},\"risks\":[\"string\"],\"confidence\":\"string\"\n}}"
    def mock_output(self, ctx) -> dict: return {"project_name":"selftest","run_id":"016-000015","checks":["pkg_signature","delta","ab_partition","power_loss","driving_safety","rollback"],"compliance":["UN_R156","GB_44496_2024"],"outputs":{"ota_dir":"workspace/automotive/ota/"},"risks":["A/B分区回退失败致ECU变砖"],"confidence":"medium","_mode":"mock"}
    def output_file(self, ctx) -> Path | None: return ctx.workspace / "automotive" / "ota_plan.json"
    def summary(self, o) -> str: return f"OTA {len(o.get('checks',[]))} 项 / 合规={o.get('compliance',[])}"
