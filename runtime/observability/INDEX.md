# observability 索引

## 文件清单

| 文件 | 用途 |
| ------ | ------ |
| `otel.py` | OTel tracer/meter 初始化,FastAPI/Prefect 自动埋点 |
| `logging.py` | Loguru 结构化(JSON / 人类可读),run_id 自动注入 |

## span 链

```text
api.request                              # API 入口
└─ router.decide                         # LLM 决策
   ├─ llm.call (provider=claude|qwen)    # 模型调用
   └─ catalog.lookup                     # 注册中心查询
└─ orchestrator.flow_run                 # Prefect flow
   ├─ task.requirements-analyst
   ├─ task.testcase-designer
   └─ ...
└─ storage.write                          # 飞轮入库

```text

## 导出

OTLP gRPC → Tempo;日志 → Loki;指标 → Prometheus。
Compose 可选 profile `--profile observability` 起栈。
