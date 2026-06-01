---
name: test-coordinator
description: 完整测试流程编排技能。输入需求文档或功能描述，自动调用核心 8 位专家 + test-lead（协调者，按 PRD 路由调用平台扩展 5 位专家）完成从需求分析到报告生成的完整测试流程。适用于新功能测试、迭代测试。
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: production
---

# 完整测试流程编排

## 触发方式

```text
/test-coordinator [需求描述或文档路径]
```

## 流程总览

```text
需求输入（任意格式：md/pdf/docx/xlsx/zip/截图/URL）
   ↓
utils.prd_loader.load_prd() ─→ 提取文本 + metadata
   ↓
utils.prd_loader.suggest_agents() ─→ 自动识别平台 → 路由表
   ↓
test-lead 决策（按路由动态编排专家组合）
   ↓
requirements-analyst（需求分析 → MD + JSON 摘要）
   ↓
testcase-designer（用例设计 → Excel 4 Sheet）
   ↓
env-manager（基础 connectivity 健康检查）
   ↓ 通过后
data-preparer（功能数据 JSON + JMeter CSV）  ← 等 env 基础检查通过再启动
   ↓
automation-engineer（pytest 脚本 + /jmeter-script-gen 子技能 → JMX）
   ↓
smoke-test（冒烟门禁：通过率 ≥95%）
   ↓ 通过
test-executor（功能回归：P0+P1，带 reruns + cov）
   ↓ 通过
test-executor（JMeter 性能测试，按 PERF_MODE 走 ci_quick / full）
   ↓
bug-manager（功能 Bug + 性能 Bug 提交追踪）
   ↓
report-generator（Allure + JMeter HTML + Word + 多端通知:企微/飞书/钉钉/Slack/邮件/Teams）
   ↓
test-lead（最终决策：功能+性能双门禁）
```

> 注：env-manager 与 data-preparer 严格上不是无依赖并行 —— data-preparer 需要 env 基础 connectivity 通过后才能写 DB；流程改为 env 完成后启动 data-preparer。

## 执行步骤

### Step 0：前置准备清单确认（test-lead）

平台识别后，先输出"开测前你需要准备什么"清单（详见 `agents/01-测试主管.md` "第零步：前置准备清单"段）。

清单按检测到的平台拼装。例：

```text
> /test-coordinator
> 帮我测试这个 Windows EXE 程序

[test-lead 自动输出：]
=== 开测前准备清单 ===
检测到：Windows 桌面 EXE 测试

【必备】
□ EXE 完整路径 → .env WIN_APP_PATH
□ Windows 系统（10/11）
□ pip 装 pywinauto + uiautomation
□ 应用版本号
□ 测试账号（如应用需登录）

【可选】
□ 注册表预设
□ 配套服务（Web 后端、DB）已就绪

请确认是否准备好。准备好回复"继续"，缺项告诉我哪一项。
```

用户确认或补齐后才进入 Step 1。

### Step 1：PRD 加载 + 平台识别 + 任务分析（test-lead）

```text
input: 用户提供的需求文档（任意格式）或自然语言描述
处理:
  1. 调 utils.prd_loader.load_prd(source) → 文本 + metadata
  2. 调 utils.prd_loader.suggest_agents(text) → 平台识别 + 路由建议
  3. 综合输出任务分析（含动态专家组合）
output:
  - 任务类型（新功能/回归/紧急修复）
  - 涉及平台（mobile_android / desktop_windows / api / ...）
  - 测试范围
  - 风险评估
  - 预估工时
  - 团队分工（核心 8 + 平台扩展按需）
```

### 路由分支（按平台识别结果动态编排）

```text
通用核心链路（8 必经）：
  requirements-analyst → testcase-designer → env-manager → data-preparer
                                                          ↓
                                                  automation-engineer
                                                  ↓ + 按平台并行调用
                              ┌──────────────────┼──────────────────┐
                              ↓                  ↓                  ↓
                      mobile-tester      desktop-tester     visual-tester
                      (Android/iOS/小程序) (EXE/.app/Electron) (游戏/视觉)
                              │                  │                  │
                              └──────┬───────────┴──────┬───────────┘
                                     ↓                  ↓
                            system-tester        ai-tester
                            (IoT/音视频/MQ/Tracing) (AI/LLM)
                                     ↓                  ↓
                                     └──────┬───────────┘
                                            ↓
                                    test-executor 统一执行
                                            ↓
                                    bug-manager → report-generator → test-lead 决策
```

### Step 2：需求分析（requirements-analyst）

```text
input: 需求文档 / PRD / 用户故事
output:
  - workspace/需求分析/requirements_analysis_{日期}.md
  - workspace/需求分析/requirements_summary_{日期}.json
```

### Step 3：用例设计（testcase-designer）

```text
input: 需求 JSON 摘要
output:
  - workspace/测试用例/testcases_[模块]_[日期].xlsx（4 Sheet）
  - 用例 ID 含 TYPE：TC-{MODULE}-{UI|API|PERF|SEC}-{NUM}
  - 自动化优先级标注
```

### Step 4：环境健康（env-manager）

```text
output: workspace/执行日志/环境检查_{时间戳}.json
失败 → 重试 10/20/40s → 仍失败则阻止后续步骤
```

### Step 5：数据准备（data-preparer，env 通过后启动）

```text
output:
  - workspace/测试数据/test_data.json（pytest 功能测试，conftest fixture 直接消费）
  - workspace/测试数据/jmeter_users.csv（JMeter 参数化）
```

### Step 6：脚本开发（automation-engineer）

