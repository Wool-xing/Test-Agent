<!--
本文件由 `FULL_GUIDE.md` 拆分而来 (W7-d 文档重构, 2026-05-14)。
原始单文件 1252 行 → 7 子文件; 主 FULL_GUIDE.md 改为索引。
内容与原 FULL_GUIDE.md 对应段完全一致, 仅拆不动语义。
-->

## 🏛️ 项目宪章（灵魂底色）

> 三公理 + 五条铭文 + 工程映射 + V1.0.0 锁死 + 双签解锁条件 — 已迁入主宪章 §10（memory `project_test_agent_workflow.md`），FULL_GUIDE 不再重复维护。

---

## 📚 文档导航

| 路径 | 文档 | 说明 | 适用对象 |
|------|------|------|----------|
| 根目录 | README.md | 简明入口（≤ 200 行） | 所有用户 |
| **根目录** | **00-项目导航.md** | **按职责分类速查（通用流程 / 平台专项 / 协议 / 输入 / CI）** | **所有用户** |
| **根目录** | **FULL_GUIDE.md（本文档）** | **永久宪章 + 完整指南** | **所有用户** |
| `docs/getting-started/` | 使用手册.md | 快速上手指南 + FAQ | 所有用户 |
| `docs/getting-started/` | 部署说明.md | 跨平台部署（Win/Mac/Linux 含 Java/JMeter/Allure） | 运维/测试 |
| `docs/getting-started/` | 配置清单.md | 一站式配置文档（.env 全字段 + Secrets + Webhook 申请） | 所有用户 |
| `docs/getting-started/` | 交付物清单.md | 测试计划 / 测试报告 / Bug 等对外提交物落地位置与责任 | 所有用户 |
| `agents/` | 16 个 .md（9 核心 + 5 平台 + 2 垂直） + README 索引 | Agent 定义文件 | 开发人员 |
| `skills/` | 32 个 Skill 文件（业务 skill） + 3 个元 Skill 子目录 + README 索引 | 可复用测试技能 | 开发人员 |
| `config/` | conftest.py / pytest.ini / .env.example / .mcp.json / requirements.txt | 配置文件集合 | 开发人员 |
| `config/` | mcp-server-impl.md | MCP server 自实现教程（zentao/wechat/feishu/dingtalk 骨架） | 高级开发 |
| `utils/` | utils（79 个 .py + init）+ README 索引（多分类） | 完整可运行 Python 工具集 | 开发人员 |
| `ci/` | github-actions-test.yml / jenkins-pipeline.groovy / 集成说明.md | CI/CD 流水线（含 JMeter 性能阶段） | DevOps |

---

## 🌌 维度全图（九大簇 · Agent 看世界的方式）

> 工程矩阵之下的认知地图——回答"测试 Agent 到底需要哪些维度的能力"。各簇能力的工程落点散布在「核心特性」「全链路覆盖矩阵」「关键模块清单」中。
> **接入策略**：簇 1-2 为 V1.0.0 主交付；簇 3-5 部分进入工程矩阵；簇 6-9 多数列入 Phase 2-4 路线图，**承认存在但不假装能立刻交付**——符合第三公理。

### 簇 1 · 工程与架构层（V1.0.0 主体）
- 七阶段工作流：需求理解 → 用例生成 → 执行 → 观测 → 根因 → 反馈 → 治理
- 自动化工具栈、Agent 协作协议、用户交互界面
- 决策回放器、停机演练、可观测性递归

### 簇 2 · 认知暗物质层（V1.0.0 部分 + Phase 3 补全）
- 认知债务（被遗忘的 Why）
- 跨系统嗅觉（上下游气味相投）
- 沉默故障（不报警的恶化）
- 灾难人类学（事故残骸还原文化）
- 道德/偏见审计

### 簇 3 · 时空与历史层（Phase 3-4）
- 时间旅行 / 历史债务回溯
- 多宇宙反事实推演
- 制度性愚蠢抗体
- 生态位"暗杀"攻击建模

### 簇 4 · 抽象与元层（V1.0.0 部分）
- 预兆感知（弱信号 + 拓扑同调）
- 反目标函数（对测试本身的测试）
- 语言游戏（语义歧义放大器）
- 哥德尔不完备宣告
- 测试热寂与熵减祭司
- 本体论测试（数字孪生 vs 物理承诺）

### 簇 5 · 行业元逻辑层（V1.0.0 参照表 + Phase 2 选定 MVP）
- 金融=承诺守恒、医疗=伤害可逆、法律=边界例外
- 教育=认知脚手架、农业=优雅降级、艺术=避免审查官
- 自动驾驶/机器人=物理承诺

