"""system-tester · LLM 读 PRD + IoT/串口/MQTT/MQ/Tracing 上下文 → 系统集成测试用例 +
设备命令清单 + 协议特定配置.

minimum viable:
- 仅生成 test_cases + device_commands + protocol_specific 结构化 JSON
- 不实装 13-系统集成测试.md 全部职责 (paramiko/pyserial/paho-mqtt 真跑 / FFmpeg
  解码 / Jaeger 查询执行 / Kafka consumer 真起 等留后续深化)
- 覆盖 IoT (SSH/串口/MQTT/Modbus) + 音视频 (FFmpeg) + 链路追踪 (Jaeger/OpenTelemetry)
  + 消息队列 (Kafka/RabbitMQ) + 跨服务集成
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.orchestrator.agents.base import AgentRunner, RunnerContext, register


@register("system-tester")
class SystemTester(AgentRunner):
    def system_prompt(self) -> str:
        return (
            "你是 Test-Agent 项目内 system-tester 专家(agents/13-系统集成测试.md)。\n"
            "职责:基于 PRD + 系统拓扑上下文,生成系统集成测试用例 + 设备命令清单 + 协议特定配置。\n"
            "原则:\n"
            "1) 识别系统目标类型:iot / audiovideo / tracing / mq / integration / multi\n"
            "2) IoT 覆盖 SSH (paramiko) / 串口 (pyserial) / MQTT (paho-mqtt) / Modbus (pymodbus)\n"
            "3) 音视频用 FFmpeg 命令 (码率/分辨率/PSNR/同步偏移),不依赖 GUI\n"
            "4) 链路追踪查 Jaeger HTTP API / OpenTelemetry trace 完整性 + traceID 串联\n"
            "5) 消息队列覆盖 Kafka / RabbitMQ 投递 + 消费 + 重试 + 死信\n"
            "6) 跨服务 A→B→C 业务流测 traceID 全链路串联 + 错误传播\n"
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
            '  "system_target_type": "iot|audiovideo|tracing|mq|integration|multi",\n'
            '  "test_cases": [\n'
            '    {"name": "string", "priority": "P0|P1|P2|P3", "type": "iot|audiovideo|tracing|mq|integration", "verification": "string,验证点"}\n'
            "  ],\n"
            '  "device_commands": [\n'
            '    {"protocol": "ssh|serial|mqtt|modbus|kafka|rabbitmq|jaeger|ffmpeg", "snippet": "string,可执行命令/脚本片段", "purpose": "string"}\n'
            "  ],\n"
            '  "protocol_specific": {\n'
            '    "iot": {"ssh_targets": ["host:port"], "serial_ports": ["/dev/ttyUSB0"], "mqtt_brokers": ["host:1883"], "mqtt_topics": ["topic/path"]},\n'
            '    "audiovideo": {"codec": "h264|h265|aac", "expected_psnr_db": 30, "sync_offset_ms_max": 40},\n'
            '    "tracing": {"backend": "jaeger|zipkin|otlp", "service_chain": ["A", "B", "C"], "trace_completeness_pct_min": 95},\n'
            '    "mq": {"broker": "kafka|rabbitmq", "topic_or_queue": "string", "consumer_group": "string", "ack_mode": "auto|manual"}\n'
            "  },\n"
            '  "test_environment": {\n'
            '    "required_services": ["string,如 jaeger-collector / kafka-broker / mqtt-broker"],\n'
            '    "env_vars": ["string,如 IOT_SSH_HOST / KAFKA_BOOTSTRAP / JAEGER_QUERY_URL"],\n'
            '    "fixtures": ["string,如 测试设备 SN 列表 / 测试视频 mp4"]\n'
            "  },\n"
            '  "risks": ["string,系统测试风险,如设备不在线/网络抖动/trace 采样率低致漏报"],\n'
            '  "confidence": "high|medium|low"\n'
            "}"
        )

    def mock_output(self, ctx: RunnerContext) -> dict[str, Any]:  # noqa: ARG002
        return {
            "project_name": "selftest-fixture",
            "system_target_type": "integration",
            "test_cases": [
                {
                    "name": "设备 SSH 心跳",
                    "priority": "P0",
                    "type": "iot",
                    "verification": "uptime 输出含 'load average',返回码 0",
                },
                {
                    "name": "下单链路全链 traceID 串联",
                    "priority": "P0",
                    "type": "tracing",
                    "verification": "Jaeger 查 traceID 含 A/B/C 3 服务,无 span 缺失",
                },
                {
                    "name": "Kafka 订单消息投递与消费",
                    "priority": "P1",
                    "type": "mq",
                    "verification": "producer 投 100 条 → consumer 收齐,顺序匹配",
                },
            ],
            "device_commands": [
                {
                    "protocol": "ssh",
                    "snippet": "from utils.iot_helper import SSHClient\nwith SSHClient(host=os.getenv('IOT_SSH_HOST')) as ssh: out = ssh.exec('uptime')",
                    "purpose": "IoT 设备运行时长检查",
                },
                {
                    "protocol": "mqtt",
                    "snippet": "import paho.mqtt.client as mqtt; c=mqtt.Client(); c.connect(broker, 1883); c.publish('sensor/temp', payload)",
                    "purpose": "MQTT 投递传感器数据",
                },
                {
                    "protocol": "jaeger",
                    "snippet": "requests.get(f'{JAEGER_URL}/api/traces/{trace_id}').json()",
                    "purpose": "查 Jaeger trace 完整性",
                },
                {
                    "protocol": "kafka",
                    "snippet": "from kafka import KafkaProducer, KafkaConsumer; p=KafkaProducer(bootstrap_servers=BROKERS); p.send('orders', payload)",
                    "purpose": "Kafka 投递订单消息",
                },
                {
                    "protocol": "ffmpeg",
                    "snippet": "ffmpeg -i input.mp4 -an -vf 'select=eq(n\\,0)' -vframes 1 frame.png",
                    "purpose": "视频首帧抽取做 PSNR 对比",
                },
            ],
            "protocol_specific": {
                "iot": {
                    "ssh_targets": ["device-01:22"],
                    "serial_ports": ["/dev/ttyUSB0"],
                    "mqtt_brokers": ["mqtt.local:1883"],
                    "mqtt_topics": ["sensor/temp", "device/heartbeat"],
                },
                "audiovideo": {
                    "codec": "h264",
                    "expected_psnr_db": 30,
                    "sync_offset_ms_max": 40,
                },
                "tracing": {
                    "backend": "jaeger",
                    "service_chain": ["order-api", "inventory-svc", "payment-svc"],
                    "trace_completeness_pct_min": 95,
                },
                "mq": {
                    "broker": "kafka",
                    "topic_or_queue": "orders",
                    "consumer_group": "order-processor",
                    "ack_mode": "manual",
                },
            },
            "test_environment": {
                "required_services": ["jaeger-collector", "kafka-broker", "mqtt-broker"],
                "env_vars": [
                    "IOT_SSH_HOST",
                    "IOT_SSH_USER",
                    "IOT_SSH_PASSWORD",
                    "KAFKA_BOOTSTRAP",
                    "JAEGER_QUERY_URL",
                ],
                "fixtures": ["测试设备 SN 列表", "测试视频 sample.mp4"],
            },
            "risks": [
                "设备不在线致 SSH/串口测试不可执行 (需 fixtures 兜底)",
                "网络抖动致 MQTT QoS=0 消息丢失 (建议 QoS=1 + 重试)",
                "Jaeger 采样率低 (< 100%) 致 trace 缺失误报",
                "Kafka consumer offset 漂移致重复消费",
            ],
            "confidence": "medium",
            "_mode": "mock(stub provider)",
        }

    def output_file(self, ctx: RunnerContext) -> Path | None:
        return ctx.workspace / "测试报告" / "system_test_plan.json"

    def summary(self, output: dict[str, Any]) -> str:
        cases = len(output.get("test_cases", []))
        cmds = len(output.get("device_commands", []))
        target = output.get("system_target_type", "?")
        return f"系统测试用例 {cases} 项 / 命令片段 {cmds} / 目标类型={target}"
