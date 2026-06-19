"""MCP servers for Test-Agent.

6 servers per project:
  - test-orchestrator: 主调度,包装 runtime/orchestrator
  - protocol-adapter:  HTTP/gRPC/WS/MQTT/Kafka 协议层
  - evidence-vault:    证据/录屏/日志(MinIO + Postgres)
  - defect-tracker:    工单桥(5 adapter zentao/jira/github/linear/webhook)
  - knowledge-base:    历史用例+缺陷向量检索(pgvector)
  - compliance-checker: 行业合规规则库(SOC2/PCI/HIPAA/IEC 62304 等)

All servers respect:
  - 已有不动 → 仅包装,不修改 16 专家/32 skill/67 脚本
  - 横切: 失败可复现(seed+snapshot+录屏),不入回归库否
  - 决策可追溯 → 工具调用落 decisions/
"""