### 簇 6 · 文明与生态层（Phase 4）
- 文明记忆守护者 / 代际解释责任
- 跨物种与生态共情
- 缓慢暴力 / 长时间尺度测试
- 末日哨兵权

### 簇 7 · 社会与权力层（Phase 3-4）
- 真相衰减 / 信息生态测试
- 数字权力审计（反垄断、反算法歧视）
- 缺席者代言人

### 簇 8 · 灵性与意义层（Phase 4）
- 意义感流失测量、减速测试
- "有些事不在此域"的铭文
- 测试者作为"未来僧侣阶层"

### 簇 9 · 神圣 / 危机 / 临界层（Phase 4-5）
- 神圣性与不可亵渎边界（宗教、葬礼、纪念）
- 濒危语言与文化灭绝速率
- 精神危机状态响应
- 生命阶段适配（儿童 / 孕期 / 临终）
- 极端断网与"最后服务"
- 司法可采信性
- 集体踩踏测试
- 数字遗产与亡者数据
- 科学可复现性
- 跨语言隐喻与禁忌翻译

---

## 🎭 关键模块清单（测试 Agent 的工具箱）

> 每个模块对应一个 utils 或 skill 的工程落点；划分到对应簇便于追溯认知来源。
> **Phase 标注**：✅ V1.0.0 已交付；⚪ Phase 2-4 路线图；❌ Phase 4-5 概念阶段。

| 模块 | 职能 | 所属簇 | 工程落点 | 阶段 |
|------|------|--------|----------|------|
| 语义歧义放大器 | 枚举术语的多重解释 | 抽象元层 | requirements-analyst + AgentChat 反问 | ✅ |
| 反目标函数引擎 | 对自身策略对抗性拆解 | 工程/元层 | `utils/mutation_runner.py` + suite_minimizer | ✅ |
| 拓扑流形观测器 | 学习系统"气氛"，捕捉弱信号 | 抽象元层 | tracing_validator + web_vitals_collector | ✅ |
| 熵减祭司 | 监测测试热寂、焚毁僵尸用例 | 抽象元层 | `utils/suite_minimizer.py` | ✅ |
| 决策回放器 | 任一判断可复现、可反驳 | 工程层 | `workspace/测试报告/{项目名}/decisions/` + tracing | ✅ |
| 数字考古学家 | 追溯遗留系统初始假设 | 文明层 | Phase 4 知识图谱冷启动 | ❌ |
| 缓慢暴力监测器 | 跨发布周期跟踪代际效应 | 文明层 | 需多年数据积累，Phase 4 | ❌ |
| 缺席者画像生成器 | 强制注入边缘用户场景 | 文明/权力层 | absentee_scenario_injector.py (9组场景) | ✅ |
| 现实缝合力探针 | 测试平台对半真半假内容的免疫 | 社会权力层 | ai_adversarial 扩展 | ⚪ |
| 公平性审计器 | 数据集/模型/决策公平性指标 (DI/EO/校准/交叉) | 社会权力层 | fairness_auditor.py | ✅ |
| 沉默故障探测器 | 无报警漂移检测/趋势分析/多源聚合 | 工程层 | silent_failure_detector.py | ✅ |
| 缺席者场景注入器 | 9组边缘场景(残障/老年/未成年/离线/危机/非母语)剧本库+章节生成 | 文明/权力层 | absentee_scenario_injector.py | ✅ |
| 末日哨兵 | 计算"这一次就是那一次"概率 | 文明层 | 需监管/学界共识授权，Phase 4 | ❌ |
| 神圣性守护器 | 识别宗教/纪念场景的不可亵渎边界 | 簇 9 | i18n_checker + taboo_matrix 禁忌矩阵 | ✅ |
| 精神危机响应器 | 模拟危机状态用户、验证交接路径 | 簇 9 | 缺席者剧本库子集 | ❌ |
| 踩踏推演器 | 群体情绪与系统反馈的正反馈回路 | 簇 9 | chaos_helper 扩展 | ❌ |
| 司法证据包生成器 | 决策链、模型版本、数据集打包 | 簇 9 | evidence_chain.py + dora_metrics + decisions/ 打包脚本 | ✅ |
| 禁忌矩阵 | 跨文化禁忌词/色/数/节日组合 | 簇 9 | i18n_checker 本地化共建 | ❌ |
| Bug 多适配引擎 | 5 套 tracker 切换 | 工程层 | `utils/bug_tracker_base.py` + `zentao_bug_manager.py` + `jira_bug_manager.py` + `github_bug_manager.py` + `linear_bug_manager.py` + `webhook_bug_manager.py` | ✅ |
| AgentChat 协调器 | 讨论触发 / 中枢路由 / 反问留档 | 工程层 | test-lead + `discussions/` | ✅ |
| 按需安装引擎 | 6 层依赖 + 运行时补装 | 工程层 | `requirements/` (base/mobile/desktop/visual/system/ai/perf 七文件) + `install.py` | ✅ |
| darwin-skill 自进化 | skill 文本结构棘轮优化 | 工程/元层 | `.claude/skills/darwin-skill/` | ✅ |

