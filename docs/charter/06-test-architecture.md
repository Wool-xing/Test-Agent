<!--
本文件由 `FULL_GUIDE.md` 拆分而来 (W7-d 文档重构, 2026-05-14)。
原始单文件 1252 行 → 7 子文件; 主 FULL_GUIDE.md 改为索引。
内容与原 FULL_GUIDE.md 对应段完全一致, 仅拆不动语义。
-->

## 🏗️ 测试架构合理性深度（金字塔 / 左移 / 右移 / 可观测 / 门禁）

> 本节是项目方法论核心。回答："为什么这套架构合理？" "全球顶尖测试团队怎么看？"

### 1. 测试金字塔 2024 现代版

**经典金字塔**（Mike Cohn 2009）：单元 70% / 集成 20% / E2E 10%。

**2024 现代调整**（Google Testing Blog / Microsoft Engineering Fundamentals 综合）：

```text
            ┌─────────────────────┐
            │  E2E / 视觉回归  10% │  ← Playwright / Appium / Airtest（慢但必要）
            ├─────────────────────┤
            │  系统/契约      20% │  ← API + 服务间 + Pact + jsonschema + Mock
            ├─────────────────────┤
            │  集成/组件      30% │  ← pytest + pytest-mock + WireMock
            ├─────────────────────┤
            │  单元           40% │  ← pytest（秒级反馈，含变异测试）
            └─────────────────────┘
                ↑
        变异测试（mutation_runner）反向验证用例有效性
```

**与经典模型差异**：
- **不再 70%/20%/10% 一刀切**，按"变更频率 + 阻塞代价"重新分布
- 单元层增加变异测试 — 用例有效性必须可量化（不只覆盖率）
- 契约层独立成层（Pact/jsonschema/openapi_test_gen）— 微服务时代必备
- 视觉回归归 E2E 层（不另设层）— SSIM/OCR 与 E2E 一同 owner

**Test-Agent 落地**：
- 单元：`pytest + pytest-mock`（项目自身 utils 层 Phase 2 补齐自测）
- 集成：`pytest` 内嵌 + `wiremock 3.3.1` Mock Server
- 契约：`utils/contract_test.py` (Pact + jsonschema) + `utils/openapi_test_gen.py`
- E2E：`Playwright`（Web/Electron）+ `Appium`（移动）+ `Airtest`（视觉）
- 变异：`utils/mutation_runner.py`（mutmut）

### 2. Shift-Left（左移）— 测试介入越早越便宜

**Boehm 法则**：缺陷修复成本随开发阶段呈指数增长（需求 1× → 设计 5× → 编码 10× → 测试 50× → 生产 200×）。

**Shift-Left 实施层级**（从最早到最晚）：

| 层 | 介入点 | 工具 / utils | 阻断力 |
| ---- | -------- | ------------ | -------- |
| L1 | **需求阶段** | `requirements-analyst` 双轨输出（MD + JSON）+ 风险矩阵 | 弱（评审） |
| L2 | **设计阶段** | `testcase-designer` 等价类/边界值/状态迁移/配对测试 + 风险矩阵 | 弱（评审） |
| L3 | **IDE 编码时** | ruff + mypy + IDE 实时提示 | 强（编辑器红线） |
| L4 | **commit 前 (pre-commit)** | gitleaks + ruff + private-source 防护 + .env 防护 + 16/32/67 文件统计 | 强（阻断 commit） |
| L5 | **PR gate** | CodeQL + pip-audit + safety + ci.yml 全套 | 强（阻断合入） |
| L6 | **静态分析** | `security_scanner.py`（已实现）+ Bandit/ZAP/Burp Pro（Phase 2 CI 集成） | 中（发现/修） |
| L7 | **契约测试** | `utils/ci_contract_gate.py` + `contract_test_generator.py` + CI job | 强（CI 阻断） |

**Test-Agent 现状评估**：L1-L7 全部串通。L7 已通过 `ci_contract_gate.py` 实现自动检测 OpenAPI spec 变更 → 生成契约 → CI job 验证阻断。

