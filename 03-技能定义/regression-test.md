---
name: regression-test
description: 回归测试 Skill。执行 P0+P1 全量用例，对比历史结果，检测 Flaky 测试，含 JMeter 性能验证。适用于迭代发布前的完整回归。
tools: Read, Write, Bash, Grep, Glob
---

# 回归测试 Skill（Regression Test）

> **目标**：在版本迭代或重大变更后，验证新功能正常且老功能未退化。

## 📋 执行流程

### 阶段1：变更影响分析（5 分钟）

实现委托 `utils/regression_scope.py`：

```bash
python -m utils.regression_scope
# 输出：
# {
#   "changed_files_count": 12,
#   "affected_modules": ["login", "payment"],
#   "full_regression_needed": false,
#   "recommendation": "targeted"
# }
```

**模块映射规则**：优先读 `workspace/regression_modules.yaml`（项目自定义），无配置则用 `DEFAULT_MODULES`。

`workspace/regression_modules.yaml` 示例：

```yaml
modules:
  login:
    - auth/
    - user/login
    - session/
  payment:
    - payment/
    - order/
  profile:
    - user/profile
    - account/
```

阈值控制：`MAX_AFFECTED_MODULES_FULL_REGRESSION`（.env 配置，默认 3）。

### 阶段2：环境与数据准备（5 分钟）

1. 调用 **env-manager**：完整健康检查
2. 调用 **data-preparer**：
   - 创建回归测试专用数据集（`workspace/测试数据/test_data.json`）
   - 初始化数据库基线状态
   - 数据库快照（可选，仅白名单表）

### 阶段3：全量用例执行（P0+P1，60 分钟）

```bash
# cov 指向被测系统源码，不指向测试脚本本身
APP_SRC="${APP_SRC_PATH:-./src}"

pytest workspace/自动化脚本/python/ \
    -v -m "p0 or p1" \
    -n 4 --timeout=120 \
    --reruns=2 --reruns-delay=5 \
    --cov="${APP_SRC}" \
    --cov-report=html:workspace/执行日志/coverage-report \
    --cov-report=xml:workspace/执行日志/coverage.xml \
    --cov-fail-under=80 \
    --alluredir=workspace/执行日志/regression-allure-results \
    --junitxml=workspace/执行日志/regression-results.xml \
    --tb=short -q
```

> reruns 启用：开发反馈速度优先；flaky 由 history 离线归档检测，不被 reruns 隐藏（归档保留每次的失败/通过状态）。

### 阶段4：Flaky 检测（5 分钟）

实现委托 `utils/flaky_detector.py`：

```bash
# 归档当前 junit-xml 到 history
python -m utils.flaky_detector \
    --archive workspace/执行日志/regression-results.xml \
    --history workspace/执行日志/history \
    --limit 5
# 输出 flaky 候选清单（JSON）：
# [{"test_id": "...", "fail_rate_pct": 40.0, "history": ["passed","failed",...], "action": "quarantine"}]
```

阈值：`fail_rate_pct > 30%` → quarantine（标记 @pytest.mark.flaky 隔离）。

### 阶段5：历史结果对比（5 分钟）

通用对比逻辑（功能层）：

```python
# 简易对比：从 history 中读取上次 junit + 当前 junit，diff 失败用例
from utils.ci_quality_gate import parse_junit
from pathlib import Path

current = parse_junit("workspace/执行日志/regression-results.xml")
history_files = sorted(Path("workspace/执行日志/history").glob("*.xml"))[-2:-1]
if history_files:
    previous = parse_junit(str(history_files[0]))
    print(f"通过率变化: {current['pass_rate_pct'] - previous['pass_rate_pct']:+.1f} pct")
```

> 性能回归对比统一在阶段 5b（JMeter 路径），不在功能阶段重复实现。

### 阶段5b：JMeter 性能测试（15 分钟）

> **前置条件**：阶段 3 功能回归通过（P0=100% / 整体≥90%）。

```bash
# 模式：CI 默认 ci_quick；release/手动 full
PERF_MODE="${PERF_MODE:-ci_quick}"

if [ "$PERF_MODE" = "full" ]; then
    THREADS=50; RAMPUP=60; DURATION=300
else
    THREADS=5;  RAMPUP=10; DURATION=60
fi

jmeter -n \
    -t workspace/自动化脚本/jmeter/test_plan.jmx \
    -l workspace/执行日志/jmeter-results/regression_perf.jtl \
    -e -o workspace/执行日志/jmeter-report/ \
    -Jtarget_host="${TARGET_HOST}" \
    -Jtarget_protocol="${TARGET_PROTOCOL:-http}" \
    -Jtarget_port="${TARGET_PORT:-80}" \
    -Jthreads=${THREADS} -Jrampup=${RAMPUP} -Jduration=${DURATION}

# 性能门禁 + 基线对比
python -m utils.jmeter_result_parser \
    workspace/执行日志/jmeter-results/regression_perf.jtl \
    --mode "${PERF_MODE}" \
    --baseline workspace/执行日志/baselines/perf_baseline.json \
    --regression-max-pct 20
```

基线更新策略：仅 release 分支 + full 模式 + 全 PASS → `--update-baseline`。

### 阶段6：回归报告生成（5 分钟）

调用 **report-generator** 生成回归测试报告：

- 通过率趋势图（从 history 近 5 次）
- 新增失败用例列表
- 修复用例列表
- 性能对比数据（current vs baseline）
- Flaky 测试清单
- 上线建议

## ✅ 通过标准（Gate）

### 功能质量门禁

| 指标 | 要求 |
|------|------|
| P0 通过率 | = 100% |
| P1 通过率 | ≥ 95% |
| 总体通过率 | ≥ 90% |
| 代码覆盖率（$APP_SRC_PATH） | ≥ 80% |
| Flaky 比例 | < 5% |

### 性能质量门禁（双模式）

| 指标 | full（50并发） | ci_quick（5并发） |
|------|--------------|------------------|
| TPS | ≥100 | ≥20 |
| P95 响应 | ≤500ms | ≤800ms |
| 平均响应 | ≤200ms | ≤400ms |
| 错误率 (pct) | <1% | <1% |
| 基线回归 | <20% | 不强制 |