```text
output:
  6a. pytest 功能脚本：workspace/自动化脚本/python/
  6b. JMeter JMX：workspace/自动化脚本/jmeter/test_plan.jmx（调用 /jmeter-script-gen）
依赖：workspace/测试数据/jmeter_users.csv
```

### Step 7：冒烟门禁

```text
执行: /smoke-test
条件: P0 通过率 ≥95% 且 无新增 P0 Bug
失败 → 停止，通知 test-lead，等待修复
```

### Step 8a：功能回归执行

```bash
pytest -m "p0 or p1" \
    -n 4 --reruns=2 --reruns-delay=5 --timeout=120 \
    --cov="${APP_SRC_PATH:-./src}" \
    --cov-report=xml:workspace/执行日志/coverage.xml \
    --cov-fail-under=80 \
    --alluredir=workspace/测试报告/allure-results \
    --junitxml=workspace/执行日志/regression-results.xml
```

阻塞条件：通过率 < 90% 时停止，不执行性能测试。

### Step 8b：JMeter 性能测试（功能回归通过后触发，分模式）

```bash
# 模式由 PERF_MODE 控制（默认 ci_quick；release/手动可设 full）
PERF_MODE="${PERF_MODE:-ci_quick}"

if [ "$PERF_MODE" = "full" ]; then
    THREADS=50; RAMPUP=60; DURATION=300
else
    THREADS=5;  RAMPUP=10; DURATION=60
fi

# TARGET_HOST/PROTOCOL/PORT 由 conftest 或 .env 解析（不含协议前缀）
jmeter -n \
    -t workspace/自动化脚本/jmeter/test_plan.jmx \
    -l workspace/执行日志/jmeter-results/result.jtl \
    -e -o workspace/执行日志/jmeter-report/ \
    -Jtarget_host="${TARGET_HOST}" \
    -Jtarget_protocol="${TARGET_PROTOCOL:-http}" \
    -Jtarget_port="${TARGET_PORT:-80}" \
    -Jthreads=${THREADS} -Jrampup=${RAMPUP} -Jduration=${DURATION}

# 解析 + 门禁
python -m utils.jmeter_result_parser \
    workspace/执行日志/jmeter-results/result.jtl \
    --mode "${PERF_MODE}" \
    --baseline workspace/执行日志/baselines/perf_baseline.json
```

### Step 9：Bug 管理（bug-manager）

```text
input:
  - 功能失败列表（failure_type=product_bug）
  - 性能门禁失败项
output:
  - 禅道 Bug ID 列表
  - 性能 Bug 标题：[性能]-[接口名]-[指标超标]
```

### Step 10：报告生成（report-generator）

```text
output:
  - Allure 交互式报告（功能）
  - JMeter HTML 报告（性能）
  - Word 测试报告（含性能基准对比）
  - Excel 数据报告
  - 多端通知:企业微信/飞书/钉钉/Slack/邮件/Teams（自动跳过未配置）
保存：workspace/测试报告/
```

### Step 11：最终决策（test-lead）

```text
output:
  - 功能门禁判定
  - 性能门禁判定（按 mode 选择 full / ci_quick 阈值）
  - 上线建议（通过/不建议/有条件）
  - 遗留风险
  - 下次迭代建议
  - 仅当 release 分支 + full 模式 + 全 PASS → 更新基线
```

## 质量门禁分层

### 冒烟门禁

| 指标 | 要求 |
|------|------|
| P0 通过率 | ≥95% |
| 新增 P0 Bug | 0 |
| 核心 API 响应 | <3s |

### 回归门禁

| 指标 | 要求 |
|------|------|
| P0 通过率 | 100% |
| P1 通过率 | ≥95% |
| 整体通过率 | ≥90% |
| 代码覆盖率（$APP_SRC_PATH） | ≥80% |
| Flaky 用例比 | <5% |
| 新增 P0 Bug | 0 |

### 性能门禁（双模式）

| 指标 | full（50并发） | ci_quick（5并发） |
|------|--------------|------------------|
| TPS | ≥100 | ≥20 |
| P95 响应 | ≤500ms | ≤800ms |
| 平均响应 | ≤200ms | ≤400ms |
| 错误率 | <1% (pct) | <1% (pct) |
| 基线回归 | <20% | 不强制 |

## 输出文件清单

```text
workspace/
├── 测试计划/
│   └── test_plan_[项目]_[日期].md         # test-lead 输出（IEEE 829 风格）
├── 需求分析/
│   ├── requirements_analysis_[日期].md
│   └── requirements_summary_[日期].json
├── 测试用例/
│   └── testcases_[模块]_[日期].xlsx
├── 测试数据/
│   ├── test_data.json                  # pytest fixture 消费
│   └── jmeter_users.csv
├── 自动化脚本/
│   ├── python/
│   └── jmeter/
│       └── test_plan.jmx
└── 执行日志/
    ├── allure-results/
    ├── allure-report/
    ├── coverage.xml
    ├── coverage-report/
    ├── jmeter-results/result.jtl
    ├── jmeter-report/index.html
    ├── baselines/perf_baseline.json
    ├── history/                        # junit-xml 归档（flaky_detector 用）
    ├── 截图/
    └── 报告/测试报告_[日期].docx
```

## 注意事项

1. 环境健康检查失败时，**必须等待环境恢复后才能继续**，不可跳过
2. 新增 P0 Bug 未修复时，**坚决不发布**，即使有业务压力
3. Flaky 用例不计入功能门禁，但需单独追踪并归档到 history
4. 每个步骤的输出保存到 workspace/ 对应目录
5. 所有 API 调用使用 `utils/api_retry_util.call_with_retry`（10s/20s/40s）
6. 通知通过 webhook 直连（utils/generate_report.send_*），未配置 webhook 自动跳过
