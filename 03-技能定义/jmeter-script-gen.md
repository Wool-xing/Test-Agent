---
name: jmeter-script-gen
description: JMeter 性能脚本生成技能。输入接口信息或业务流程描述，生成可直接运行的 JMeter JMX 测试计划，支持接口压测/业务流程并发/阶梯加压三种模式。数据由 data-preparer 提供 CSV，结果输出给 test-executor / report-generator / bug-manager。
tools: Read, Write, Edit, Grep, Glob
---

# JMeter 性能脚本生成

## 触发方式

```
/jmeter-script-gen [接口信息 或 业务流程描述]
```

## 数据流（与其他 Agent 闭环）

```
data-preparer
  → workspace/测试数据/jmeter_users.csv（参数化数据，由 utils/jmeter_csv_exporter）
       ↓
automation-engineer（执行本技能生成 JMX）
  → workspace/自动化脚本/jmeter/test_plan.jmx
       ↓
test-executor
  → 执行 jmeter -n，输出 result.jtl + 性能指标 JSON
       ↓
       ├─→ report-generator     : HTML 报告 + 通知
       └─→ bug-manager          : 性能 Bug 工单（TPS低 / P95超限 / 错误率高）
```

## 执行流程

### Step 1：分析性能需求

从需求 JSON 摘要 `requirements_summary_*.json` 的 `performance_requirements` 字段提取：
- 目标接口列表（URL / Method / Header / Body）
- 性能目标（目标 TPS / 响应时间上限 / 并发用户数）
- 测试模式（接口级压测 / 业务流程并发 / 阶梯加压）

### Step 2：调用 data-preparer 准备 CSV

```python
from utils.jmeter_csv_exporter import generate_jmeter_dataset

generate_jmeter_dataset(count=50, output_path="workspace/测试数据/jmeter_users.csv")
```

CSV 格式：

```csv
username,password,user_id
test_user_a3f2,Test@123456,xxxx-xxxx-xxxx-xxxx
test_user_b9k7,Test@123456,xxxx-xxxx-xxxx-xxxx
```

### Step 3：生成 JMX 测试计划

#### 关键变量（命令行 -J 注入）

| 变量 | 含义 | 默认 |
|------|------|------|
| `target_host` | 目标主机（**不含协议前缀**） | test-api.example.com |
| `target_protocol` | http / https | http |
| `target_port` | 端口 | 80 |
| `threads` | 并发数 | 5 |
| `rampup` | 启动时间（秒） | 10 |
| `duration` | 持续时间（秒） | 60 |

#### 模板A：标准接口压测（最常用）

