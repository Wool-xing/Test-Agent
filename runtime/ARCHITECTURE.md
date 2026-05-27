# 运行时层架构

> 2026-05-11 立项,在不改 14 专家 / 13 Skill / 67 脚本前提下,新增可执行运行时,让"文档+脚本工具箱" → "可被 API/CLI/CI 直接调用的产品"。

## 战略判断

- "全平台/全协议/全测试类型/全行业全覆盖" = 项目死亡信号。Selenium/Postman/k6/JMeter 均单点打透赢
- 已有 14 专家+13 Skill 编排骨架 = 真护城河,真正稀缺是 **智能编排层 + 数据飞轮**
- 三阶段串行打通,门槛守严:
  - **B(M1-M6) QA 团队编排平台** — 摘已有资产最低果实
  - **A(M7-M12) 开发者自测**(IDE 插件) — 需 B 飞轮数据喂养再打
  - **C(M13-M18) CI 中间件**(原生集成 Jenkins/GitLab/Argo/Tekton/K8s Operator) — 需 A+B 背书

## 双层架构

| 层 | 内容 | 谁维护 |
|----|------|--------|
| **L1 核心闭包** | 测试编排引擎 / 14 专家+调度器 / 输入解析器 / 输出渲染器 / MCP 协议层 / 飞轮 / AI 路由 | 自己 |
| **L2 扩展面** | 协议适配器市场 / 测试类型 Skill 包 / 行业 Profile / 工具桥 / 报告模板 | 社区/插件/AI 生成 |

## 八维测试矩阵

| 维度 | 取值 |
|------|------|
| 平台 | Web/移动/桌面/嵌入式/云原生/中间件/DB/AI模型/区块链/IoT/工控 |
| 协议 | HTTP(S)/gRPC/WS/TCP/UDP/MQTT/AMQP/Kafka/Redis/SOAP/GraphQL/Modbus/CAN |
| 测试类型 | 单元/集成/E2E/UI/API/性能/压力/容量/混沌/安全/渗透/模糊/合规/可访问性/兼容/本地化/可用性/视觉回归/契约/可观测 |
| 流程 | 需求评审 → 用例 → 数据/Mock → 执行 → 缺陷 → 回归 → 上线监控 |
| 自动化层 | 录制 / 手写 / AI 生成 / AI 自愈 / 自主决策 |
| 部署 | 本地/Docker/K8s/Serverless/边缘 |
| Profile | 通用层做厚 + 行业 Profile 留扩展位 |
| 智能等级 | L0 脚本 → L1 数据驱动 → L2 关键字 → L3 AI 辅助 → L4 自主决策 |

**警告**:不要让维度交叉乘积爆炸成 N^8 测试包;AI 路由按需取交集。

## 6 个 MCP 服务规划

| MCP | 职责 | 状态 |
|-----|------|------|
| `mcp-test-orchestrator` | 主调度,被测物→专家组合 | M2 上线 |
| `mcp-protocol-adapter` | 协议层统一抽象 | M2 上线 |
| `mcp-evidence-vault` | 证据/录屏/日志 | M2 上线 |
| `mcp-defect-tracker` | 工单桥(Jira/禅道/PingCode/飞书) | M2 复用现有 |
| `mcp-knowledge-base` | 历史用例+缺陷+RCA 向量检索 | M2 起步 |
| `mcp-compliance-checker` | 行业合规规则库(空载,L2 扩展) | M3 |

## 选型

| 项 | 选型 |
|----|------|
| LLM 抽象 | **LiteLLM** 多厂商 + Ollama 兜底 + stub(测试) |
| 编排引擎 | **Prefect 2.x** + 自研 Direct 降级执行器(无 Prefect 也能跑) |
| 执行器底层 | Pytest 复用(67 脚本本就是 pytest 生态) |
| DB | Postgres + **pgvector** |
| 对象存储 | MinIO |
| 报表 OLAP | ClickHouse(M3 上,M1 不急) |
| API | FastAPI + Pydantic v2 |
| CLI | Typer + Rich |
| 观测 | OpenTelemetry + Loguru |
| UI | M3 上,M1 仅 CLI |
| 开源时机 | **M3 上运行时再开源** |

## M1 交付清单

| # | 模块 | 路径 | 状态 |
|---|------|------|------|
| 1 | 目录骨架+pyproject | `runtime/` | ✅ |
| 2 | AI 路由 v1 | `runtime/router/` | ✅ stub 5/5 类型 |
| 3 | 注册中心 | `runtime/registry/` | ✅ 14+13 实跑验证 |
| 4 | 编排(Prefect+Direct) | `runtime/orchestrator/` | ✅ E2E 通 |
| 5 | FastAPI 入口 | `runtime/api/` | ✅ 6 端点 |
| 6 | Typer CLI | `runtime/cli/` | ✅ `tagent run|plan|catalog|doctor` |
| 7 | 飞轮 schema | `runtime/storage/` | ✅ 6 表 + Alembic |
| 8 | OTel+Loguru | `runtime/observability/` | ✅ |
| 9 | docker-compose | `runtime/docker-compose.yml` | ✅ 含 observability profile |
| 10 | E2E smoke | 验证脚本 | ✅ 路由 5/5 + DAG 8 节点 direct 模式跑通 |
| 11 | 文档同步 | 本节 + README + FULL_GUIDE + CHANGELOG + VERSION + 00-导航 | ✅ |

## 八维路由验证

| 输入 | 期望 | 实测 |
|------|------|------|
| `Web system https://example.com login flow` | web-system | ✓ web-system + 8 专家 |
| `REST API gRPC endpoints to test` | rest-api | ✓ rest-api + 6 专家 |
| `APK mobile Android app` | mobile-app | ✓ mobile-app + mobile-tester |
| `Windows desktop exe app` | desktop-app | ✓ desktop-app + desktop-tester |
| `LLM AI model evaluation pipeline` | ai-model | ✓ ai-model + ai-tester |

**stub 准确率 = 5/5 = 100%**(自包含,不出网)。M1 真模型门槛 ≥85%,M2 双模型投票。

## M2 路线图

| 任务 | 内容 |
|------|------|
| MCP 6 件套 | `mcp-test-orchestrator/-protocol-adapter/-evidence-vault/-defect-tracker/-knowledge-base/-compliance-checker` 上线 |
| Web UI | 单页 React:上传被测物 → 看 DAG 实时进度 → 看报告 → 看证据 |
| 真模型路由 | Claude+Qwen 实测,准确率 ≥85% |
| 协议适配器 | HTTP/gRPC/WS/MQTT/Kafka 5 协议起步 |
| 行业 Profile 插槽 | `profiles/general-web.yaml` 示例 + 加 Profile 文档 |

## 放弃条件

- W1 末:骨架+注册没完成 → 慢一周接受
- W3 末:路由+编排没贯通 → 砍 OTel+ClickHouse,优先打通
- W5 末:E2E demo 跑不通 → 砍移动/AI 专家,只跑 Web+API
- W6 末:文档没同步 → **不准 bump 版本**
- 客户 <2 → 砍 A,固守 B
- DAU < 1000(A 阶段) → 加固 B,不进 C
