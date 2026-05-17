# Test-Agent 完善计划（全球测试专家视角，2026）

> 基于 4 维度并行代理深度分析 + 行业标杆对标
> 分析来源: 架构审查 / 企业就绪度 / 开发者体验 / 测试方法论

---

## 总览

| 阶段 | 主题 | 条目数 | 预计 commits |
|------|------|--------|-------------|
| Phase 3 | 引擎加固 | 5 | 5-7 |
| Phase 4 | 测试智能 | 5 | 5-8 |
| Phase 5 | 企业就绪 | 5 | 5-7 |
| Phase 6 | 开发者体验 | 5 | 4-6 |
| Phase 7 | 方法论深化 | 5 | 4-6 |
| Phase 8 | 平台化 | 5 | 4-6 |

---

## Phase 3: 引擎加固（执行可靠性）`最高优先级`

### #9 自愈引擎（Self-Healing）
- **现状**: 无。DOM 变更后测试断裂。`scripts.py` 无 selector 重试逻辑
- **行业对标**: Testsigma 90% / Mabl 85% 维护削减
- **方案**: 多属性元素追踪 (CSS+ARIA+文本+视觉) + 意图定位器 + locator 存储
- **文件**: 新建 `runtime/self_healing/`

### #10 Direct Executor 零重试
- **证据**: `runtime/orchestrator/direct.py:71-78` — 失败直接 append，无重试路径
- **影响**: stub LLM 一次失败 = DAG 节点失败，无恢复
- **方案**: 统一直连/Prefect 双路径重试逻辑，exponential backoff

### #11 on_failure="skip" 空实现
- **证据**: `runtime/orchestrator/tasks.py:38-39` — 声明为 skip 的节点仍计为失败
- **方案**: 实现真正的 skip（计为 skipped，不计入 failed）

### #12 共享 fixture 阻塞并行
- **证据**: `conftest.py:106,150` — session-scoped browser_context + test_data 共享可变文件
- **方案**: function-scoped fixture + 每个测试独立 tmp_path

### #13 DAG 执行无进度反馈 + 无断路器
- **证据**: `flows.py:36-44` — 10+ 节点全失败仍继续；无超时；无进度条
- **方案**: 加 `tqdm` 进度条 + `max_failures` 断路器 + per-node timeout

---

## Phase 4: 测试智能（分析 & 决策）

### #14 可观测性仪表板（Observability Dashboard）
- **现状**: `/dashboard` API 仅有 pass/fail 计数
- **行业对标**: 三行决策布局（决策信号→诊断趋势→行动）+ MTTD/MTTR
- **方案**: 加 flaky trend、环境健康、依赖延迟、用户旅程完成率图表

### #15 发布就绪评分（Release Readiness Score）
- **现状**: 无。test-lead 手动判断
- **行业对标**: 自动化 Go/No-Go，加权评分多维度
- **方案**: 加权评分 smoke×0.4 + regression×0.3 + perf×0.2 + security×0.1 → GREEN/YELLOW/RED

### #16 Flaky 测试自动隔离
- **现状**: `flaky_detector.py` 仅解析 junit-xml
- **行业对标**: 跨运行趋势分析 + 自动 quarantine
- **方案**: 加 Pass→Fail→Pass 模式检测，自动标记 `@flaky` + 隔离

### #17 测试影响分析（Test Impact Analysis）
- **现状**: `regression_scope.py` 做 git diff
- **行业对标**: 代码依赖图 + ML 选择最可能失败的测试
- **方案**: AST 解析 import 图 + pytest 覆盖率数据联合

### #18 需求可追溯性
- **现状**: `TC-{MODULE}-{TYPE}-{NUM}` 命名仅模块级
- **行业对标**: 双向追溯矩阵（需求 ID ↔ 测试用例 ID ↔ 缺陷 ID）
- **方案**: `prd_loader.py` 解析 PRD 生成需求 ID，自动链接到生成的测试用例

---

## Phase 5: 企业就绪（F500 采用）

### #19 RBAC 访问控制
- **现状**: 仅单 bearer token
- **方案**: 角色模型 admin/lead/tester/viewer + per-team namespace

