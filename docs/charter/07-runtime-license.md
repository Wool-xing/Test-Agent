<!--
本文件由 `FULL_GUIDE.md` 拆分而来 (W7-d 文档重构, 2026-05-14)。
原始单文件 1252 行 → 7 子文件; 主 FULL_GUIDE.md 改为索引。
内容与原 FULL_GUIDE.md 对应段完全一致, 仅拆不动语义。
-->

## 🧠 V1.1.0-alpha 运行时层(`runtime/`)

> 已有 14 专家 / 13 Skill / 49 脚本**不动**(宪章铁律),`runtime/` 仅作可执行调度层。
> 让"文档+脚本工具箱"升级为"可被 API/CLI/CI 直接调用的运行时"。

### 模块拓扑

```
用户输入(任意格式)
   │
   ▼
runtime/api  或  runtime/cli         ← 统一入口
   │
   ▼
runtime/router                       ← LiteLLM 多厂商 + Ollama 兜底
   │ (DAG:专家+Skill+顺序+置信度+理由)
   ▼
runtime/orchestrator                 ← Prefect 2.x flow + Direct 降级执行器
   │
   ├─► 02-专家定义/*.md              ← Claude Code 加载
   ├─► 03-技能定义/*.md              ← Skill 调用
   └─► 05-代码示例/*.py              ← 49 脚本(subprocess 隔离)
   │
   ▼
runtime/storage 飞轮                  ← Postgres+pgvector + MinIO
   │
   ▼
报告 + 通知(复用已有 utils/)
```

### 八维测试矩阵(运行时元数据骨架)

| 维度 | 取值 |
|------|------|
| 平台 | Web/移动/桌面/嵌入式/云原生/中间件/DB/AI模型/区块链/IoT/工控 |
| 协议 | HTTP(S)/gRPC/WS/TCP/UDP/MQTT/AMQP/Kafka/Redis/SOAP/GraphQL/Modbus/CAN |
| 测试类型 | 单元/集成/E2E/UI/API/性能/压力/容量/混沌/安全/渗透/模糊/合规/可访问性/兼容/本地化/可用性/视觉回归/契约/可观测 |
| 流程 | 需求评审 → 用例 → 数据/Mock → 执行 → 缺陷 → 回归 → 上线监控 |
| 自动化层 | 录制 / 手写 / AI 生成 / AI 自愈 / 自主决策 |
| 部署 | 本地/Docker/K8s/Serverless/边缘 |
| Profile | 通用层做厚 + 行业 Profile 留扩展位(`profiles/`,M2 上线) |
| 智能等级 | L0 脚本 → L1 数据驱动 → L2 关键字 → L3 AI 辅助 → L4 自主决策 |

### 多厂商 LLM 路由

```bash
TAGENT_LLM_PROVIDER=claude     # anthropic/claude-sonnet-4-6
TAGENT_LLM_PROVIDER=openai     # openai/gpt-4o
TAGENT_LLM_PROVIDER=gemini     # gemini/gemini-1.5-pro
TAGENT_LLM_PROVIDER=qwen       # openai/qwen-plus
TAGENT_LLM_PROVIDER=deepseek   # deepseek/deepseek-chat
TAGENT_LLM_PROVIDER=ollama     # ollama/qwen2.5:7b(本地)
TAGENT_LLM_PROVIDER=stub       # 测试 stub(不出网)

TAGENT_LLM_PROVIDER_FALLBACK=ollama  # 主路由失败回退
```

支持**双模型投票**:`route_with_vote(artifact, providers=["claude","qwen"])`。分歧 → 降低 confidence,合并 DAG 节点。

### 飞轮 schema(`runtime/storage/`)

| 表 | 用途 |
|----|------|
| `runs` | 一次执行(run_id/输入/状态/DAG/起止) |
| `cases` | 测试用例(优先级/步骤/结果/专家/技能) |
| `defects` | 缺陷(严重度/状态/根因/外部 Bug 系统 URL) |
| `evidence` | 证据(MinIO key+sha256:截图/录屏/HAR/日志) |
| `feedback` | 用户标注(误报/漏报/路由对错) |
| `embeddings` | pgvector 向量(用例/缺陷/报告语义检索) |

### 一键起 + 跑通

```bash
# 1. 起本地依赖(Postgres + MinIO + Prefect Server)
cd runtime && docker compose up -d

# 2. 跑数据库迁移
cd runtime/storage && alembic upgrade head

# 3. 校验注册中心
python -m runtime.cli.main catalog

# 4. 单次跑(本地直跑,不上 Prefect 也行)
TAGENT_LLM_PROVIDER=stub python -m runtime.cli.main run "Web 系统 https://example.com"

# 5. 起 HTTP 服务
uvicorn runtime.api.main:app --port 8800
# POST /run/text, /run/file, /run/url
# GET /status/{run_id}, /report/{run_id}, /catalog, /health
```