**Phase 2 收尾点**：✅ 已完成。L7 契约链路已串成"PR 改了 OpenAPI spec → 自动跑 contract → 不通过阻断合入"。

### 3. Shift-Right（右移）— 生产即测试环境

**核心理念**：测试不止于发布前；通过生产监测 + 安全发布机制 + 主动故障注入持续验证质量。

**Shift-Right 实施层级**：

| 层 | 机制 | 工具 / utils | Test-Agent 状态 |
| ---- | ------ | ------------ | ---------------- |
| R1 | **合成监控**（Synthetic Monitoring） | 定时跑核心路径（登录/下单），24h 覆盖 | ⚪ 路线图 Phase 3 加 `utils/synthetic_monitor.py` |
| R2 | **真实用户监测**（RUM） | Web Vitals 上报 + 前端错误堆栈 | ✅ `utils/web_vitals_collector.py`（采集端） |
| R3 | **链路追踪**（Distributed Tracing） | Jaeger / Zipkin + traceID 业务断言 | ✅ `utils/tracing_validator.py` |
| R4 | **金丝雀发布**（Canary）+ **特性开关**（Feature Flag） | 渐进放量 + 回滚阀 | ⚪ 路线图 Phase 3 加 `utils/canary_runner.py` + `feature_flag_validator.py` |
| R5 | **混沌工程**（Chaos Engineering） | 主动注入 CPU/内存/磁盘/网络/进程/k8s 故障 | ✅ `utils/chaos_helper.py` |
| R6 | **灾备演练**（Failover Drill） | 主动 kill-pod + 数据一致性校验 | ✅ `utils/chaos_helper.kill_pod` |
| R7 | **A/B 测试**（Experimentation） | 多版本流量切分验证 | ⚪ 业务方按需自加 |
| R8 | **DORA 4 指标**（部署频率 / Lead Time / 失败率 / MTTR） | DevOps 健康度量 | ✅ `utils/dora_metrics.py` |
| R9 | **SLO/错误预算** | SLI 阈值 + 错误预算燃烧率 | ✅ `utils/slo_validator.py` |

**Phase 3 收尾点**：补 R1（合成监控）+ R4（canary/feature flag），完成 Shift-Right 闭环。

### 4. 可观测性（Observability）三柱 + 测试可视化

**三柱**（OpenTelemetry 标准）：
- **Traces**（链路）：`utils/tracing_validator.py`
- **Metrics**（指标）：JMeter result + DORA + flaky rate
- **Logs**（日志）：pytest log + logcat / iOS syslog（mobile_driver）+ 系统日志（desktop_driver）

**测试侧可观测**（独立于业务可观测性）：

| 维度 | 数据源 | 现状 | 可视化目标 |
| ------ | -------- | ------ | ---------- |
| 用例通过率 | junit-xml | ✅ Allure | Allure 报告 |
| 覆盖率 | coverage.xml | ✅ pytest-cov HTML | 覆盖率 HTML |
| 性能基线 | jmeter-results/result.jtl | ✅ JMeter HTML + baseline.json | JMeter HTML |
| Flaky 率 | history/junit-xml | ✅ flaky_detector | ⚪ 缺统一仪表盘 |
| DORA 4 指标 | git log + 缺陷库 | ✅ dora_metrics.py | ⚪ 缺统一仪表盘 |
| 缺陷密度/逃逸率/重开率 | bug tracker | ✅ bug-manager 内嵌 | ⚪ 缺统一仪表盘 |
| 用例减重信号 | 覆盖率 + Jaccard | ✅ suite_minimizer | ⚪ 报告内嵌 |
| 变异分数 | mutmut | ✅ mutation_runner | ⚪ 报告内嵌 |

**Phase 3 收尾点**：整合 flaky/DORA/缺陷密度/变异分数到统一 dashboard（Grafana 或 静态 HTML）。

