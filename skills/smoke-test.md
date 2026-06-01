---
name: smoke-test
description: 冒烟测试 Skill，仅执行 P0 核心用例，10 分钟内快速验证主干功能是否正常。门禁通过率 ≥95%（与 test-lead 全栈口径对齐）。适用于代码合并前、每日构建验证、发布前最后确认。
tools: Read, Write, Bash, Grep, Glob
SKILL_IMPL_STATUS: production
---

# 冒烟测试 Skill（Smoke Test）

> **目标**：10 分钟内完成核心功能验证。仅测 P0 用例，快速暴露主干流程问题。

## 🔔 调用前置准备

```text
□ env-manager 已通过基础健康检查
□ workspace/测试用例/*.xlsx 存在含 P0 用例（或 testcase-designer 先生成）
□ workspace/测试数据/test_data.json 存在（或 data-preparer 兜底）
□ workspace/自动化脚本/python/ 含 P0 用例（marker @pytest.mark.p0）
□ pytest.ini markers 已注册项目模块 marker
□ HEADLESS=true（CI）/ false（本地调试）
```

缺项 test-lead 会 prompt 用户补齐。

## 📋 执行流程（含 1 分钟缓冲，总上限 11 分钟）

### 阶段1：环境检查（1 分钟）

调用 **env-manager**，执行快速健康检查：
- 应用服务可达性（HTTP 2xx）
- 数据库 TCP 探活
- Redis ping
- Mock 服务（可选）

环境检查失败 → 立即终止 + 报告，**不执行测试**。

### 阶段2：P0 用例筛选（1 分钟）

```text
- 读取 workspace/测试用例/*.xlsx
- 过滤条件：优先级 = P0
- 排除标记 @pytest.mark.flaky 用例（已隔离）
- 预期 P0 数量：10~30 条（取决于模块规模）
```

### 阶段3：最小数据准备（1 分钟）

调用 **data-preparer**，仅准备 P0 必要数据：
- 复用 `workspace/测试数据/test_data.json`（若存在则直接用，无则调用 data_factory 生成基础账号）
- 不做完整 cleanup，只确保必要数据存在

### 阶段4：P0 用例执行（5 分钟）

```bash
pytest workspace/自动化脚本/python/ \
    -v -m "p0" \
    --timeout=60 \
    -n 2 \
    --alluredir=workspace/测试报告/allure-results \
    --junitxml=workspace/执行日志/smoke-results.xml \
    --tb=short \
    --no-header
```

> 冒烟阶段**不开 reruns**（与 utils/flaky_detector 检测策略一致）。

### 阶段5：结果判定（2 分钟）

```bash
python -m utils.ci_quality_gate \
    --smoke-xml workspace/执行日志/smoke-results.xml \
    --output-json workspace/执行日志/smoke_gate_result.json
```

### 阶段6：报告生成（1 分钟，缓冲）

```bash
allure generate workspace/测试报告/allure-results \
    --output workspace/执行日志/allure-report \
    --clean
```

## ✅ 通过标准（Gate）

- **P0 用例通过率 ≥ 95%**（与 test-lead 门禁、utils/ci_quality_gate 一致）
- **新增 P0 级 Bug = 0**
- **核心 API 响应时间 < 3s**

> 注：旧版"P0 任意 1 个失败立即停止"已废弃。统一以 95% 通过率为准。

## 输出示例

**通过：**
```text
✅ 冒烟测试通过
模块：用户登录模块 V1.0.0
执行时间：8 分 32 秒
P0 用例：25 个，通过 25 个，失败 0 个（100%）
结论：可以继续部署 / 全量测试
```

**失败：**
```text
❌ 冒烟测试失败，阻止部署
模块：用户登录模块 V1.0.0
执行时间：7 分 15 秒
P0 用例：25 个，通过 23 个，失败 2 个（92.0% < 95%）
失败用例：
  - TC-LOGIN-API-001：断言失败，实际返回 502
  - TC-LOGIN-UI-005：超时（>60s）
结论：主干功能异常，请修复后重新执行冒烟测试
```

## ✅ 质量检查清单

每次冒烟测试必须检查：
- [ ] 环境健康检查通过
- [ ] P0 用例全部执行（无遗漏）
- [ ] 执行时间 < 11 分钟（含缓冲）
- [ ] 失败用例已记录 + 自动分类
- [ ] 判定结果明确（通过/失败）+ JSON 落地

## ⚠️ 注意事项

1. **冒烟测试不是全量测试**：只测 P0，不代表所有功能正常
2. **失败必须阻止后续阶段**：冒烟失败应阻止后续部署或全量测试
3. **快速反馈**：结果应在 11 分钟内给出，否则测试设计有问题
4. **CI 集成**：每次 PR / push 自动触发（见 ci/）