### Prefect 缺席降级(Direct 执行器)

`runtime/orchestrator/direct.py` 提供与 Prefect flow 等价契约的纯标准库执行器(ThreadPoolExecutor 并发,Kahn 拓扑排序)。Prefect 未装时 `Kernel.execute_sync` 自动回落,**让小团队/CI 离线测可不依赖 Prefect 部署**。

### 八维路由准确率(M1 收口)

- 5 类典型输入(web/api/mobile/desktop/ai-model)stub 路由 = 5/5(100%)
- M1 门槛:多模型真测 ≥85%;不达 → 双模型投票

### 与 14 专家 / 13 Skill / 49 脚本的关系

| 项 | 关系 |
|----|------|
| 14 专家 `.md` | **不动**。`registry` 扫 frontmatter,`router` 喂 LLM 选用 |
| 13 Skill `.md` | **不动**。同上 |
| 49 脚本 `.py` | **不动**。`orchestrator/adapters/scripts.py` subprocess 隔离调用 |
| `utils/` 通知/Bug | 复用 `generate_report.py` / `zentao_bug_manager.py` |

任何专家/Skill/脚本**新增**或**修改**仍按宪章 §1 同步铁律走;`runtime/` 是新增 **调度** 层,不重复实现专家逻辑。

---

## 📜 LICENSE / CHANGELOG / CONTRIBUTING / SECURITY

- **LICENSE**：MIT（详见 [`LICENSE`](LICENSE)）
- **CHANGELOG**：详见 [`CHANGELOG.md`](CHANGELOG.md)（V1.0.0 首版含 darwin-skill 集成 / Bug 多适配 / AgentChat 协议 / 按需安装 + 运行时补装 / 永久宪章定位）
- **VERSION**：详见 [`VERSION`](VERSION)
- **CONTRIBUTING**：详见 [`CONTRIBUTING.md`](CONTRIBUTING.md)（含同步铁律 + RACI 矩阵）
- **SECURITY**：详见 [`SECURITY.md`](SECURITY.md)（漏洞报告流程 + GitHub Security Advisories 入口）
- **CODE_OF_CONDUCT**：详见 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)（基于 Contributor Covenant 2.1）

---

## 🗺️ 项目当前状态与下次会话快速指引

### 当前阶段（最后更新：2026-05-11）

- **Phase**：Phase 1（V1.0.0 工程基线 + 概念宪章已成）
- **关键已交付**：14 agent + 14 skill + AgentChat + Bug 多适配 + 按需安装（含运行时补装） + darwin-skill 集成

### 历史关键决议

- 2026-05-11：宪章四章 + 三公理 + 五铭文起草完成（基于 DeepSeek 四轮 + Claude 整理）
- 2026-05-11：FULL_GUIDE.md 糅合全局记忆，确立永久宪章地位
- 2026-05-11：darwin-skill 不消费运行数据（Via Negativa 显式标注）；反问 KB 不进 V1.0.0
- 2026-05-11：V1.0.0 阶段铭文锁死，单签兼任不构成有效授权

### 下次会话进入项目时，按顺序检查

1. 本节「当前阶段」是否仍是 Phase 1？是否有新里程碑？
2. 「📋 开放问题」第 Q1-Q8 是否有新决议？
3. 「Phase 触发条件总表」哪一行的触发条件已达成？
4. 「🎭 关键模块清单」是否有模块从 ⚪/❌ 升级到 ✅？
5. 是否需要扩写某一章节为深度版？
6. 是否需要把开放问题转成 Jira 风格的可分配任务？

### 来源与引用（认知史）

- 第一轮（DeepSeek）：测试 Agent 七阶段架构
- 第二轮（DeepSeek）：认知暗物质 + 10 个反问
- 第三轮（DeepSeek）：抽象/探索/哲学维度
- 第四轮（DeepSeek）：全人类 + 全行业视角
- 第五轮（Claude 补充）：神圣 / 危机 / 临界层 10 个新增
- 整理框架：八大簇 → 九大簇演进（Claude 整理）
- 宪章草案：四章 + 三公理 + 五铭文（Claude 草拟）
- V1.0.0 工程基线：14 agent + 14 skill + utils 49 个 + CI/CD（项目自建）
- 永久宪章糅合（2026-05-11）：FULL_GUIDE 工程主体 + 全局记忆哲学维度合一

---

*本文档是活的，每次重大决策后须更新「📋 开放问题」与「🗺️ 项目当前状态」两节。改其他章节须经 test-lead review，符合闭环约定 14/15/16。*