```xml
<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.6.3">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan"
              testname="接口性能测试计划" enabled="true">
      <elementProp name="TestPlan.user_defined_variables" elementType="Arguments">
        <collectionProp name="Arguments.arguments">
          <elementProp name="TARGET_HOST" elementType="Argument">
            <stringProp name="Argument.name">TARGET_HOST</stringProp>
            <stringProp name="Argument.value">${__P(target_host,test-api.example.com)}</stringProp>
          </elementProp>
          <elementProp name="TARGET_PROTOCOL" elementType="Argument">
            <stringProp name="Argument.name">TARGET_PROTOCOL</stringProp>
            <stringProp name="Argument.value">${__P(target_protocol,http)}</stringProp>
          </elementProp>
          <elementProp name="TARGET_PORT" elementType="Argument">
            <stringProp name="Argument.name">TARGET_PORT</stringProp>
            <stringProp name="Argument.value">${__P(target_port,80)}</stringProp>
          </elementProp>
          <elementProp name="THREADS" elementType="Argument">
            <stringProp name="Argument.name">THREADS</stringProp>
            <stringProp name="Argument.value">${__P(threads,5)}</stringProp>
          </elementProp>
          <elementProp name="RAMPUP" elementType="Argument">
            <stringProp name="Argument.name">RAMPUP</stringProp>
            <stringProp name="Argument.value">${__P(rampup,10)}</stringProp>
          </elementProp>
          <elementProp name="DURATION" elementType="Argument">
            <stringProp name="Argument.name">DURATION</stringProp>
            <stringProp name="Argument.value">${__P(duration,60)}</stringProp>
          </elementProp>
        </collectionProp>
      </elementProp>
    </TestPlan>
    <hashTree>

      <!-- CSV 参数化（数据由 data-preparer 生成） -->
      <CSVDataSet guiclass="TestBeanGUI" testclass="CSVDataSet"
                  testname="参数化数据_CSV" enabled="true">
        <stringProp name="filename">workspace/测试数据/jmeter_users.csv</stringProp>
        <stringProp name="variableNames">username,password,user_id</stringProp>
        <stringProp name="delimiter">,</stringProp>
        <boolProp name="quotedData">false</boolProp>
        <boolProp name="recycle">true</boolProp>
        <boolProp name="stopThread">false</boolProp>
        <stringProp name="shareMode">shareMode.all</stringProp>
      </CSVDataSet>
      <hashTree/>

      <!-- HTTP 默认值（host/port/protocol 全变量化）-->
      <ConfigTestElement guiclass="HttpDefaultsGui" testclass="ConfigTestElement"
                         testname="HTTP请求默认值" enabled="true">
        <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
          <collectionProp name="Arguments.arguments"/>
        </elementProp>
        <stringProp name="HTTPSampler.domain">${TARGET_HOST}</stringProp>
        <stringProp name="HTTPSampler.port">${TARGET_PORT}</stringProp>
        <stringProp name="HTTPSampler.protocol">${TARGET_PROTOCOL}</stringProp>
        <stringProp name="HTTPSampler.contentEncoding">UTF-8</stringProp>
      </ConfigTestElement>
      <hashTree/>

      <!-- 全局 Header -->
      <HeaderManager guiclass="HeaderPanel" testclass="HeaderManager"
                     testname="全局请求头" enabled="true">
        <collectionProp name="HeaderManager.headers">
          <elementProp name="" elementType="Header">
            <stringProp name="Header.name">Content-Type</stringProp>
            <stringProp name="Header.value">application/json</stringProp>
          </elementProp>
        </collectionProp>
      </HeaderManager>
      <hashTree/>

      <!-- 线程组 -->
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup"
                   testname="并发用户组" enabled="true">
        <intProp name="ThreadGroup.num_threads">${THREADS}</intProp>
        <intProp name="ThreadGroup.ramp_time">${RAMPUP}</intProp>
        <longProp name="ThreadGroup.duration">${DURATION}</longProp>
        <longProp name="ThreadGroup.delay">0</longProp>
        <boolProp name="ThreadGroup.scheduler">true</boolProp>
        <stringProp name="ThreadGroup.on_sample_error">continue</stringProp>
      </ThreadGroup>
      <hashTree>

        <!-- Step 1: 登录获取 Token -->
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy"
                          testname="01_登录获取Token" enabled="true">
          <stringProp name="HTTPSampler.path">/api/v1/auth/login</stringProp>
          <stringProp name="HTTPSampler.method">POST</stringProp>
          <boolProp name="HTTPSampler.use_keepalive">true</boolProp>
          <boolProp name="HTTPSampler.postBodyRaw">true</boolProp>
          <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
            <collectionProp name="Arguments.arguments">
              <elementProp name="" elementType="HTTPArgument">
                <boolProp name="HTTPArgument.always_encode">false</boolProp>
                <stringProp name="Argument.value">{"username":"${username}","password":"${password}"}</stringProp>
                <stringProp name="Argument.metadata">=</stringProp>
              </elementProp>
            </collectionProp>
          </elementProp>
        </HTTPSamplerProxy>
        <hashTree>
          <!-- 提取 Token（JMeter 5.x 用 JSONPostProcessor） -->
          <JSONPostProcessor guiclass="JSONPostProcessorGui" testclass="JSONPostProcessor"
                             testname="提取Token" enabled="true">
            <stringProp name="JSONPostProcessor.referenceNames">access_token</stringProp>
            <stringProp name="JSONPostProcessor.jsonPathExprs">$.token</stringProp>
            <stringProp name="JSONPostProcessor.defaultValues">TOKEN_NOT_FOUND</stringProp>
          </JSONPostProcessor>
          <hashTree/>
          <!-- 登录响应断言 -->
          <ResponseAssertion guiclass="AssertionGui" testclass="ResponseAssertion"
                             testname="登录响应断言" enabled="true">
            <collectionProp name="Asserion.test_strings">
              <stringProp name="49586">200</stringProp>
            </collectionProp>
            <stringProp name="Assertion.test_field">Assertion.response_code</stringProp>
            <intProp name="Assertion.test_type">8</intProp>
          </ResponseAssertion>
          <hashTree/>
          <!-- 登录失败时中止当前线程（防止后续 401 雪崩） -->
          <IfController guiclass="IfControllerPanel" testclass="IfController"
                        testname="If 登录成功" enabled="true">
            <stringProp name="IfController.condition">"${access_token}" != "TOKEN_NOT_FOUND"</stringProp>
            <boolProp name="IfController.evaluateAll">false</boolProp>
            <boolProp name="IfController.useExpression">true</boolProp>
          </IfController>
          <hashTree/>
        </hashTree>

        <!-- Step 2: 核心业务接口（仅在登录成功时执行） -->
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy"
                          testname="02_核心业务接口" enabled="true">
          <stringProp name="HTTPSampler.path">/api/v1/home</stringProp>
          <stringProp name="HTTPSampler.method">GET</stringProp>
          <boolProp name="HTTPSampler.use_keepalive">true</boolProp>
          <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
            <collectionProp name="Arguments.arguments"/>
          </elementProp>
        </HTTPSamplerProxy>
        <hashTree>
          <HeaderManager guiclass="HeaderPanel" testclass="HeaderManager"
                         testname="认证Header" enabled="true">
            <collectionProp name="HeaderManager.headers">
              <elementProp name="" elementType="Header">
                <stringProp name="Header.name">Authorization</stringProp>
                <stringProp name="Header.value">Bearer ${access_token}</stringProp>
              </elementProp>
            </collectionProp>
          </HeaderManager>
          <hashTree/>
          <ResponseAssertion guiclass="AssertionGui" testclass="ResponseAssertion"
                             testname="业务响应断言" enabled="true">
            <collectionProp name="Asserion.test_strings">
              <stringProp name="49586">200</stringProp>
            </collectionProp>
            <stringProp name="Assertion.test_field">Assertion.response_code</stringProp>
            <intProp name="Assertion.test_type">8</intProp>
          </ResponseAssertion>
          <hashTree/>
        </hashTree>

        <!-- 结果收集 -->
        <ResultCollector guiclass="StatVisualizer" testclass="ResultCollector"
                         testname="聚合报告" enabled="true">
          <boolProp name="ResultCollector.error_logging">false</boolProp>
          <objProp>
            <name>saveConfig</name>
            <value class="SampleSaveConfiguration">
              <time>true</time><latency>true</latency><timestamp>true</timestamp>
              <success>true</success><label>true</label><code>true</code>
              <responseMessage>true</responseMessage><threadName>true</threadName>
              <dataType>true</dataType><encoding>false</encoding>
              <assertions>true</assertions><subresults>true</subresults>
              <responseData>false</responseData><samplerData>false</samplerData>
              <xml>false</xml><fieldNames>true</fieldNames>
              <responseHeaders>false</responseHeaders><requestHeaders>false</requestHeaders>
              <responseDataOnError>false</responseDataOnError>
              <saveAssertionResultsFailureMessage>true</saveAssertionResultsFailureMessage>
              <bytes>true</bytes><sentBytes>true</sentBytes>
              <url>true</url><threadCounts>true</threadCounts>
              <idleTime>true</idleTime><connectTime>true</connectTime>
            </value>
          </objProp>
          <stringProp name="filename">workspace/执行日志/jmeter-results/result.jtl</stringProp>
        </ResultCollector>
        <hashTree/>

      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
```