### #20 审计追踪
- **现状**: 零审计日志
- **方案**: 所有操作记录 who/when/what + 不可变审计表

### #21 多租户
- **现状**: 无 tenant_id，所有数据共享
- **方案**: tenant_id 注入 + per-tenant 数据隔离

### #22 启动时配置校验
- **现状**: 23 env vars 缺配 → 运行时崩溃
- **方案**: pydantic `model_validator` 检查必填字段 + 启动时友好报错

### #23 执行生命周期钩子
- **现状**: `flows.py` 整体执行，无 before_node/after_node
- **方案**: 钩子注册机制 + 自定义指标/通知/策略注入

---

## Phase 6: 开发者体验（降低门槛）

### #24 安装步骤从 15→3
- **现状**: Python+Node+Git+Java+JMeter+Allure+Docker+install.sh+.env+claude+smoke = 15 步
- **对标**: Playwright 2 步
- **方案**: `tagent bootstrap` 一站式命令（检测+安装+配置+验证）

### #25 Debug 模式 + 日志级别开关
- **现状**: 11 个 `logger.debug()` 运行时不可见
- **方案**: `TAGENT_LOG_LEVEL` env + `--debug` CLI flag

### #26 错误消息可操作化
- **现状**: "internal error -- see logs" 无日志路径/无关联 ID
- **方案**: 所有错误附 log 路径 + correlation_id + 建议修复动作

### #27 新手教程
- **现状**: 无 tutorial/quickstart 目录
- **方案**: 5 步交互式教程：clone → bootstrap → demo → 第一个自定义测试 → 读报告

### #28 Shell 自动补全 + --no-color
- **方案**: `tagent --install-completion` + `--no-color` flag

---

## Phase 7: 方法论深化（测试科学性）

### #29 分支覆盖率门禁
- **现状**: 仅行覆盖率 `--cov-fail-under=80`
- **方案**: 启用 `--cov-branch` + 条件/决策覆盖率

### #30 测试代码静态分析
- **现状**: 被测代码有 SAST，测试代码无 lint
- **方案**: `pytest.ini` 集成 `pylint`/`radon` + 复杂度门禁

### #31 可移植性测试
- **现状**: ISO 25010 中覆盖最弱的一环
- **方案**: 可安装性/共存性/可替换性测试套件 + `@portability` marker

### #32 量化风险矩阵
- **现状**: 定性影响×概率，无校准
- **方案**: 概率校准 + 风险敞口阈值 + 缓解后再评估闭环

### #33 分类树方法（ISTQB 第10项）
- **方案**: 新建 `classification_tree.py` + `03-技能定义/classification-tree.md`

---

## Phase 8: 平台化（生态 & 扩展）

### #34 插件发现机制
- **现状**: 仅扫描固定目录
- **方案**: `importlib.metadata` entry_points 支持第三方包注册

### #35 测试数据合成引擎
- **方案**: 生产数据影子拷贝 + PII 自动脱敏 + 数据子集化

### #36 APM/Observability 预集成仪表板
- **方案**: 一键导出 Datadog/Grafana dashboard JSON

### #37 用户旅程影响映射
- **方案**: 测试结果标注影响的业务路径（注册/支付/核心操作）

### #38 多地域合成监控
- **方案**: GitHub Actions matrix 多地域定时执行 + 延迟热力图

---

## 执行顺序

```
Phase 3 (#9→#10→#11→#12→#13)  ← 引擎不牢，上层白搭
Phase 4 (#14→#15→#16→#17→#18)  ← 有了可靠执行，才谈智能分析
Phase 6 (#24→#25→#26→#27→#28)  ← 降低门槛 = 更多人用 = 更多反馈
Phase 5 (#19→#20→#21→#22→#23)  ← 企业客户需要的基本保障
Phase 7 (#29→#30→#31→#32→#33)  ← 测试方法论的科学严谨性
Phase 8 (#34→#35→#36→#37→#38)  ← 生态扩展
```

**共 30 项。** 每项独立 PR，先确认再动手。
