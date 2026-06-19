---
name: testcase-design
description: 快速生成测试用例技能。输入需求描述，调用 testcase-designer 专家生成结构化测试用例，输出格式由用户自选：默认 Excel（4 Sheet），可选 xmind / markmap / opml 思维导图，或 --format all 一键产全部。适用于用例评审、快速梳理测试点。
tools: Read, Write, Grep, Glob
SKILL_IMPL_STATUS: production
---

# 测试用例快速生成

## 触发方式

```text
/testcase-design [需求描述或功能名称]

```text

## 🔔 调用前置准备

```text

□ PRD 文档（任意格式：md/pdf/docx/xlsx/pptx/zip/png/url）
□ 或 requirements-analyst 已生成 requirements_summary_*.json
□ openpyxl 已装（生成 4 Sheet Excel）
□ utils/excel_generator.py 部署到 utils/
□ 业务模块名（用于用例 ID：TC-{MODULE}-{TYPE}-{NUM}）

```text

## 适用场景

- 需求评审阶段，快速梳理测试点
- 手工测试时，快速生成用例清单
- 自动化脚本开发前，确认测试范围
- 单独生成用例，不需要完整测试流程

## 执行流程

### Step 1：需求解读（requirements-analyst 简化版）

- 识别核心功能点
- 确定优先级分级
- 列出业务规则
- 识别高风险区域

### Step 2：用例设计（testcase-designer）

- 等价类划分
- 边界值分析
- 场景法（核心流程）
- 错误推测（高风险区域）
- 输出 Excel 文件（4 Sheet）

## 输出格式

### 控制台预览（快速）

```text

=== 测试用例清单（预览）===
功能模块：[用户登录]
用例数量：34 条（P0:5, P1:12, P2:12, P3:5）

P0 核心用例（5 条）：
  TC-LOGIN-UI-001  正确账号密码登录       ✓
  TC-LOGIN-API-001 登录接口返回 token      ✓
  TC-LOGIN-UI-002  记住密码功能            ✓
  TC-LOGIN-UI-003  Token 刷新机制          ✓
  TC-LOGIN-UI-004  退出登录清除会话        ✓

P1 主要用例（12 条）：
  TC-LOGIN-UI-005  账号不存在提示
  TC-LOGIN-UI-006  连续失败 5 次锁定
  ... 详见 Excel

[Excel 已保存至 workspace/测试用例/testcases_登录_20260510.xlsx]

```text

### Excel 文件（默认）

落盘路径：`workspace/测试用例/testcases_[模块]_[YYYYMMDD].xlsx`

由 `utils/excel_generator.create_testcase_excel(testcases, output_path)` 生成 4 Sheet：

-**Sheet1 用例总览**：优先级分布 + 模块分布统计
-**Sheet2 测试用例**：完整用例（16 列，含 API 字段 method/path/headers/expected_status）
-**Sheet3 P0冒烟集**：仅 P0 用例（带前置条件、数据）
-**Sheet4 P0_P1回归集**：P0+P1 用例

### 思维导图 / 大纲

`runtime/exporters/` 已注册 3 个 exporter，用户自选；同一 TestCaseTree 一份 IR，三种落盘：

| `--format` | 扩展 | 用途 | 工具兼容 |
| ----------- | ------ | ------ | --------- |
| `xmind`   | `.xmind` | 思维导图（P0/P1/P2 自动转 marker） | XMind 8 / ZEN / 2020+ / Mind+ |
| `markmap` | `.md`    | Markdown 嵌入式（GitHub README 直渲） | markmap.js / VSCode 插件 |
| `opml`    | `.opml`  | 通用大纲交换 | MindManager / Workflowy / Word |
| `all`     | —        | 一键产全部 3 种 + Excel | 用户自挑 |

CLI：

```bash

tagent export plan.json --format xmind   --out workspace/测试用例/login.xmind
tagent export plan.json --format markmap --out workspace/测试用例/login.md
tagent export plan.json --format opml    --out workspace/测试用例/login.opml
tagent export plan.json --format all     --out-dir workspace/测试用例/

```text

`plan.json` 是 `TestCaseTree` 的 JSON 序列化（testcase-designer 输出，结构见 `runtime/exporters/INDEX.md`）。

## 用例 ID 规范

`TC-{MODULE}-{TYPE}-{NUM}`，TYPE ∈ {UI, API, PERF, SEC}。

示例：`TC-LOGIN-UI-001`、`TC-PAYMENT-API-003`、`TC-LOGIN-PERF-001`。

## 用例设计要点

### 必覆盖场景

```text

1. Happy Path（主流程）
2. 边界值（最大 / 最小 / 零 / 临界 / 空）
3. 异常处理（网络超时 / 并发 / 第三方失败）
4. 权限控制（无权限 / 越权 / 数据隔离）
5. 安全验证（SQL 注入 / XSS / 接口鉴权）

```text

### 优先级占比（合计 100%）

| 优先级 | 占比 |
| -------- | ------ |
| P0 | 10% |
| P1 | 30% |
| P2 | 40% |
| P3 | 20% |

### 用例数量参考

| 功能复杂度 | 预期用例数 |
| ----------- | --------- |
| 简单（单一输入/输出） | 5-10 条 |
| 中等（多步骤流程） | 15-25 条 |
| 复杂（多角色/多状态） | 30-50 条 |
| 模块级（含子功能） | 50-100 条 |

## 快速 Markdown 输出（评审场景）

当用户需要极快输出时，直接输出 Markdown 表格：

```markdown

| 用例ID            | 优先级 | 类型 | 场景         | 测试步骤                          | 预期结果              |
| ------------------- | -------- | ------ | ------------ | ---------------------------------- | --------------------- |
| TC-LOGIN-UI-001  | P0     | UI   | 正常登录     | 1.输入正确账号密码 2.点击登录       | 跳转首页              |
| TC-LOGIN-UI-002  | P0     | UI   | 空账号提交   | 1.账号留空 2.点击登录              | 提示"请输入账号"       |
| TC-LOGIN-UI-003  | P1     | UI   | 连续失败锁定 | 1.输错密码 5 次                    | 账号锁定提示           |

```text
