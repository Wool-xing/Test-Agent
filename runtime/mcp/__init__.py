"""MCP servers for Test-Agent.

6 servers per project charter §16:
  - test-orchestrator: 主调度,包装 runtime/orchestrator
  - protocol-adapter:  HTTP/gRPC/WS/MQTT/Kafka 协议层
  - evidence-vault:    证据/录屏/日志(MinIO + Postgres)
  - defect-tracker:    工单桥(5 adapter zentao/jira/github/linear/webhook)
  - knowledge-base:    历史用例+缺陷向量检索(pgvector)
  - compliance-checker: 行业合规规则库(SOC2/PCI/HIPAA/IEC 62304 等)

All servers respect:
  - 主宪章 §9: 已有不动 → 仅包装,不修改 14 专家/14 skill/49 脚本
  - 主宪章 §21 横切: 失败可复现(seed+snapshot+录屏),不入回归库否
  - 主宪章 §18-12: 决策可追溯 → 工具调用落 decisions/
"""