#### 模板B：阶梯加压（10 → 50 → 100 用户）

用三个串行 ThreadGroup 模拟阶梯：

```xml
<!-- 阶梯1：10 用户 / 30s 加压 / 持续 120s -->
<ThreadGroup testname="Step1_10用户" enabled="true">
  <intProp name="ThreadGroup.num_threads">10</intProp>
  <intProp name="ThreadGroup.ramp_time">30</intProp>
  <longProp name="ThreadGroup.duration">120</longProp>
  <boolProp name="ThreadGroup.scheduler">true</boolProp>
</ThreadGroup>

<!-- 阶梯2：50 用户 -->
<ThreadGroup testname="Step2_50用户" enabled="true">
  <intProp name="ThreadGroup.num_threads">50</intProp>
  <intProp name="ThreadGroup.ramp_time">60</intProp>
  <longProp name="ThreadGroup.duration">120</longProp>
  <boolProp name="ThreadGroup.scheduler">true</boolProp>
  <longProp name="ThreadGroup.delay">120</longProp>
</ThreadGroup>

<!-- 阶梯3：100 用户 -->
<ThreadGroup testname="Step3_100用户" enabled="true">
  <intProp name="ThreadGroup.num_threads">100</intProp>
  <intProp name="ThreadGroup.ramp_time">60</intProp>
  <longProp name="ThreadGroup.duration">120</longProp>
  <boolProp name="ThreadGroup.scheduler">true</boolProp>
  <longProp name="ThreadGroup.delay">240</longProp>
</ThreadGroup>
```

## 执行命令

