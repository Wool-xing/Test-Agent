"""system-test skill · LLM 读上游 system-tester 产物 → 6 阶段系统集成测试编排.

V1.26.0 minimum viable (ROADMAP skill rollout #4 落地):
- LLM 读 PRD + 上游 system-tester expert 产物 → 6 阶段执行计划
  (环境检查 / IoT 测试 / 音视频校验 / 链路追踪 / 消息队列 / 报告归档)
  + 质量门禁 + 子场景路由策略
- 不实装 skills/system-test.md 全部职责 (SSH 真跑 / 串口读写
  / FFmpeg 解码 / Jaeger 查询 / Kafka consumer 等留后续深化)
- 输出执行计划 JSON, 真执行守护在 utils 层 (iot_helper / media_validator
  / tracing_validator / mq_helper)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register_skill


@register_skill("system-test")
class SystemTest(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 Test-Agent 项目内 system-test skill(skills/system-test.md)。\n"
            "职责:基于 PRD + 上游 system-tester expert 产物,编排系统集成测试 6 阶段执行计划。\n"
            "原则:\n"
            "1) 识别子场景:iot / audiovideo / tracing / mq / multi (可复合)\n"
            "2) IoT 覆盖 SSH 命令执行 + 串口通信 + MQTT 消息收发 + Modbus 寄存器读写\n"
            "3) 音视频用 FFprobe 元信息提取 + FFmpeg 解码 + 抽帧 SSIM + 音画同步偏移\n"
            "4) 链路追踪用 Jaeger HTTP API 查 trace + 完整性断言 (span 缺口 / 延迟)\n"
            "5) 消息队列覆盖 Kafka produce/consume + RabbitMQ publish/subscribe + 延迟 + 重连\n"
            "6) 跨服务端到端 A→B→C 业务流 + traceID 串联校验\n"
            "7) 环境检查优先: SSH/串口/MQTT broker/FFmpeg/Jaeger/Kafka/RabbitMQ 连通性\n"
            "8) 不假设具体设备 IP/凭证,引用 env 变量名(IOT_SSH_HOST / KAFKA_BROKERS 等)\n"
            "输出严格 JSON,不要 markdown 代码块包裹。"
        )

    def user_prompt(self, ctx: RunnerContext) -> str:
        req_summary = ctx.upstream.get("requirements-analyst", {})
        sys_plan = ctx.upstream.get("system-tester", {})
        features = req_summary.get("features", [])
        test_cases = sys_plan.get("test_cases", [])
        device_commands = sys_plan.get("device_commands", [])
        sub_scenarios = sys_plan.get("sub_scenarios", [])
        p0_count = sum(1 for tc in test_cases if tc.get("priority") == "P0")
        return (
            f"## 原始 PRD(截断 3000 字符)\n```\n{ctx.artifact_text[:3000]}\n```\n\n"
            f"## 上游 requirements-analyst 摘要\n"
            f"- 功能数: {len(features)} (P0={sum(1 for f in features if f.get('priority') == 'P0')})\n\n"
            f"## 上游 system-tester expert 产物\n"
            f"- 子场景: {sub_scenarios or '(未指定, 推断)'}\n"
            f"- 测试用例数: {len(test_cases)} (P0={p0_count})\n"
            f"- 设备命令数: {len(device_commands)}\n\n"
            "## 输出 schema\n"
            "{\n"
            '  "project_name": "string,简短项目名",\n'
            '  "run_id": "string,UUID/timestamp 任务 id",\n'
            '  "sub_scenarios": ["iot", "audiovideo", "tracing", "mq"],\n'
            '  "phases": [\n'
            '    {"phase": 1, "name": "env_check", "estimated_min": 5, "checks": [{"component": "ssh|serial|mqtt|ffmpeg|jaeger|kafka|rabbitmq", "command": "string"}], "depends_on": []},\n'
            '    {"phase": 2, "name": "iot_test", "estimated_min": 20, "optional": true, "cases": [{"device": "string", "priority": "P0|P1|P2|P3", "method": "ssh_command|serial_read|mqtt_pubsub|modbus_read", "assertion": "string"}], "depends_on": ["env_check"]},\n'
            '    {"phase": 3, "name": "media_validation", "estimated_min": 15, "optional": true, "cases": [{"file": "string", "priority": "P0|P1", "method": "ffprobe_meta|ssim_compare|av_sync|psnr_check", "threshold": {}}], "depends_on": ["env_check"]},\n'
            '    {"phase": 4, "name": "tracing_validation", "estimated_min": 10, "optional": true, "cases": [{"trace_id": "string", "priority": "P0|P1", "check": "span_completeness|latency|cross_service|error_span"}], "depends_on": ["env_check"]},\n'
            '    {"phase": 5, "name": "mq_validation", "estimated_min": 15, "optional": true, "cases": [{"broker": "kafka|rabbitmq", "topic": "string", "priority": "P0|P1", "method": "produce_consume|pub_sub|dlq_check|reconnect"}], "depends_on": ["env_check"]},\n'
            '    {"phase": 6, "name": "report_archive", "estimated_min": 5, "outputs": ["string,路径"], "depends_on": ["iot_test", "media_validation", "tracing_validation", "mq_validation"]}\n'
            "  ],\n"
            '  "quality_gates": {\n'
            '    "p0_pass_rate": 0.95,\n'
            '    "ssh_timeout_sec": 10,\n'
            '    "serial_baud_match": true,\n'
            '    "mqtt_qos": 1,\n'
            '    "media_psnr_min_db": 30,\n'
            '    "media_ssim_min": 0.95,\n'
            '    "trace_span_gap_max": 0,\n'
            '    "trace_latency_ms_max": 5000,\n'
            '    "mq_message_loss": 0,\n'
            '    "mq_reconnect_success": true\n'
            "  },\n"
            '  "sub_scenario_routing": {\n'
            '    "iot": {"utils": ["iot_helper"], "optional": false},\n'
            '    "audiovideo": {"utils": ["media_validator"], "optional": false},\n'
            '    "tracing": {"utils": ["tracing_validator"], "optional": false},\n'
            '    "mq": {"utils": ["mq_helper"], "optional": false}\n'
            "  },\n"
            '  "outputs": {\n'
            '    "iot_dir": "workspace/测试报告/iot-logs/",\n'
            '    "media_dir": "workspace/测试报告/media-logs/",\n'
            '    "trace_dir": "workspace/测试报告/trace-logs/",\n'
            '    "mq_dir": "workspace/测试报告/mq-logs/",\n'
            '    "allure_dir": "workspace/Allure/system/{run_id}/"\n'
            "  },\n"
            '  "risks": ["string,如 SSH 超时 / 串口断连 / MQTT broker 离线 / Kafka offset 丢失"],\n'
            '  "confidence": "high|medium|low"\n'
            "}"
        )

    def mock_output(self, ctx: RunnerContext) -> dict[str, Any]:  # noqa: ARG002
        return {
            "project_name": "selftest-fixture",
            "run_id": "selftest-20260516-000004",
            "sub_scenarios": ["iot", "audiovideo", "tracing", "mq"],
            "phases": [
                {
                    "phase": 1,
                    "name": "env_check",
                    "estimated_min": 5,
                    "checks": [
                        {"component": "ssh", "command": "ssh -V"},
                        {"component": "serial", "command": "python -c 'import serial; print(serial.__version__)'"},
                        {"component": "mqtt", "command": "python -c 'import paho.mqtt.client; print(\"mqtt ok\")'"},
                        {"component": "ffmpeg", "command": "ffmpeg -version"},
                        {"component": "ffprobe", "command": "ffprobe -version"},
                        {"component": "jaeger", "command": "curl ${JAEGER_BASE_URL}/api/services"},
                        {"component": "kafka", "command": "python -c 'from kafka import KafkaConsumer; print(\"kafka ok\")'"},
                        {"component": "rabbitmq", "command": "python -c 'import pika; print(\"rabbitmq ok\")'"},
                    ],
                    "depends_on": [],
                },
                {
                    "phase": 2,
                    "name": "iot_test",
                    "estimated_min": 20,
                    "optional": True,
                    "cases": [
                        {"device": "edge-gateway-01", "priority": "P0", "method": "ssh_command", "assertion": "uname -a 返含 Linux"},
                        {"device": "sensor-temp-01", "priority": "P0", "method": "serial_read", "assertion": "9600 8N1 读 temperature 字段非空"},
                        {"device": "mqtt-broker", "priority": "P1", "method": "mqtt_pubsub", "assertion": "publish \"test/hello\" → subscribe 收到相同 payload"},
                        {"device": "plc-01", "priority": "P1", "method": "modbus_read", "assertion": "holding register 40001 值在 [0, 100] 范围"},
                    ],
                    "depends_on": ["env_check"],
                },
                {
                    "phase": 3,
                    "name": "media_validation",
                    "estimated_min": 15,
                    "optional": True,
                    "cases": [
                        {"file": "sample_1080p.mp4", "priority": "P0", "method": "ffprobe_meta", "threshold": {"width": 1920, "height": 1080, "codec": "h264"}},
                        {"file": "sample_1080p.mp4", "priority": "P1", "method": "ssim_compare", "threshold": {"ssim_min": 0.95}},
                        {"file": "sample_1080p.mp4", "priority": "P1", "method": "av_sync", "threshold": {"offset_ms_max": 100}},
                    ],
                    "depends_on": ["env_check"],
                },
                {
                    "phase": 4,
                    "name": "tracing_validation",
                    "estimated_min": 10,
                    "optional": True,
                    "cases": [
                        {"trace_id": "<from-service-A>", "priority": "P0", "check": "span_completeness"},
                        {"trace_id": "<from-service-A>", "priority": "P0", "check": "latency"},
                        {"trace_id": "<from-service-A>", "priority": "P1", "check": "cross_service"},
                    ],
                    "depends_on": ["env_check"],
                },
                {
                    "phase": 5,
                    "name": "mq_validation",
                    "estimated_min": 15,
                    "optional": True,
                    "cases": [
                        {"broker": "kafka", "topic": "orders", "priority": "P0", "method": "produce_consume"},
                        {"broker": "rabbitmq", "topic": "events.user", "priority": "P1", "method": "pub_sub"},
                        {"broker": "kafka", "topic": "orders", "priority": "P1", "method": "reconnect"},
                    ],
                    "depends_on": ["env_check"],
                },
                {
                    "phase": 6,
                    "name": "report_archive",
                    "estimated_min": 5,
                    "outputs": [
                        "workspace/Allure/system/selftest-20260516-000004/",
                        "workspace/测试报告/iot-logs/",
                        "workspace/测试报告/media-logs/",
                        "workspace/测试报告/trace-logs/",
                        "workspace/测试报告/mq-logs/",
                    ],
                    "depends_on": ["iot_test", "media_validation", "tracing_validation", "mq_validation"],
                },
            ],
            "quality_gates": {
                "p0_pass_rate": 0.95,
                "ssh_timeout_sec": 10,
                "serial_baud_match": True,
                "mqtt_qos": 1,
                "media_psnr_min_db": 30,
                "media_ssim_min": 0.95,
                "trace_span_gap_max": 0,
                "trace_latency_ms_max": 5000,
                "mq_message_loss": 0,
                "mq_reconnect_success": True,
            },
            "sub_scenario_routing": {
                "iot": {"utils": ["iot_helper"], "optional": False},
                "audiovideo": {"utils": ["media_validator"], "optional": False},
                "tracing": {"utils": ["tracing_validator"], "optional": False},
                "mq": {"utils": ["mq_helper"], "optional": False},
            },
            "outputs": {
                "iot_dir": "workspace/测试报告/iot-logs/",
                "media_dir": "workspace/测试报告/media-logs/",
                "trace_dir": "workspace/测试报告/trace-logs/",
                "mq_dir": "workspace/测试报告/mq-logs/",
                "allure_dir": "workspace/Allure/system/selftest-20260516-000004/",
            },
            "risks": [
                "SSH 超时 10s 致设备命令失败 (建议重试 3 次 + 指数退避)",
                "串口断连致传感器读取缺失 (建议 DTR/RTS 握手 + 超时重连)",
                "MQTT broker 离线致 pub/sub 中断 (建议 broker 集群 + 本地 mosquitto 兜底)",
                "Kafka offset 丢失致消息漏检 (建议 consumer group 独立 + auto.offset.reset=earliest)",
                "FFprobe 解码失败格式不支持 (建议先转码为 h264/aac 再检)",
                "Jaeger API 限速致 trace 查询截断 (建议 batch 查询 + 缓存 span 索引)",
            ],
            "confidence": "medium",
            "_mode": "mock(stub provider)",
        }

    def output_file(self, ctx: RunnerContext) -> Path | None:
        return ctx.workspace / "测试报告" / "system_test_plan.json"

    def summary(self, output: dict[str, Any]) -> str:
        phases = len(output.get("phases", []))
        subs = output.get("sub_scenarios", [])
        cases = sum(
            len(p.get("cases", [])) if isinstance(p, dict) else 0
            for p in output.get("phases", [])
        )
        return (
            f"系统集成编排 {phases} 阶段 / 子场景={subs} / "
            f"用例 {cases}"
        )
