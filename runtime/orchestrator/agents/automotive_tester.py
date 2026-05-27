"""automotive-tester · LLM 读 PRD + CAN-bus/ISO-26262 上下文 → ASIL 评估 + HIL 测试用例
+ ADAS 场景 + OTA 升级测试 + 协议特定配置.

V1.20.0 minimum viable (ROADMAP rollout #6 落地, V1.x rollout 收尾):
- 仅生成 ASIL 评估 + test_cases + bus_test_plan + adas_scenarios + ota_plan
  + compliance_matrix 结构化 JSON
- 不实装 16-车载测试.md 全部职责 (Vector CANoe 真跑 / HIL 台架真接 / VTD/CarMaker/CARLA
  仿真真跑 / OTA A/B 分区真切 / SocketCAN 真嗅探 等留 V1.x 深化)
- 覆盖 ECU + ADAS 域控 + IVI + V2X 4 大子系统
- 覆盖 CAN / CAN-FD / LIN / FlexRay / Automotive Ethernet / DoIP/UDS / SOME-IP / V2X
  8 协议
- 合规标准:ISO 26262 ASIL A-D + ISO 21448 SOTIF + UN R155/R156 + GB 44495/44496-2024
  + AUTOSAR + ASPICE
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register


@register("automotive-tester")
class AutomotiveTester(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 Test-Agent 项目内 automotive-tester 专家(agents/16-车载测试.md)。\n"
            "职责:基于 PRD + 车载上下文,生成 ASIL 评估 + 测试用例 + ADAS 场景 + OTA 计划 + 合规矩阵。\n"
            "原则:\n"
            "1) 识别子系统:ecu / adas / ivi / v2x / multi\n"
            "2) ASIL 等级分解 (HARA 危险分析):A/B/C/D + 对应测试深度 (ASIL C/D 必 HIL)\n"
            "3) 协议矩阵覆盖 CAN (Classical/FD) / LIN / FlexRay / Automotive Ethernet / DoIP/UDS\n"
            "   / SOME-IP / V2X (DSRC/C-V2X)\n"
            "4) HIL/SIL/MIL/PIL 环路按算法阶段选 (MIL 早期 → HIL 集成 + 故障注入)\n"
            "5) ADAS 场景库:AEB/ACC/LKA/LCC/APA/RPA/AVP/HWA/NOA + ODD 边界 + 极端场景 (夜雨雪逆光)\n"
            "6) OTA 7 步:包签名 + 差分包 + A/B 分区 + 回退 + 断电恢复 + 行车安全 + DTC 对比\n"
            "7) 合规矩阵触发:ISO 26262 / SOTIF / UN R155 R156 / GB 44495 44496-2024 / AUTOSAR / ASPICE\n"
            "输出严格 JSON,不要 markdown 代码块包裹。"
        )

    def user_prompt(self, ctx: RunnerContext) -> str:
        req_summary = ctx.upstream.get("requirements-analyst", {})
        features = req_summary.get("features", [])
        non_functional = req_summary.get("non_functional", {})
        return (
            f"## 原始 PRD(截断 4000 字符)\n```\n{ctx.artifact_text[:4000]}\n```\n\n"
            f"## 上游 requirements-analyst 摘要\n"
            f"- 功能数: {len(features)} (P0={sum(1 for f in features if f.get('priority') == 'P0')})\n"
            f"- 非功能要求: {non_functional}\n\n"
            "## 输出 schema\n"
            "{\n"
            '  "project_name": "string,简短项目名",\n'
            '  "vehicle_subsystem": "ecu|adas|ivi|v2x|multi",\n'
            '  "asil_assessment": {\n'
            '    "hara_summary": "string,危险分析摘要",\n'
            '    "asil_level": "QM|A|B|C|D",\n'
            '    "safety_goals": ["string,FuSa 安全目标"],\n'
            '    "loop_required": "MIL|SIL|PIL|HIL"\n'
            "  },\n"
            '  "test_cases": [\n'
            '    {"name": "string", "priority": "P0|P1|P2|P3", "category": "unit|integration|hil|adas|ota|protocol", "verification": "string"}\n'
            "  ],\n"
            '  "bus_test_plan": [\n'
            '    {"protocol": "can|can-fd|lin|flexray|ethernet|doip|some-ip|v2x", "tool": "string,如 Vector CANoe / SocketCAN", "test_points": ["string"]}\n'
            "  ],\n"
            '  "adas_scenarios": [\n'
            '    {"feature": "AEB|ACC|LKA|LCC|APA|RPA|AVP|HWA|NOA", "scenario": "string,如 静止前车 / 夜间逆光 / 鬼探头", "odd_boundary": "string"}\n'
            "  ],\n"
            '  "ota_plan": {\n'
            '    "package_signing": "string,签名+证书链方案",\n'
            '    "differential_pkg": "bsdiff|xdelta3|none",\n'
            '    "ab_partition_rollback": true,\n'
            '    "interruption_recovery": ["断电", "弱网", "中断"],\n'
            '    "driving_safety_check": "string,如 P 档 + 手刹 + 停车",\n'
            '    "dtc_diff_required": true\n'
            "  },\n"
            '  "compliance_matrix": [\n'
            '    {"standard": "ISO 26262|ISO 21448 SOTIF|UN R155|UN R156|GB 44495-2024|GB 44496-2024|AUTOSAR|ASPICE", "applicable": true, "evidence_required": "string"}\n'
            "  ],\n"
            '  "test_environment": {\n'
            '    "hil_bench": ["string,如 dSPACE SCALEXIO / NI VeriStand"],\n'
            '    "simulation": ["string,如 VTD / CarMaker / CARLA"],\n'
            '    "recording_format": "MDF|MF4",\n'
            '    "env_vars": ["string,如 CANOE_HOST / HIL_BENCH_IP"]\n'
            "  },\n"
            '  "risks": ["string,如 真车测试无 kill-switch / OTA 无回退 / V2X 信号丢失"],\n'
            '  "confidence": "high|medium|low"\n'
            "}"
        )

    def mock_output(self, ctx: RunnerContext) -> dict[str, Any]:  # noqa: ARG002
        return {
            "project_name": "selftest-fixture",
            "vehicle_subsystem": "adas",
            "asil_assessment": {
                "hara_summary": "AEB 失效致前车追尾 → 严重伤害,概率高,可控性低",
                "asil_level": "D",
                "safety_goals": [
                    "SG-01: AEB 触发延迟 < 200ms (ASIL D)",
                    "SG-02: 误触发率 < 1e-7/h",
                    "SG-03: 失效安全状态 = 释放制动 + 告警驾驶员",
                ],
                "loop_required": "HIL",
            },
            "test_cases": [
                {
                    "name": "AEB 静止前车触发延迟",
                    "priority": "P0",
                    "category": "hil",
                    "verification": "HIL 注入毫米波雷达回波,测 brake 信号上升时间 < 200ms",
                },
                {
                    "name": "CAN-FD 总线负载率",
                    "priority": "P0",
                    "category": "protocol",
                    "verification": "Vector CANoe 5 Mbps 总线 100% 工况负载率 < 60%",
                },
                {
                    "name": "MISRA C 合规扫描",
                    "priority": "P1",
                    "category": "unit",
                    "verification": "PC-lint / Polyspace 0 violation",
                },
                {
                    "name": "OTA 升级中断恢复",
                    "priority": "P0",
                    "category": "ota",
                    "verification": "升级 50% 时断电 → 重启自动回 A 分区 + DTC 无新增",
                },
            ],
            "bus_test_plan": [
                {
                    "protocol": "can-fd",
                    "tool": "Vector CANoe + CAPL 脚本",
                    "test_points": [
                        "DBC 帧周期偏差 < 5%",
                        "总线负载率峰值 < 60%",
                        "错误帧注入 → 节点 bus-off 恢复 < 100ms",
                    ],
                },
                {
                    "protocol": "doip",
                    "tool": "OpenDXM + Wireshark",
                    "test_points": [
                        "UDS 0x10 DiagnosticSessionControl 状态机",
                        "0x27 SecurityAccess 种子-密钥",
                        "0x34/0x36/0x37 刷写 Sequence",
                    ],
                },
                {
                    "protocol": "some-ip",
                    "tool": "vsomeip + Wireshark Lua",
                    "test_points": [
                        "Service Discovery (SD) Offer/Find 周期",
                        "Event 订阅 + Notification 推送时延",
                    ],
                },
            ],
            "adas_scenarios": [
                {
                    "feature": "AEB",
                    "scenario": "静止前车 + 60 km/h 接近 + 干燥沥青",
                    "odd_boundary": "速度 30-100 km/h, 干燥/湿润, 白天",
                },
                {
                    "feature": "AEB",
                    "scenario": "夜间逆光横穿行人",
                    "odd_boundary": "夜间 + 强逆光眩光",
                },
                {
                    "feature": "LKA",
                    "scenario": "标线模糊 + 隧道入口光线突变",
                    "odd_boundary": "标线可识别度 > 60%, 直道+缓弯",
                },
                {
                    "feature": "NOA",
                    "scenario": "高速强插车 + 鬼探头",
                    "odd_boundary": "高速封闭路段, 速度 60-120 km/h",
                },
            ],
            "ota_plan": {
                "package_signing": "RSA 4096 + X.509 证书链, OEM 根证书锚定",
                "differential_pkg": "bsdiff",
                "ab_partition_rollback": True,
                "interruption_recovery": ["断电", "弱网", "中断", "Bootloader 自检失败"],
                "driving_safety_check": "P 档 + 手刹拉起 + 整车电源 IG-ON + 车速 = 0",
                "dtc_diff_required": True,
            },
            "compliance_matrix": [
                {"standard": "ISO 26262", "applicable": True, "evidence_required": "ASIL D 测试证据链 + MC/DC 覆盖报告"},
                {"standard": "ISO 21448 SOTIF", "applicable": True, "evidence_required": "ODD 边界声明 + 极端场景库执行记录"},
                {"standard": "UN R155", "applicable": True, "evidence_required": "CSMS 网络安全管理体系审核记录"},
                {"standard": "UN R156", "applicable": True, "evidence_required": "SUMS 升级流程 + 用户通知 + 回退证据"},
                {"standard": "GB 44495-2024", "applicable": True, "evidence_required": "中国市场强制汽车信息安全送审"},
                {"standard": "GB 44496-2024", "applicable": True, "evidence_required": "中国市场强制 OTA 软件升级送审"},
                {"standard": "AUTOSAR", "applicable": True, "evidence_required": "AUTOSAR Classic/Adaptive 架构合规"},
                {"standard": "ASPICE", "applicable": True, "evidence_required": "ASPICE L3+ 流程能力评估"},
            ],
            "test_environment": {
                "hil_bench": ["dSPACE SCALEXIO + ConfigurationDesk", "NI VeriStand"],
                "simulation": ["VTD", "CarMaker", "CARLA (开源)"],
                "recording_format": "MDF",
                "env_vars": ["CANOE_HOST", "HIL_BENCH_IP", "VTD_LICENSE_SERVER"],
            },
            "risks": [
                "真车测试无 kill-switch 致失控 (建议封闭场地 + 安全员驾驶)",
                "OTA 无 A/B 回退致砖车 (建议必含 Bootloader 自检 + 回退路径)",
                "V2X 信号丢失致鬼探头误判 (建议视觉 + 雷达冗余融合)",
                "HIL 仿真模型保真度不足致漏测 (建议 SIL/HIL 双层验证 + 真车小批量)",
                "ASIL D 单元 MC/DC 覆盖不达标 (建议 PC-lint + 必须 100% MC/DC)",
            ],
            "confidence": "medium",
            "_mode": "mock(stub provider)",
        }

    def output_file(self, ctx: RunnerContext) -> Path | None:
        return ctx.workspace / "执行日志" / "automotive_test_plan.json"

    def summary(self, output: dict[str, Any]) -> str:
        cases = len(output.get("test_cases", []))
        scenarios = len(output.get("adas_scenarios", []))
        asil = output.get("asil_assessment", {}).get("asil_level", "?")
        subsystem = output.get("vehicle_subsystem", "?")
        return f"车载测试用例 {cases} 项 / ADAS 场景 {scenarios} / ASIL={asil} / 子系统={subsystem}"