```bash
# CI 默认：ci_quick
jmeter -n \
  -t workspace/自动化脚本/jmeter/test_plan.jmx \
  -l workspace/执行日志/jmeter-results/result.jtl \
  -e -o workspace/执行日志/jmeter-report/ \
  -Jtarget_host="${TARGET_HOST}" \
  -Jtarget_protocol="${TARGET_PROTOCOL:-http}" \
  -Jtarget_port="${TARGET_PORT:-80}" \
  -Jthreads=5 -Jrampup=10 -Jduration=60

# 完整压测：full（手动 / release）
jmeter -n \
  -t workspace/自动化脚本/jmeter/test_plan.jmx \
  -l workspace/执行日志/jmeter-results/result.jtl \
  -e -o workspace/执行日志/jmeter-report/ \
  -Jtarget_host="${TARGET_HOST}" \
  -Jtarget_protocol="${TARGET_PROTOCOL:-http}" \
  -Jtarget_port="${TARGET_PORT:-80}" \
  -Jthreads=50 -Jrampup=60 -Jduration=300

# 阶梯加压
jmeter -n \
  -t workspace/自动化脚本/jmeter/stepped_load.jmx \
  -l workspace/执行日志/jmeter-results/stepped_result.jtl \
  -Jtarget_host="${TARGET_HOST}"
```

> 部署前 .env 中需解析 TEST_API_URL → TARGET_HOST/PROTOCOL/PORT。可用 conftest 或独立脚本完成。

## 性能质量门禁（双模式）

| 指标 | full（50并发） | ci_quick（5并发） | 不达标处置 |
|------|--------------|------------------|---------|
| TPS | ≥100 | ≥20 | 性能 Bug → bug-manager |
| P95 响应 | ≤500ms | ≤800ms | 性能 Bug，标注慢接口 |
| 平均响应 | ≤200ms | ≤400ms | 告警 + 性能分析 |
| 错误率 (pct) | <1% | <1% | 查日志 + 阻断发布 |
| 基线回归 | <20% | 不强制 | 告警 + 排查 |

## JTL 解析与门禁（实现位于 utils/jmeter_result_parser.py）

```bash
# CI quick
python -m utils.jmeter_result_parser \
    workspace/执行日志/jmeter-results/result.jtl \
    --mode ci_quick

# Full + 基线对比 + 通过则更新基线
python -m utils.jmeter_result_parser \
    workspace/执行日志/jmeter-results/result.jtl \
    --mode full \
    --baseline workspace/执行日志/baselines/perf_baseline.json \
    --update-baseline
```

## 向 report-generator 输出格式

```json
{
  "type": "performance",
  "tool": "JMeter 5.6.3",
  "executed_at": "2026-05-10T15:00:00",
  "mode": "ci_quick",
  "jmx_file": "workspace/自动化脚本/jmeter/test_plan.jmx",
  "metrics": {
    "total_requests": 15000,
    "tps": 102.5,
    "avg_response_ms": 145,
    "p95_response_ms": 420,
    "p99_response_ms": 680,
    "error_rate_pct": 0.12
  },
  "quality_gate": {
    "overall": "PASS",
    "checks": {
      "tps":   {"actual": 102.5, "required": "≥100", "pass": true},
      "p95":   {"actual": 420,   "required": "≤500ms", "pass": true},
      "avg":   {"actual": 145,   "required": "≤200ms", "pass": true},
      "error": {"actual_pct": 0.12, "required": "<1%", "pass": true}
    }
  },
  "baseline": {
    "baseline_exists": true,
    "regression_pct": 3.2,
    "is_regression": false
  },
  "html_report": "workspace/执行日志/jmeter-report/index.html",
  "jtl_file": "workspace/执行日志/jmeter-results/result.jtl"
}
```

## 输出文件结构

```
workspace/自动化脚本/jmeter/
├── test_plan.jmx              # 标准接口压测计划
├── business_flow.jmx          # 业务流程并发计划（按需）
└── stepped_load.jmx           # 阶梯加压计划

workspace/测试数据/
└── jmeter_users.csv           # 参数化数据（data-preparer 生成）

workspace/执行日志/
├── jmeter-results/result.jtl  # 原始结果（CSV）
├── jmeter-report/index.html   # JMeter HTML 可视化
└── baselines/perf_baseline.json
```

## 代码质量要求

```
✅ JMX 中 host/protocol/port 全变量化（${TARGET_HOST/PROTOCOL/PORT}）
✅ TARGET_HOST 不含协议前缀
✅ CSV 由 data-preparer 生成，不在 JMX 中手写数据
✅ 每个请求必须有响应断言（防静默失败）
✅ JSONPostProcessor 提取 Token（不用旧名 JSONPathExtractor）
✅ 登录失败时 If Controller 中止后续请求
✅ 结果保存到 workspace/执行日志/jmeter-results/
✅ 解析与门禁统一调 utils/jmeter_result_parser.py
✅ 性能 Bug 提交给 bug-manager（标题：[性能]-[接口名]-[指标超标]）
```
