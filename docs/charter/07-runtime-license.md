<!--
本文件由 `FULL_GUIDE.md` 拆分而来 (W7-d 文档重构, 2026-05-14)。
原始单文件 1252 行 → 7 子文件; 主 FULL_GUIDE.md 改为索引。
内容与原 FULL_GUIDE.md 对应段完全一致, 仅拆不动语义。
-->

## 🧠 V1.23.0 运行时层(`runtime/`)

> 已有 16 专家 / 32 Skill / 49 utils**不动**(宪章铁律),`runtime/` 作可执行调度层 + 真 LLM-driven agent/skill runner。
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

### 与 16 专家 / 32 Skill / 49 utils 的关系

| 项 | 关系 |
|----|------|
| 16 专家 `.md` | **不动**。`registry` 扫 frontmatter,`router` 喂 LLM 选用 |
| 32 Skill `.md` | **不动**。同上 |
| 49 utils `.py` | **不动**。`orchestrator/adapters/scripts.py` subprocess 隔离调用 |
| `utils/` 通知/Bug | 复用 `generate_report.py` / `zentao_bug_manager.py` |

任何专家/Skill/脚本**新增**或**修改**仍按宪章 §1 同步铁律走;`runtime/` 是新增 **调度** 层,不重复实现专家逻辑。
V1.14+ 真 LLM-driven agent runner + V1.21+ SkillRunner 系统为 runtime 新增执行能力,详见 [ROADMAP.md](../../ROADMAP.md)。

---

## 📜 LICENSE / CHANGELOG / CONTRIBUTING / SECURITY

- **LICENSE**：MIT（详见 [`LICENSE`](LICENSE)）
- **CHANGELOG**：详见 [`../../CHANGELOG.md`](../../CHANGELOG.md)（V1.31.0 含 17 版累积 / expert rollout 收尾 / skill rollout 全 14/14 完成）
- **VERSION**：详见 [`VERSION`](VERSION)
- **CONTRIBUTING**：详见 [`CONTRIBUTING.md`](CONTRIBUTING.md)（含同步铁律 + RACI 矩阵）
- **SECURITY**：详见 [`SECURITY.md`](SECURITY.md)（漏洞报告流程 + GitHub Security Advisories 入口）
- **CODE_OF_CONDUCT**：详见 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)（基于 Contributor Covenant 2.1）

---

## 🗺️ 项目当前状态与下次会话快速指引

### 当前阶段（最后更新：2026-05-16）

- **Phase**：Phase 2 前期（V1.31.0 · expert rollout 收尾 + skill rollout 完成 14/14）
- **关键已交付**：16 expert (11p+5s) · 32 skill (23p+7s+0r+2v) · AgentChat · Bug 多适配 · 按需安装 · darwin-skill · MCP 6 件套 · Marketplace · 教学层 · 多 LLM config · 16 SkillRunner 全落地
- **活跃 PR**：无（V1.31 rollout 完成，2026-05-16）

### 历史关键决议

- 2026-05-11：宪章四章 + 三公理 + 五铭文起草完成
- 2026-05-11：FULL_GUIDE.md 确立永久宪章地位
- 2026-05-11：darwin-skill 不消费运行数据（Via Negativa）；反问 KB 不进 V1.0.0
- 2026-05-12 ~ 2026-05-14：V1.1-V1.14 runtime 层 + 教学层 + Marketplace + 渗透/车载 + Hermes + GBrain + Karpathy + ECC
- 2026-05-15 ~ 2026-05-16：V1.15-V1.26 13 版迭代 — 11 expert 真 LLM-driven 落地 + 4 SkillRunner 生产落地 + 多 LLM config + 深审修复

### 下次会话进入项目时，按顺序检查

1. 本节「当前阶段」是否有新里程碑？
2. 「Phase 触发条件总表」哪一行的触发条件已达成？
3. ROADMAP.md skill rollout 进度
4. 是否有新 charter 缺口需回写？

### 来源与引用（认知史）

- 第一至五轮（DeepSeek + Claude）：测试 Agent 架构 + 九大簇
- V1.0.0 工程基线：14 agent + 14 skill + 49 utils + CI/CD（历史基线）
- V1.1.0 ~ V1.31.0：runtime + 11 agent runner + 16 skill runner + 教学/市场/多LLM（详见 CHANGELOG + ROADMAP）
- 永久宪章糅合（2026-05-11/14/16）：FULL_GUIDE 工程主体 + 全局记忆哲学维度 + 持续回写

---

*本文档是活的，每次重大决策后须更新「📋 开放问题」与「🗺️ 项目当前状态」两节。改其他章节须经 test-lead review。*