---

## 🚀 核心特性

### 16 位专家（核心 9 + 平台扩展 5 + 垂直领域 2）

| 角色 | 职责 |
|------|------|
| **test-lead**（协调者） | 全局调度、质量把控、发布决策、基线管理 |
| requirements-analyst | 测试范围界定、风险识别、业务规则梳理（输出 MD + JSON 摘要） |
| testcase-designer | 等价类/边界值/场景法，P0~P3 分级，4 Sheet Excel |
| env-manager | 环境健康检查、多环境切换、Docker 支持 |
| data-preparer | 数据工厂（Faker+Factory Boy）、自动清理、脱敏、JMeter CSV |
| automation-engineer | Playwright（UI）+ requests（API）+ JMeter 驱动（性能）+ Locust（开发期备用） |
| test-executor | 并行执行、失败分类、Flaky 隔离、JMeter 性能阶段 |
| bug-manager | Bug 提交（5 适配器：禅道/Jira/GitHub/Linear/Webhook）、生命周期追踪、回归验证 |
| report-generator | Allure + JMeter HTML + Word + 多端通知（企微/飞书/钉钉/Slack/邮件/Teams，curl 直连） |
| mobile-tester / desktop-tester / visual-tester / system-tester / ai-tester | 平台扩展 5 位专家 |
| pentest-tester / automotive-tester | 垂直领域 2 位专家（渗透安全 + 车载/自动驾驶） |

### 32 个业务 Skill + 3 个元 Skill

**通用流程 8 个**：

- `smoke-test`：10 分钟 P0 冒烟（门禁 95%）
- `test-coordinator`：完整流程编排
- `regression-test`：P0+P1 回归 + Flaky 检测 + JMeter 性能验证
- `testcase-design`：4 Sheet Excel 用例 + 多格式导出
- `python-script-gen`：pytest UI/API 脚本
- `jmeter-script-gen`：JMeter JMX 脚本（CI quick / full 双模式）
- `data-preparation`：测试数据 + JMeter 参数化 CSV
- `zentao-bug-submission`：Bug 规范提交（按 `BUG_TRACKER` 自动路由 5 套 tracker）

**平台扩展 5 个**：`mobile-test` / `desktop-test` / `visual-test` / `system-test` / `ai-test`

**垂直领域 12 个**：渗透安全 7（pentest-coordinator/recon/vuln/exploit/web/api/report）+ 车载 5（automotive-test/can-bus/adas/hil-loop/ota）

**ECC 测试加固 6 个**：`tdd-workflow` / `e2e-testing` / `verification-loop` / `eval-harness` / `security-review` / `agent-introspection-debugging`

**探索 + 元工具 4 个**：`build-your-own-x-explorer` + `karpathy-guidelines` + `darwin-skill` + `nuwa-skill`

> 完整 32 业务 Skill + 3 元 Skill 清单见 [ROADMAP.md](../../ROADMAP.md) 与 [skills/README.md](../../skills/README.md)。

### 工程级质量门禁（分层）

**功能门禁**

| 指标 | 冒烟 | 回归 |
|------|------|------|
| P0 通过率 | ≥95% | 100% |
| P1 通过率 | - | ≥95% |
| 整体通过率 | - | ≥90% |
| 代码覆盖率（$APP_SRC_PATH） | - | ≥80% |
| Flaky 比例 | - | <5% |

**性能门禁（双模式）**

| 指标 | full（50并发） | ci_quick（5并发） |
|------|--------------|------------------|
| TPS | ≥100 | ≥20 |
| P95 响应 | ≤500ms | ≤800ms |
| 平均响应 | ≤200ms | ≤400ms |
| 错误率 (pct) | <1% | <1% |
| 基线回归 | <20% | 不强制 |

### 工程化规范

- **指数退避重试**：`utils/api_retry_util.call_with_retry`（10s → 20s → 40s）
- **pytest-xdist** 并行执行（默认 4 进程，可调）
- **Flaky 检测与隔离**：`utils/flaky_detector` + `workspace/测试报告/{项目名}/history/` 归档
- **性能基线管理**：`workspace/测试报告/{项目名}/baselines/perf_baseline.json`，仅 release+full+PASS 自动更新
- **CI/CD 就绪**：GitHub Actions + Jenkins，性能阶段双模式分层
- **MCP 收口**：当前仅启用 filesystem；通知/Bug 走 SDK 直连

---
