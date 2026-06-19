<!--
本文件由 `FULL_GUIDE.md` 拆分而来 (W7-d 文档重构, 2026-05-14)。
原始单文件 1252 行 → 7 子文件; 主 FULL_GUIDE.md 改为索引。
内容与原 FULL_GUIDE.md 对应段完全一致, 仅拆不动语义。
-->

## 🤝 AgentChat 协作协议（讨论 / 通信 / 反问）

> 解决三个问题：(1) agent 之间何时讨论；(2) 怎么通信不撞车；(3) 何时反问用户、怎么反问。
>**底线**：所有讨论、反问、跨 agent 协调都留可追溯纪要——`workspace/测试报告/{项目名}/discussions/{YYYYMMDD}_{topic}.md`，归档不可删。

### 1. 讨论触发条件（非每次都开会）

每次任务都开会 = 货物崇拜协作。只在**真分歧**时启动多 agent 讨论：

| 触发场景 | 参与 agent | 讨论形式 | 输出落点 |
| --------- | ----------- | --------- | --------- |
| 需求术语歧义 / 多种合理理解 | requirements-analyst + testcase-designer + test-lead | 2 轮提议+反对 | 测试计划「术语对齐」节 |
| 用例评审意见冲突 | testcase-designer + automation-engineer + 责任领域 expert | 1 轮评议 + test-lead 仲裁 | 用例 Excel 评审记录 Sheet |
| Bug 严重度争议（P0 vs P1） | bug-manager + test-executor + automation-engineer | 1 轮举证 + test-lead 拍板 | Bug 单内嵌讨论 thread |
| 性能门禁不达标的放行讨论 | test-executor + bug-manager + test-lead + 业务 expert | 2-3 轮风险评估 | 测试报告「放行决议」节 |
| 跨平台测试策略选择 | mobile / desktop / visual / system tester | 横向通气 | 测试计划「平台分工」节 |

**不触发讨论的情况**：明确指令执行、已有 SOP 的标准流程、单 agent 内部决策。

### 2. 通信路由（test-lead 中枢式，非全连接）

```text
            ┌──────────────┐
            │   test-lead  │ ← 唯一中枢
            └──────┬───────┘
                   │ (Agent tool 调用)
       ┌───────────┼─────────────┐
       ↓           ↓             ↓
   [analyst]  [designer]   [engineer] ...
       ↑           ↑             ↑
       └───────────┴─────────────┘
       专家间不直接通信，全部走 test-lead 路由

```text

**为什么不让 agent 互相直连**：全连接 = N² 复杂度 + 冲突无法仲裁 + 纪要难追溯。中枢式 = test-lead 看见所有上下文、防止双写文件冲突、自动归档讨论。

**唯一例外**：env-manager / data-preparer 串行链路允许直接传 fixture（不算"通信"，是流水线）。

### 3. 反问机制（agent 不假装全知）

agent 在三种情况**必须停下反问用户**，不允许猜：

| 反问触发信号 | 反问形式 | 示例 |
| ------------ | --------- | ------ |
| 需求术语有 ≥2 种合理解释 | 列举所有解释 + 标推荐 | "您说的'用户登录'指：(A) 手机号+密码 (B) SSO 单点 (C) 微信第三方 — 我推荐 A，对吗？" |
| 跨多种合理实现路径 | 列方案 + 利弊 + 默认推荐 | "Bug 工具 5 选 1：禅道（已配置）/ Jira / GitHub Issues / Linear / Webhook—默认走禅道" |
| 涉及不可逆操作（覆盖文件 / 生产环境 / 删除数据） | 强制二次确认 | "即将 git push --force，会覆盖远端 main—确认吗？" |

**反问预算按操作不可逆度分级**：

| 操作类别 | 单次任务反问预算 | 示例 |
| --------- | --------------- | ------ |
|**可逆操作**（重做不留痕） | ≤ 5 次 | 用例生成、数据准备、报告生成 |
|**半不可逆**（需手动回滚） | ≤ 3 次 | 脚本提交、Bug 提单、测试环境配置 |
|**不可逆**（影响真实数据/共享状态） |**强制单次明确确认，不计预算**| 覆盖文件、生产环境操作、删除数据、git push --force |

