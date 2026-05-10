# CI/CD 集成说明

## 概述

本项目提供 GitHub Actions 和 Jenkins 两种 CI/CD 集成方案，均支持：

- 三级测试（冒烟 / 回归 / 全量）+ JMeter 性能阶段
- 并行执行加速
- 质量门禁分层（统一调用 `utils/ci_quality_gate.py` 与 `utils/jmeter_result_parser.py`）
- Allure 测试报告
- 三端通知（企业微信 / 飞书 / 钉钉，curl 直连 webhook，**未启用 MCP 通道**）

> 通知与 Bug 提交均走直连 SDK/webhook（参见 `utils/generate_report.send_*` / `utils/zentao_bug_manager.py`）。`.mcp.json` 仅启用 filesystem。

---

## GitHub Actions 集成

### 文件位置

部署脚本会自动放到：

```
your-test-project/.github/workflows/test.yml
```

### 触发条件

| 触发事件 | 默认测试级别 | 性能模式 |
|---------|-----------|---------|
| push 到 main / develop | regression | ci_quick |
| push 到 release/* | regression | full |
| PR 到 main / develop | smoke（仅冒烟） | 不执行 |
| 手动触发（workflow_dispatch） | 用户选择 | 用户选择 |

### 必须配置的 Secrets

在 GitHub 仓库 → Settings → Secrets and variables → Actions：

```
# 应用与数据库
TEST_APP_URL              # 应用 URL（如 http://test.example.com）
TEST_API_URL              # API URL（如 http://test-api.example.com）
TEST_DB_HOST              # 数据库主机
TEST_DB_PORT              # 数据库端口
TEST_DB_USER              # 数据库账号
TEST_DB_PASSWORD          # 数据库密码

# Staging（如需要 staging 流水线）
STAGING_APP_URL
STAGING_API_URL
STAGING_DB_HOST
STAGING_DB_PASSWORD

# 测试账号
TEST_USER
TEST_PASS
ADMIN_USER
ADMIN_PASS

# 性能压测账号
PERF_TEST_USER
PERF_TEST_PASS

# Mock 服务（可选）
MOCK_SERVER_URL

# 禅道
ZENTAO_BASE_URL
ZENTAO_ACCOUNT
ZENTAO_PASSWORD

# 通知（可选，未配置则跳过）
WECHAT_WEBHOOK_URL
FEISHU_WEBHOOK
DINGTALK_WEBHOOK

# 覆盖率（可选）
CODECOV_TOKEN             # 私库需要

# 被测系统源码路径（覆盖率指向）
APP_SRC_PATH              # 默认 ./src
```

> Secrets 在 if 表达式中**不能直接引用**。yml 中通过 `outputs` 中转或 `if: env.X != ''` 模式判断。

### Allure 报告发布

报告自动发布到 GitHub Pages（需要开启）：

1. Settings → Pages → Source 选择 `gh-pages` 分支
2. main 分支 push 后报告自动更新
3. 访问：`https://{username}.github.io/{repo}/`

---

## Jenkins 集成

### 环境要求

| 组件 | 版本 |
|------|------|
| Jenkins | 2.400+ |
| Python | 3.11+ |
| Docker | 20.10+（推荐，使用容器化环境） |
| Allure Jenkins 插件 | 2.29+ |

### 安装 Jenkins 插件

- `Allure Jenkins Plugin`
- `AnsiColor Plugin`
- `HTML Publisher Plugin`
- `JUnit Plugin`
- `Docker Pipeline`
- `Pipeline: Stage Step`
- `Timestamper`

### 配置 Credentials

Manage Jenkins → Credentials → 添加以下 Secret text：

```
TEST_APP_URL
TEST_API_URL
TEST_DB_HOST
TEST_DB_PASSWORD
TEST_USER / TEST_PASS / ADMIN_USER / ADMIN_PASS
PERF_TEST_USER / PERF_TEST_PASS
MOCK_SERVER_URL（可选）
ZENTAO_BASE_URL / ZENTAO_ACCOUNT / ZENTAO_PASSWORD
WECHAT_WEBHOOK_URL / FEISHU_WEBHOOK / DINGTALK_WEBHOOK（可选）
APP_SRC_PATH
```

### 创建 Pipeline

1. 新建 Pipeline 任务
2. Pipeline → Definition 选择 `Pipeline script from SCM`
3. SCM 选 Git，填入仓库地址
4. Script Path：`Jenkinsfile`（部署脚本会拷到项目根）
5. 保存并触发构建

---

## 质量门禁标准（分层）

质量门禁内联到 `utils/ci_quality_gate.py` 与 `utils/jmeter_result_parser.py`，CI 直接调用，避免重复实现。

### 功能门禁

| 指标 | 冒烟 | 回归 | 不达标处置 |
|------|------|------|---------|
| P0 通过率 | ≥95% | 100% | 停止 / 等待修复 |
| P1 通过率 | - | ≥95% | 记录遗留风险 |
| 整体通过率 | - | ≥90% | 评估风险 |
| 代码覆盖率（$APP_SRC_PATH） | - | ≥80% | 补充用例 |
| 新增 P0 Bug | 0 | 0 | 阻断发布 |
| Flaky 比例 | - | <5% | 隔离 + 分析 |

### 性能门禁（双模式）

| 指标 | full（50并发） | ci_quick（5并发） | 不达标处置 |
|------|--------------|------------------|---------|
| TPS | ≥100 | ≥20 | 性能 Bug |
| P95 响应 | ≤500ms | ≤800ms | 慢接口分析 |
| 平均响应 | ≤200ms | ≤400ms | 告警 |
| 错误率 (pct) | <1% | <1% | 阻断发布 |
| 基线回归 | <20% | 不强制 | 告警 + 排查 |

门禁失败时：

- GitHub Actions：工作流标记为失败，PR 无法合并
- Jenkins：构建状态变为 FAILURE，不触发部署

---

## 测试报告说明

### Allure 报告

```bash
# 本地查看
allure serve workspace/执行日志/allure-results

# 生成静态报告
allure generate workspace/执行日志/allure-results \
    --output workspace/执行日志/allure-report --clean
```

### 报告目录结构

```
workspace/执行日志/
├── allure-results/                # Allure 原始数据
├── allure-report/                 # Allure 静态 HTML
├── jmeter-results/result.jtl      # JMeter 原始结果
├── jmeter-report/index.html       # JMeter HTML 可视化
├── coverage.xml                   # 覆盖率 XML（Cobertura，供 Codecov）
├── coverage-report/               # 覆盖率 HTML
├── baselines/perf_baseline.json   # 性能基线
├── history/                       # junit-xml 归档（flaky_detector 用）
├── 截图/                          # UI 失败截图
├── 报告/测试报告_{日期}.docx       # Word 报告
├── pytest.log                     # 详细执行日志
├── smoke-results.xml              # 冒烟 junit
├── regression-results.xml         # 回归 junit
└── 环境检查_{时间戳}.json
```

### 通知方式

CI 通过 curl 调 webhook 直接发送，未走 MCP（与全栈一致）。

通知内容示例：
```
✅ 测试通过 | 构建#42 | 级别:regression | 模式:ci_quick | 查看报告
❌ 测试失败 | 构建#43 | 级别:smoke    | 查看报告
```

如需启用 MCP 通道（zentao / wechat / feishu / dingtalk mcp_server），自行实现对应模块后追加 `.mcp.json`（参见 `.mcp.json` `_comment` 字段）。

---

## 常见问题

**Q: Playwright 在 Docker 中无法运行？**
A: `playwright install chromium --with-deps` 自动安装系统依赖。Docker image 建议 `python:3.11`（非 slim）。slim 镜像缺 wget/tar/字体等系统依赖，需先 `apt-get install -y wget tar libnss3 libatk1.0-0 ...`。

**Q: 并行测试时 fixture 冲突？**
A: 使用 `scope="function"` fixture，或为每个 worker 创建独立数据库连接 / 测试账号。

**Q: GitHub Actions 超时？**
A: 调整 `timeout-minutes` 或减少并行进程数（`-n` 参数）。冒烟 15min / 回归 90min / 性能 20min 是默认上限。

**Q: Allure 报告无法显示？**
A: 检查 `gh-pages` 分支权限。Settings → Actions → General → Workflow permissions 选 `Read and write permissions`。

**Q: JMeter 5.6.3 下载失败（404）？**
A: Apache 官方镜像只保留最新若干版本。yml/groovy 默认使用 `archive.apache.org/dist/jmeter/binaries/` 兜底链接。

**Q: Codecov 401 错误？**
A: 私有仓库需配置 `CODECOV_TOKEN` Secret。公开仓库可不配。

**Q: secrets 在 if 表达式中报错 / 永远 false？**
A: GitHub Actions 不允许 `if: secrets.X != ''`。yml 已用 outputs 中转模式：先 `set output webhook_present=true/false`，后续 step `if: needs.X.outputs.webhook_present == 'true'`。

**Q: Jenkins `currentBuild.currentResult` 在 stage when 中不可靠？**
A: yml 改用 environment flag（`env.STAGE_X_OK = 'true'`），后续 stage `when { expression { return env.STAGE_X_OK == 'true' } }`。

**Q: GitLab CI 集成？**
A: 当前未提供 .gitlab-ci.yml 模板。可参考 yml 改写：触发 → 安装 → pytest → utils.ci_quality_gate → JMeter → utils.jmeter_result_parser → Allure。后续按需添加。
