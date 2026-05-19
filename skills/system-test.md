---
name: system-test
description: 系统集成测试 Skill。IoT 嵌入式（SSH/串口/MQTT）+ 音视频（FFmpeg）+ 链路追踪（Jaeger）+ 消息队列（Kafka/RabbitMQ）。底层调用 utils/iot_helper、utils/media_validator、utils/tracing_validator、utils/mq_helper。
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: production
---

# 系统集成测试 Skill

## 触发方式

```text
/system-test [子场景：iot|media|tracing|mq 或 复合描述]
```

## 🔔 开测前准备清单（按子场景）

```text
IoT/嵌入式：
□ SSH 凭证 → IOT_SSH_HOST / USER / PASSWORD
□ 串口路径 + 波特率 → IOT_SERIAL_PORT / IOT_SERIAL_BAUDRATE
□ MQTT broker → IOT_MQTT_BROKER

音视频：
□ ffmpeg + ffprobe 已装（系统 PATH 中可用）
□ 测试视频/音频文件路径

链路追踪：
□ Jaeger HTTP API URL → JAEGER_BASE_URL
□ 已知 trace_id（来自业务请求）

消息队列：
□ Kafka brokers → KAFKA_BROKERS
□ RabbitMQ URL → RABBITMQ_URL
□ topic / queue 名称
```

## 适用场景

- IoT / 嵌入式设备：SSH 命令执行、串口通信、MQTT 消息
- 音视频校验：分辨率、码率、帧对比、音画同步
- 微服务链路：trace 完整性、耗时、跨服务调用
- 消息队列：Kafka / RabbitMQ 投递+消费验证
- 跨服务端到端：A→B→C 业务流 + traceID 串联

## 执行流程

### Step 1：环境检查

```bash
# 各组件可用性
ssh -V
python -c "import paramiko; print(paramiko.__version__)"
python -c "import serial; print(serial.__version__)"
python -c "import paho.mqtt.client as m; print('mqtt ok')"
ffmpeg -version
ffprobe -version
curl ${JAEGER_BASE_URL}/api/services      # Jaeger 健康
```

### Step 2：执行测试（按子场景）

```bash
# IoT
pytest -m "system and iot" -v

# 音视频
pytest -m "system and media" -v

# 链路追踪
pytest -m "system and tracing" -v

# 消息队列
pytest -m "system and mq" -v

# 全部系统集成
pytest -m "system and p0" -v
```

## 质量门禁

| 子场景 | 关键指标 | 要求 |
|-------|---------|------|
| IoT | SSH 响应、MQTT 投递成功率 | 100% / >99% |
| 音视频 | 帧 SSIM、音画偏移 | ≥0.95 / <80ms |
| 链路追踪 | Trace 完整服务覆盖 | 100% |
| MQ | 消息投递+消费成功率 | 100% |

## 输出文件

```text
workspace/执行日志/
├── iot-logs/
├── media-frames/
├── tracing/
└── mq-logs/
```