超预算 → 汇总成"待澄清清单"一次性问。

**反问纪律**（防过度反问）：

- 反问前必须给**带推荐的默认选项**，不做纯空白发问
- 反问全部落档到 `discussions/{date}_clarifications.md`
- 同一会话内不重复问已澄清过的同一术语

**不做的事（Via Negativa 显式标注）**：V1.0.0**不构建反问知识库（KB）**——不做 embedding 向量库、不做半结构化匹配引擎、不做语义检索。所有反问纪要落 `discussions/` 后由 test-lead 在新任务前**人工查阅**类似场景。

-**为什么不做**：(a) V1.0.0 时期数据量不足（< 100 条反问）；(b) 反问的"是否还有效"依赖项目阶段，自动复用可能传递过期判断；(c) 投入 KB 工程 ≠ 提升决策质量
-**现状更新（2026-05-16）**：discussions/ 累计反问 + 讨论纪要已超 200 条，进入 Phase 2 重新评估区间。详见 [06-test-architecture.md](06-test-architecture.md) Phase 2 触发条件
-**未来开案条件**：若需要开放反问 KB，须由 test-lead + 独立伦理责任人**双签**立项

### 4. 讨论纪要标准格式

```markdown

# {YYYY-MM-DD} {topic}

- 触发场景：xxx
- 参与 agent：[a, b, c]
- 提议：xxx
- 反对意见：xxx
- 仲裁（test-lead）：xxx
- 落点：xxx（测试计划 X 节 / Bug 单 Y / 用例 Excel Z Sheet）
- 决策版本：commit {sha}

```text

### 5. 落进交付物（不只是档案）

讨论结果**自动嵌入**对应交付物的"决议"节，不作为孤立文档存在。三份强制模板：

#### 5.1 测试计划「关键决议摘要」段（置于测试计划开头，需求分析之后）

```markdown

## 关键决议摘要

| 议题 | 决议 | 仲裁人 | 讨论纪要 |
| ------ | ------ | ------- | --------- |
| 术语「用户登录」澄清 | 取 SSO 单点 + 手机号备用 | test-lead | [→ 20260511_login-terms.md] |
| 兼容矩阵优先级 | Win 11 + Chrome 优先，IE 弃测 | test-lead | [→ 20260511_browser-matrix.md] |
| 平台分工 | iOS + Android 由 mobile-tester；Web 由 automation-engineer | test-lead | [→ 20260511_platform-split.md] |

```text

#### 5.2 测试报告「放行决议」章节（置于报告执行摘要之后、详细数据之前）

```markdown

## 放行决议（含投票/仲裁过程）

**结论**：✅ 同意上线 / ⚠️ 有条件放行 / ❌ 拒绝放行

**关键讨论**：

- 触发：性能门禁 P95=850ms > 阈值 500ms
- 提议方：test-executor「建议阻断」
- 反对方：业务 expert「峰值场景外阈值可接受」
- 仲裁（test-lead）：有条件放行——上线后 48h 内必须修复至阈值内，否则回滚
- 投票：3 赞成 1 弃权 0 反对
- 决议落档：discussions/20260511_perf-gate-release.md
- 决策快照：decisions/20260511_release_DEC-001.json

```text

#### 5.3 Bug 单争议讨论 thread（置于 Bug 描述末尾，仅争议 Bug 强制）

```markdown

---
**争议讨论**（严重度 P0 vs P1）：

- bug-manager 主张 P0：触发概率 30%，影响下单链路
- automation-engineer 反驳 P1：仅特定地区/网络组合下复现
- test-lead 仲裁：定 P0——影响下单链路即定 P0，与触发率无关
- 落档：discussions/20260511_bug-PG-2031-severity.md
---

```text

**规则**：争议未落档 → 不允许 Bug 单关闭、不允许测试报告签发、不允许测试计划评审通过。

---