### 5. 质量门禁分层（Layered Quality Gates）

**为什么分层**：一刀切门禁要么过严卡死开发节奏，要么过松形同虚设。分层 = 不同阶段不同严苛度。

**Test-Agent 五层门禁**：

| 层 | 触发 | 关键阈值 | 不达标处置 | 实现 |
| ---- | ------ | --------- | ---------- | ------ |
| **smoke** | 每次 commit/PR | P0 通过率 ≥95% + 0 新 P0 Bug + API ≤3000ms | 阻断后续 | `utils/ci_quality_gate.py::GATES['smoke']` |
| **regression** | merge 到 main / develop | P0=100% / P1≥95% / 总体≥90% / cov ≥80% / Flaky <5% | 评估遗留风险 | `utils/ci_quality_gate.py::GATES['regression_p0_p1']` |
| **performance_ci_quick** | CI 默认（5 并发） | TPS≥20 / P95≤800ms / err <1% | 警告不阻 | `utils/jmeter_result_parser.DEFAULT_GATES_CI_QUICK` |
| **performance_full** | release/* 分支 + 手动（50 并发） | TPS≥100 / P95≤500ms / 基线回归 <20% | 阻断 release | `utils/jmeter_result_parser.DEFAULT_GATES_FULL` |
| **release** | 上线前 | 上述全 PASS + bug-manager 审批 + test-lead 决策 | 不上线 | `agents/01-测试主管.md::上线决策` |

**门禁可配置性**：阈值集中在 `utils/ci_quality_gate.py::GATES` + `utils/jmeter_result_parser.py::DEFAULT_GATES_*`。Phase 2 抽 `quality_gate_engine.py` + yaml 驱动，让用户改阈值不需改代码。

**Flaky vs Reruns 设计哲学**：
- **冒烟阶段**：不开 reruns，**保留 flaky 信号**（Flaky 是质量问题，不是网络问题）
- **回归阶段**：开 reruns（`--reruns=2 --reruns-delay=5`），**追求快反馈**
- **Flaky 检测**：`utils/flaky_detector.py` 离线扫 history，失败率 >30% 标 quarantine
- **Quarantined 用例**：单独 marker `@flaky`，不计入门禁，每周清理

### 6. 调整路径（Phase 触发条件 + 关键交付）

> **不绑月份编号**——按触发条件推进，不按日历推进。"写进路线图就是承诺"，三年后回看不打脸的承诺，才写。

**Phase 触发条件总表**：

| Phase | 触发条件 | 标志性交付 |
| ------ | --------- | ---------- |
| **Phase 1**（已完成 V1.0.0-V1.36.0） | 概念宪章成 + 工程基线就绪 + expert rollout 收尾 + skill rollout 完成 | 16 expert (11p+5s) + 32 skill (23p+7s+0r+2v) + AgentChat + Bug 多适配 + 按需安装 + darwin-skill + MCP + 教学层 + Marketplace + 多 LLM config |
| **Phase 2** | utils 单测覆盖 ≥ 60% 且团队 ≥ 5 人 | 契约链路串通 + 门禁引擎 yaml 抽象 + 反问 KB 重新评估 + skill rollout 继续 |
| **Phase 3** | Phase 2 全交付 + 接入 ≥ 2 行业 | 合成监控 + canary/feature flag + 统一 dashboard + 沉默故障 + 缺席者注入 |
| **Phase 4** | 接入合规行业（金融/医疗/司法）| 证据链司法可采信打包 + 数字考古学家 + AI 测试深化 |
| **Phase 5** | 多语种多文化接入需求 | 神圣性守护 + 禁忌矩阵 + 跨文化 i18n |

**当前路线图详表**：

| 维度 | 现状 | 落点 Phase | 关键交付 |
| ------ | ------ | ----------- | --------- |
| **金字塔单元层** | 弱（utils 自身无测试） | Phase 2 | `tests/test_utils_*.py` 全覆盖 + 变异测试反向用 |
| **Shift-Left L7 契约链路** | utils 雏形未串通 | Phase 2 | OpenAPI 改动 → contract → PR 阻断 |
| **门禁引擎抽象** | 阈值写死代码 | Phase 2 | ✅ `utils/quality_gate_engine.py` + `config/quality_gates.yaml` 驱动 |
| **Shift-Right R1 合成监控** | 缺 | Phase 3 | `utils/synthetic_monitor.py` |
| **Shift-Right R4 canary + feature flag** | 缺 | Phase 3 | `utils/canary_runner.py` + `feature_flag_validator.py` |
| **可观测统一 dashboard** | 散落 HTML 报告 | Phase 3 | DORA + 缺陷密度 + flaky + 变异分数 → Grafana / 静态 HTML 模板 |
| **伦理 / 偏见审计** | 散落 utils | Phase 3 | 数据集偏差扫描 + 决策公平性指标 + 偏见门禁 |
| **沉默故障检测** | 缺 | Phase 3 | tracing 阈值漂移 + 无报警恶化检测器 |
| **缺席者场景注入** | a11y/i18n 已有 | Phase 3 | 边缘场景剧本库（残障/老年/未成年/未联网/精神危机） |
| **AI 测试深化** | 漂移 + LLM eval | Phase 4 | + prompt 版本回归 + RAG 召回精度 + token 成本门禁 + hallucination rate |
| **证据链 / 司法可采信打包** | 散落 | Phase 4 | 决策日志 + 模型版本 + 数据集 → 标准送审包 |
| **数字考古学家**（遗留系统初始假设回溯） | 缺 | Phase 4 | 知识图谱冷启动 + Why 数据库 |
| **神圣性守护 + 禁忌矩阵** | 缺 | Phase 5 | 跨文化禁忌词/色/数/节日组合（本地化共建） |
| **darwin-skill 集成（自进化）** | ✅ V1.0.0 已并入 | Phase 1 | 上游 SKILL.md + workspace 落 results.tsv + 季度同步 |
| **Bug Tracker 多适配** | ✅ V1.0.0 已并入 | Phase 1 | 5 套适配器（zentao/jira/github/linear/webhook）+ 工厂模式 |
| **AgentChat 协作协议** | ✅ V1.0.0 已并入 | Phase 1 | discussions/ 纪要 + test-lead 中枢路由 + 反问 3 级预算 |
| **按需安装与依赖分层** | ✅ V1.0.0 已并入 | Phase 1 | 6 requirements 文件 + install.py + 运行时补装回路 |

> **第三公理在此节兑现**：项目有意识地**少承诺**——文明级伦理议题（如缓慢暴力、末日哨兵、神圣性守护）我们承认其存在，但**不在工程路线图上假装能做**。如果未来接入特定行业（金融 / 医疗 / 司法）需要其中某项能力，由业务方按需单独立项，不绑进通用框架。

---

## ❓ 关键反问清单（决策入口）

> 进入项目重大决策前，按场景挑相应反问做一次自检——比直接动手安全 10 倍。
> 这些反问的回答应落档到 `discussions/{date}_strategic-questions.md`。

### 落地与可行性

- 哪 3 项能在 6 个月内做 MVP？哪些需 5 年以上数据？
- 如何把"测试热寂""意义感流失""缓慢暴力"转成 CI/CD 可消费的数值？
- "好奇心税"与"反目标函数"的额外算力如何 ROI？

### 架构与角色

- 单一巨型 Agent vs 专科 Agent 群？（当前选专科 + test-lead 中枢）
- 业务交付 Agent 与权力审计 Agent 冲突时谁仲裁？
- 元测试递归到第几层停止？

### 伦理与治理

- Agent 被垄断企业部署时，如何防止测试范围被裁剪？（铭文 2）
- 你愿意写下哪一条"不可逾越"的硬规则？（铭文）
- Agent 被强制关闭前的"遗嘱"留给谁？（铭文 5 + 熄火协议）

### 哲学与终局

- 你愿意亲手设计一个走向自我消解的 Agent 吗？
- 是否刻意保留"无害但不可预测"的缺陷？
- 你心中"绝不应被测试"的事是什么？（第三公理）

---

## 📋 开放问题与待决议事项

> **每条决策落定后须更新本表 + 在「🗺️ 项目当前状态」节追加里程碑**。
> 状态：⏳ 未定 / 🔄 评估中 / ✅ 已定 / ❌ 否决

| # | 议题 |  |  |
| --- | ------ | --------- | ------ |
|  |  |  |  |
| Q2 | Agent 架构：单体 vs 专 |  | V1.0.0 选专科 + test-lead 中枢 |
| Q3 | 五条铭文的技术实现机制（不可变区域、熔断条件）？ | 🔄 | V1.0.0 铭文锁死，无削弱机制；Phase 4 接入合规行业后重新设计 |
| Q4 | 独立审计署的法律实体形态？ | ⏳ | 触发条件：团队 ≥ 20 人 或 接入合规行业 |
| Q5 | 末日哨兵权的触发授权链？ | ⏳ | 需监管/学界共识，Phase 4 |
|  |  |  |  |
| Q7 | 团队最小配置（工程/行业专家/伦理责任人）？ | ⏳ | V1.0.0 单人可启动；剥离伦理责任人需 ≥ 20 人 |
| Q8 | 与现有 AI 测试平台（Mabl / Applitools / Functionize）的差异化定位？ | ⏳ | 候选定位：「承诺学科 + 伦理护栏 + 行业隐喻先行」 |

---

## 📖 关键术语表

宪章与工程文档共用术语。读者重新进入项目时，从这里建立词汇基线。

| 术语 | 释义 |
| ------ | ------ |
| 承诺学科 | 把测试从"检查代码"推进到"检查承诺"——金融的守恒、医疗的可逆、司法的可采信，都是承诺 |
| 隐喻先行 | 进入新行业前先建立"根本隐喻"档案，决定该测什么承诺、不碰什么红线 |
| 三筐分类 | Yes / No / **Too Hard**。大部分事进第三筐；不做决策也是决策 |
| 三公理 | 项目最高纲领（见首节）——承诺检验 / 谦卑义务 / 命名不可测之物 |
| 铭文 | 写入项目不可变区域的伦理约束（见首节五条铭文） |
| 认知债务 | 曾经存在但已被遗忘的设计 Why。数字考古学家的工作对象 |
| 测试热寂 | 所有测试通过、信息量趋零的状态。靠变异测试 + suite_minimizer 反向破解 |
| 缓慢暴力 | 跨年级别才显现的算法伤害（如教育算法十年后的代际效应）——单次发布无法发现 |
| 哥德尔宣告 | 明确声明某属性"真但不可测"。**承认局限，不假装能测** |
| 现实缝合力 | 信息平台抵抗真假混淆的能力。深度伪造时代核心 |
| 沉默故障 | 不报警的恶化——指标看着正常但用户体验/语义已塌 |
| 末日哨兵 | 极端风险下越过流程直达全人类的预警机制——需监管/学界共识授权 |
| 缺席者代言 | 为未联网者、残障者、未出生者保留测试用例配额 |
| 熄火协议 | Agent 被关闭前的遗嘱与决策链留存规则——多端通知 + Word 报告 + decisions/ 归档 |
| 货物崇拜 | 形式齐备但实质缺失——飞机跑道堆好了，飞机不会降落。本项目最大敌人之一 |
| Skin in the Game | 是否承担后果。Agent 的判断无 skin，因此最终决策由 test-lead 签字 |
| Via Negativa | 通过命名"不做的事"而非"做的事"来定义边界。本项目用它显式标注 darwin-skill 不自学习、反问不建 KB |
| 棘轮机制 | 改进后总分必须严格高于改进前才保留；退步自动回滚——darwin-skill 与门禁共用 |

---

---
