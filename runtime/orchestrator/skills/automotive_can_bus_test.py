"""automotive-can-bus-test · CAN/CAN-FD/LIN/FlexRay/SOME-IP 协议测试编排 ."""
from __future__ import annotations

from pathlib import Path

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register_skill


@register_skill("automotive-can-bus-test")
class AutomotiveCanBusTest(AgentRunner):
    def system_prompt(self) -> str: return "你是 automotive-can-bus-test skill。CAN/CAN-FD/LIN/FlexRay/SOME-IP + DoIP/UDS 诊断编排。协议一致性 + DBC解析 + 时序 + 故障注入。输出严格 JSON。"
    def user_prompt(self, ctx: RunnerContext) -> str:
        return f"## PRD\n```\n{ctx.artifact_text[:3000]}\n```\n\n## schema\n{{\n  \"project_name\":\"string\",\"run_id\":\"string\",\n  \"protocols\":[\"CAN\",\"CAN-FD\",\"LIN\",\"FlexRay\",\"SOME-IP\"],\n  \"checks\":[\"proto_conformance\",\"dbc_parse\",\"timing\",\"fault_injection\",\"uds_diag\"],\n  \"outputs\":{{\"can_dir\":\"workspace/automotive/can/\"}},\"risks\":[\"string\"],\"confidence\":\"string\"\n}}"
    def mock_output(self, ctx) -> dict: return {"project_name":"selftest","run_id":"016-000013","protocols":["CAN","CAN-FD","SOME-IP"],"checks":["proto_conformance","dbc_parse","timing","fault_injection"],"outputs":{"can_dir":"workspace/automotive/can/"},"risks":["CAN 总线物理层干扰致误判"],"confidence":"medium","_mode":"mock"}
    def output_file(self, ctx) -> Path | None: return ctx.workspace / "automotive" / "can_plan.json"
    def summary(self, o) -> str: return f"总线测试 {len(o.get('protocols',[]))} 协议"
