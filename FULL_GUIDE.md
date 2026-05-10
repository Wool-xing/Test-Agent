# Test-Agent 完整指南（FULL_GUIDE）

> **本文档定位**：完整详细指南（架构 / 三视角矩阵 / 技术栈深度 / 闭环约定 / 跨工具兼容）。
> 简明入口 → [README.md](README.md) ；按职责分类速查 → [00-项目导航.md](00-项目导航.md)。

**项目代号**：`test-agent-team`（全英文）
**项目目录名**：`Test-Agent`（中文别名 `Test-Agent工作流搭建`）
**版本**：V1.0.0（详见 [VERSION](VERSION) + [CHANGELOG.md](CHANGELOG.md)）
**更新日期**：2026-05-11
**模型**：Claude 4.x 系列（Opus 4.7 / Sonnet 4.6 / Haiku 4.5，由 Claude Code 默认管理）

---

## 📚 文档导航

| 路径 | 文档 | 说明 | 适用对象 |
|------|------|------|----------|
| 根目录 | README.md | 简明入口（≤ 200 行） | 所有用户 |
| **根目录** | **00-项目导航.md** | **按职责分类速查（通用流程 / 平台专项 / 协议 / 输入 / CI）** | **所有用户** |
| `01-快速开始/` | 使用手册.md | 快速上手指南 + FAQ | 所有用户 |
| `01-快速开始/` | 部署说明.md | 跨平台部署（Win/Mac/Linux 含 Java/JMeter/Allure） | 运维/测试 |
| `01-快速开始/` | 配置清单.md | 一站式配置文档（.env 全字段 + Secrets + Webhook 申请） | 所有用户 |
| `01-快速开始/` | 交付物清单.md | 测试计划 / 测试报告 / Bug 等对外提交物落地位置与责任 | 所有用户 |
| `02-专家定义/` | 14 个 .md（9 核心 + 5 平台扩展） + README 索引 | Agent 定义文件 | 开发人员 |
| `03-技能定义/` | 13 个 Skill 文件 + README 索引 | 可复用测试技能 | 开发人员 |
| `04-配置文件/` | conftest.py / pytest.ini / .env.example / .mcp.json / requirements.txt | 配置文件集合 | 开发人员 |
| `04-配置文件/` | mcp-server-impl.md | MCP server 自实现教程（zentao/wechat/feishu/dingtalk 骨架） | 高级开发 |
| `05-代码示例/` | utils（49 个 .py + init）+ README 索引（多分类） | 完整可运行 Python 工具集 | 开发人员 |
| `06-CICD集成/` | github-actions-test.yml / jenkins-pipeline.groovy / 集成说明.md | CI/CD 流水线（含 JMeter 性能阶段） | DevOps |

---

## 🚀 核心特性

### 13 位专家 + 1 位协调者（核心 8 + 平台扩展 5 + test-lead）

| 角色 | 职责 |
|------|------|
| **test-lead**（协调者） | 全局调度、质量把控、发布决策、基线管理 |
| requirements-analyst | 测试范围界定、风险识别、业务规则梳理（输出 MD + JSON 摘要） |
| testcase-designer | 等价类/边界值/场景法，P0~P3 分级，4 Sheet Excel |
| env-manager | 环境健康检查、多环境切换、Docker 支持 |
| data-preparer | 数据工厂（Faker+Factory Boy）、自动清理、脱敏、JMeter CSV |
| automation-engineer | Playwright（UI）+ requests（API）+ JMeter 驱动（性能）+ Locust（开发期备用） |
| test-executor | 并行执行、失败分类、Flaky 隔离、JMeter 性能阶段 |
| bug-manager | 禅道提交（severity 1=P0）、生命周期追踪、回归验证 |
| report-generator | Allure + JMeter HTML + Word + 三端通知（企微/飞书/钉钉，curl 直连） |

### 13 个执行技能

**核心 8 个**：

- `smoke-test`：10 分钟 P0 冒烟（含 1 分钟缓冲，门禁 95%）
- `test-coordinator`：完整流程编排
- `regression-test`：P0+P1 回归 + Flaky 检测 + JMeter 性能验证
- `testcase-design`：4 Sheet Excel 用例
- `python-script-gen`：pytest UI/API 脚本
- `jmeter-script-gen`：JMeter JMX 脚本（CI quick / full 双模式）
- `data-preparation`：测试数据 + JMeter 参数化 CSV
- `zentao-bug-submission`：禅道 Bug 规范提交

**平台扩展 5 个**：

- `mobile-test`：Android / iOS / 微信小程序（Appium + 微信 CLI）
- `desktop-test`：Windows EXE / macOS GUI / Electron（pywinauto + Playwright Electron）
- `visual-test`：游戏 / 视觉回归 / OCR（Airtest + OpenCV + Tesseract）
- `system-test`：IoT / 音视频 / 链路追踪 / MQ（SSH+串口+MQTT+FFmpeg+Jaeger+Kafka）
- `ai-test`：模型质量 / 数据漂移 / 公平性 / LLM 评估

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
- **Flaky 检测与隔离**：`utils/flaky_detector` + `workspace/执行日志/history/` 归档
- **性能基线管理**：`workspace/执行日志/baselines/perf_baseline.json`，仅 release+full+PASS 自动更新
- **CI/CD 就绪**：GitHub Actions + Jenkins，性能阶段双模式分层
- **MCP 收口**：当前仅启用 filesystem；通知/Bug 走 SDK 直连

---

## 🌐 全链路覆盖矩阵（三视角）

### 矩阵 A：产品形态覆盖

| 产品形态 | 工具栈 | 责任 Agent | 关联 Skill | 状态 |
|---------|-------|-----------|----------|------|
| Web（PC + 移动 H5） | Playwright | automation-engineer | `/python-script-gen` | ✅ |
| REST / GraphQL / SOAP API | requests / protocol_helper | automation-engineer | `/python-script-gen` | ✅ |
| Android APP | Appium + adb | mobile-tester | `/mobile-test` | ✅ |
| iOS APP | Appium + XCUITest | mobile-tester | `/mobile-test` | ✅ |
| 微信 / 支付宝 / 抖音小程序 | 微信开发者工具 CLI | mobile-tester | `/mobile-test` | ✅ |
| Windows EXE | pywinauto + uiautomation | desktop-tester | `/desktop-test` | ✅ |
| macOS .app | PyAutoGUI + AppleScript | desktop-tester | `/desktop-test` | ✅ |
| Linux GUI | atspi + xdotool | desktop-tester | `/desktop-test` | ✅ |
| Electron 跨平台 | Playwright Electron API | desktop-tester | `/desktop-test` | ✅ |
| 游戏 / Canvas / WebGL / Unity | Airtest + OpenCV | visual-tester | `/visual-test` | ✅ |
| IoT / 嵌入式 | SSH + 串口 + MQTT + Modbus | system-tester | `/system-test` | ✅ |
| 音视频 / 流媒体 | FFmpeg + ffprobe | system-tester | `/system-test` | ✅ |
| AI / ML 模型 + LLM | scikit-learn + scipy + LLM eval | ai-tester | `/ai-test` | ✅ |
| 区块链 / 智能合约 | Web3 + Slither + Foundry | system-tester | `/system-test` | ✅ |
| 数据库 | SQLAlchemy + db_test_helper | data-preparer | `/data-preparation` | ✅ |

### 矩阵 B：测试类型覆盖

| 测试类型 | 工具 / utils | 责任 Agent | 状态 |
|---------|------------|-----------|------|
| 功能（unit / integration / e2e / UAT BDD） | pytest + pytest-mock + pytest-bdd | automation-engineer | ✅ |
| 性能（基准/负载/压力/Volume/Spike/Soak/SLO） | JMeter + Locust + slo_validator + soak_runner | test-executor | ✅ |
| 安全（SAST/DAST/依赖/Header/TLS/API/Fuzzing） | Bandit + Safety + ZAP + Burp Pro + api_security_scanner + fuzzer | bug-manager | ✅ |
| 兼容（浏览器/OS/分辨率/语言矩阵） | compatibility_matrix（pairwise） | testcase-designer | ✅ |
| 弱网（3G/4G/wifi_weak/satellite/offline） | tc + Toxiproxy + network_throttle | test-executor | ✅ |
| 稳定（Android Monkey + 长时 soak + 内存泄漏） | mobile_driver.run_monkey + soak_runner | mobile-tester | ✅ |
| 可靠性（重连/重试/降级/熔断） | api_retry_util + 业务故障注入 | automation-engineer | ✅ |
| 混沌（CPU/内存/磁盘/网络/进程/k8s） | chaos_helper | test-executor | ✅ |
| 灾备 / Failover | chaos_helper.kill_pod + 数据一致性校验 | test-executor | ✅ |
| UX（任务时长/点击数/TTI/恢复率） | ux_metrics.UXTracker | testcase-designer | ✅ |
| 易用性（Nielsen 10 + 角色扮演） | 人工 walkthrough | testcase-designer | ✅ |
| 探索性（SBTM session + heuristics） | charter 模板 + 录屏 | testcase-designer | ✅ |
| 前端性能 Web Vitals（LCP/FID/CLS/INP） | web_vitals_collector | automation-engineer | ✅ |
| A11y 无障碍（WCAG 2.1） | a11y_scanner（axe + Lighthouse + pa11y） | testcase-designer | ✅ |
| 国际化 / 本地化（多语言/RTL） | i18n_checker | testcase-designer | ✅ |
| 数据库（事务/死锁/迁移/备份恢复/主从） | db_test_helper | data-preparer | ✅ |
| 契约测试（Pact / jsonschema） | contract_test + openapi_test_gen | automation-engineer | ✅ |
| 视觉回归（SSIM + OCR + diff） | visual_helper | visual-tester | ✅ |
| AI 对抗 / LLM 越狱 / Prompt Injection | ai_adversarial | ai-tester | ✅ |
| 变异测试（用例有效性） | mutation_runner | testcase-designer | ✅ |
| DORA 4 指标 + 缺陷密度 + 套件减重 | dora_metrics + suite_minimizer | bug-manager | ✅ |

### 矩阵 C：用例设计方法（ISTQB 经典）

| 方法 | 实现 | 责任 Agent | 状态 |
|------|------|-----------|------|
| 等价类划分 / 边界值 | 文档 + Excel 模板 | testcase-designer | ✅ |
| 判定表 / 因果图 | 文档手动 + Excel | testcase-designer | ✅ |
| 场景法 / 错误推测 | 文档 | testcase-designer | ✅ |
| 状态迁移法（0/1-switch + 负例） | state_machine_tester | testcase-designer | ✅ |
| 配对测试（Allpairs） | pairwise_generator | testcase-designer | ✅ |
| 正交实验法 | compatibility_matrix（隐含） | testcase-designer | ✅ |
| 探索性测试（SBTM） | charter 模板 | testcase-designer | ✅ |
| 易用性走查（Nielsen 10） | 人工 + 检查清单 | testcase-designer | ✅ |
| 基于风险的测试 | 风险矩阵文档 | test-lead | ✅ |

### 矩阵 D：协议覆盖

| 协议 | 实现 utils | 状态 |
|------|----------|------|
| HTTP / HTTPS | api_retry_util | ✅ |
| WebSocket（同步/异步/重连/并发） | websocket_helper | ✅ |
| gRPC / TCP / UDP / GraphQL / SOAP / Modbus | protocol_helper | ✅ |
| MQTT / SSH / 串口 | iot_helper | ✅ |
| Kafka / RabbitMQ | mq_helper | ✅ |
| Jaeger / Zipkin（链路追踪） | tracing_validator | ✅ |

### 测试金字塔分布

```text
        E2E（10%）         ← Playwright/Appium，慢但必要
       /集成（20%）/        ← API + 服务间 + Mock
      /单元（70%）/         ← pytest + pytest-mock，秒级反馈
```

**总覆盖率 ~95%**（含闭环：Bug 禅道 + 三端通知 + CI/CD GitHub Actions/Jenkins + Dependabot）

剩 ~5% 为高度专业合规领域（HIPAA 医疗 / SOC2 金融 / DO-178C 航空 / IEC61508 工业控制）—— 业务方按需自加。

---

## 🏗️ 架构图（运行时）

```text
┌────────────────────────────────────────────────────────────────┐
│                     test-lead（协调者）                         │
│       全局调度 / 质量门禁 / 风险决策 / 基线管理                  │
└────────────────────────────────────────────────────────────────┘
            │
   ┌────────┴───────────────┐
   ↓                        ↓
[requirements-analyst]  [testcase-designer]
   │                        │
   └────────┬───────────────┘
            ↓
     [env-manager]  ──→ 串行（基础 connectivity 通过后）──→ [data-preparer]
            │                                              │
            └───────────────────┬──────────────────────────┘
                                ↓
                   [automation-engineer]
                    pytest 脚本 + /jmeter-script-gen → JMX
                                ↓
                           /smoke-test（门禁 95%）
                                ↓ 通过
                          [test-executor]
                          功能回归（P0+P1）
                                ↓ 通过
                          [test-executor]
                          JMeter 性能（ci_quick / full）
                                ↓
                           [bug-manager]
                                ↓
                          [report-generator]
                  Allure + JMeter HTML + Word + 三端通知
                                ↓
                        test-lead 最终决策
```

---

## ⚡ 快速开始

### 1. GitHub 一键部署（最快）

```bash
# Mac / Linux 一行远程部署
curl -fsSL https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.sh | bash -s -- /path/to/your-test-project

# 或先 clone 再本地跑
git clone https://github.com/Wool-xing/Test-Agent.git
bash Test-Agent工作流搭建/install.sh /path/to/your-test-project
```

> 默认仓库为 `Wool-xing/Test-Agent`。fork 后将路径替换为你自己用户名（或用 `TEST_AGENT_REPO_URL` 环境变量覆盖）。Windows / 手动方式见 `01-快速开始/部署说明.md`。

`install.sh` 自动完成：克隆模板 → 装 Claude Code → 建目录 → 拷贝全部文件 → 装 Python 依赖 + Playwright。

### 2. 后续步骤

详细启动指引（含 Java/JMeter/Allure 安装、.env 必填、首次跑通验证）：

→ `01-快速开始/使用手册.md` 顶部 **🚀 启动指引** 章节

### 2. 配置 .env（敏感信息）

```bash
cd your-test-project
cp .env.example .env
# 编辑 .env，填入 TEST_APP_URL / TEST_DB_* / ZENTAO_* / WECHAT_WEBHOOK_URL 等
```

### 3. 启动 Claude Code

```bash
cd your-test-project
claude
```

### 4. 在 Claude Code 提示符使用斜杠技能

```text
> /smoke-test                          # 10 分钟 P0 冒烟
> /test-coordinator                    # 完整流程
> /regression-test                     # 回归 + JMeter
> /testcase-design                     # 仅生成用例 Excel
> /python-script-gen                   # 生成 pytest 脚本
> /jmeter-script-gen                   # 生成 JMeter JMX
> /data-preparation                    # 测试数据 + JMeter CSV
> /zentao-bug-submission               # 提交 Bug 到禅道
```

或自然语言：

```text
> 帮我对用户登录功能进行完整测试。需求：手机号+密码登录，记住密码，
> 连续失败 5 次锁定 30 分钟。
```

> 注：`>` 后面是 Claude Code 提示符的输入（斜杠技能或自然语言），**不是 shell 命令**。

---

## 📋 工作流选择指南

| 场景 | 推荐工作流 | 耗时 | 用例范围 | 触发 |
|------|-----------|------|---------|------|
| 上线前快速验证 | `/smoke-test` | ~10 分钟 | P0 | 手动 / CI |
| 新功能完整测试 | `/test-coordinator` | ~2-4 小时 | 全部 | 手动 |
| 迭代后回归 | `/regression-test` | ~1-2 小时 | P0+P1 | CI 自动 |
| 数据准备 | `/data-preparation` | ~5 分钟 | - | 测试前自动 |
| Bug 提交 | `/zentao-bug-submission` | ~2 分钟/个 | - | 失败后 |

---

## 🔧 技术栈速查

| 类型 | 框架/工具 | 版本 | 说明 |
|------|-----------|------|------|
| 接口测试 | requests + pytest + allure-pytest | pytest 7.4.3 | |
| UI 测试 | playwright + pytest-playwright | playwright 1.40.0 | |
| 性能测试（主） | Apache JMeter | 5.6.3（需独立装 Java + JMeter） | CI/release 门禁权威 |
| 性能测试（备） | locust | 2.25.0 | 开发期 Python 内压测 |
| 测试数据 | faker + factory-boy | 20.x + 3.3.0 | utils/data_factory |
| 覆盖率 | pytest-cov | 4.1.0 | cov 指向 $APP_SRC_PATH |
| 并行执行 | pytest-xdist | 3.5.0 | 默认 4 进程 |
| 失败重试 | pytest-rerunfailures | 13.0 | 命令行显式开启 |
| Mock | pytest-mock | 3.12.0 | unittest.mock 包装 |
| 配置 | PyYAML | 6.0.1 | regression_modules.yaml |
| Excel | openpyxl | 3.1.2 | utils/excel_generator |
| Word 报告 | python-docx | 1.1.0 | utils/generate_report |
| Bug 管理 | 禅道 SDK 直连 | - | utils/zentao_bug_manager（severity 1=P0） |
| 通知 | webhook curl 直连 | - | utils/generate_report.send_*（企微/飞书/钉钉） |
| 重试 | tenacity / 自实现 | 8.2.3 | utils/api_retry_util（10/20/40s） |
| AI 模型 | Claude 4.x 系列 | Opus 4.7 / Sonnet 4.6 | Claude Code 默认管理 |
| MCP | filesystem | npm @modelcontextprotocol | 仅启用 filesystem |

---

## 🔐 闭环约定（设计原则）

1. **数据**：测试数据落 `workspace/测试数据/test_data.json`（conftest fixture 直接消费）
2. **覆盖率**：cov 指向 `$APP_SRC_PATH`（被测系统源码，不是测试脚本本身）
3. **重试策略**：全栈统一 10/20/40s（指数退避），由 `utils/api_retry_util.call_with_retry` 提供
4. **severity/pri 映射**：1=P0 / 2=P1 / 3=P2 / 4=P3，由 `utils/zentao_bug_manager.SEVERITY_MAP` 权威
5. **error_rate 单位**：百分比 pct（字段名 `_pct` 后缀），全栈一致
6. **基线管理**：仅 release 分支 + full 模式 + 全门禁 PASS 才更新 `perf_baseline.json`
7. **门禁分层**：smoke / regression / performance_full / performance_ci_quick，由 `utils/ci_quality_gate.py` 与 `utils/jmeter_result_parser.py` 统一实现
8. **MCP 通道**：当前仅 filesystem。通知/Bug 走 SDK 直连，4 个自定义 mcp_server（zentao/wechat/feishu/dingtalk）按需后续实现
9. **prod 环境**：`get_current_env()` 直接 raise，禁止误测生产
10. **Flaky 与 reruns**：冒烟阶段不开 reruns（保留 flaky 信号），回归阶段开 reruns（快速反馈），flaky 由 history 离线归档检测

---

## 📂 部署后目录速览

```text
your-test-project/
├── .claude/{agents,skills}/           ← 14 agent + 13 skill
├── .github/workflows/test.yml
├── Jenkinsfile
├── utils/                             ← 49 个 .py + __init__
├── src/                               ← 被测系统源码（cov 指向）
├── workspace/
│   ├── 测试计划/  需求分析/  测试用例/  测试数据/
│   ├── 自动化脚本/python/  jmeter/
│   ├── regression_modules.yaml        ← 回归范围配置（可选）
│   └── 执行日志/
│       ├── allure-results/  allure-report/
│       ├── jmeter-results/  jmeter-report/
│       ├── coverage.xml  coverage-report/
│       ├── baselines/perf_baseline.json
│       ├── history/                   ← junit-xml 归档
│       ├── 截图/  报告/
├── conftest.py / pytest.ini / requirements.txt
├── .mcp.json / .env
```

---

## 🛠️ 升级 / 回滚 / 卸载

详见 `01-快速开始/部署说明.md` "升级 / 回滚 / 卸载" 章节。

升级会覆盖：`.claude/agents/`、`.claude/skills/`、`utils/`、`conftest.py`、`pytest.ini`、`requirements.txt`、`.mcp.json`、`.github/workflows/test.yml`、`Jenkinsfile`。
不会覆盖：`.env`、`workspace/`、`src/`。

---

## 🤝 协作与反馈

- 文档结构、Bug 反馈：在仓库内提 issue
- 功能扩展：先在 `02-专家定义/` 加 agent / `03-技能定义/` 加 skill，详见 `CONTRIBUTING.md`
- 改动 `utils/` 时同步更新 `04-配置文件/requirements.txt` 与 `06-CICD集成/` 中的引用

---

## 🔄 跨 AI 工具兼容性

**Claude Code 是默认 / 推荐 runtime，但本项目不强制绑定**。

| 组件 | Claude Code 依赖 | 跨工具适配 |
|------|----------------|----------|
| `.claude/agents/*.md`（YAML frontmatter） | ✅ Claude Code spec | Cursor 用 `.cursorrules`；Continue.dev 用 `.continue/`；通用 LLM 拼接为 system prompt |
| `.claude/skills/*.md`（斜杠技能） | ✅ Claude Code 独有 | 其他工具无对等机制 |
| `.mcp.json`（MCP 协议） | 半依赖 | MCP 是开放协议；Claude Desktop / Cursor 部分支持；OpenAI 系也开始支持 |
| `Agent` 工具（test-lead 调用子专家） | ✅ Claude Code 独有 | 其他工具用人工编排 / 多 agent 框架替代 |
| `utils/*.py`（49 个，含 `__init__.py`） | ❌ 纯 Python | 跨工具完全可用 |
| pytest / Playwright / JMeter / Allure | ❌ 跨工具 | 完全可用 |
| CI/CD（yml / groovy） | ❌ 跨工具 | 完全可用 |
| conftest.py / .env / requirements.txt | ❌ 标准 Python | 完全可用 |

### 迁移成本

- **工程链零改动**：utils + pytest + JMeter + CI 完全跨工具
- **agent / skill 文档需重写**：迁移到 Cursor / Continue / 其他工具的对应格式
- **失去**：Claude Code skill 自动加载、Agent tool 子专家协调、`.claude/` 目录约定

### 模型选择

- README 中 Claude 4.x（Opus 4.7 / Sonnet 4.6 / Haiku 4.5）是**推荐**而非强制
- 项目代码本身**不调用任何 LLM API**（utils 全是工具代码）
- 模型由 Claude Code 账户级管理：`claude /login` + `/model` 切换
- 用其他 AI 工具时按其规范选模型即可

---

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
|----|--------|------------|--------|
| L1 | **需求阶段** | `requirements-analyst` 双轨输出（MD + JSON）+ 风险矩阵 | 弱（评审） |
| L2 | **设计阶段** | `testcase-designer` 等价类/边界值/状态迁移/配对测试 + 风险矩阵 | 弱（评审） |
| L3 | **IDE 编码时** | ruff + mypy + IDE 实时提示 | 强（编辑器红线） |
| L4 | **commit 前 (pre-commit)** | gitleaks + ruff + private-source 防护 + .env 防护 + 14/13/49 文件统计 | 强（阻断 commit） |
| L5 | **PR gate** | CodeQL + pip-audit + safety + ci.yml 全套 | 强（阻断合入） |
| L6 | **静态分析** | Bandit（Python SAST）+ ZAP/Burp Pro（DAST） | 中（发现/修） |
| L7 | **契约测试** | `utils/contract_test.py` consumer-side / provider-side | 强（CI 阻断） |

**Test-Agent 现状评估**：L1-L5 已串通；L6 在 utils 已有 `security_scanner.py`；L7 utils 存在但未串成"自动 PR 阻断"链路。

**Phase 2 收尾点**：把 L7 契约测试串成"PR 改了 OpenAPI spec → 自动跑 contract → 不通过阻断合入"链路。

### 3. Shift-Right（右移）— 生产即测试环境

**核心理念**：测试不止于发布前；通过生产监测 + 安全发布机制 + 主动故障注入持续验证质量。

**Shift-Right 实施层级**：

| 层 | 机制 | 工具 / utils | Test-Agent 状态 |
|----|------|------------|----------------|
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
|------|--------|------|----------|
| 用例通过率 | junit-xml | ✅ Allure | Allure 报告 |
| 覆盖率 | coverage.xml | ✅ pytest-cov HTML | 覆盖率 HTML |
| 性能基线 | jmeter-results/result.jtl | ✅ JMeter HTML + baseline.json | JMeter HTML |
| Flaky 率 | history/junit-xml | ✅ flaky_detector | ⚪ 缺统一仪表盘 |
| DORA 4 指标 | git log + 缺陷库 | ✅ dora_metrics.py | ⚪ 缺统一仪表盘 |
| 缺陷密度/逃逸率/重开率 | 禅道 | ✅ bug-manager 内嵌 | ⚪ 缺统一仪表盘 |
| 用例减重信号 | 覆盖率 + Jaccard | ✅ suite_minimizer | ⚪ 报告内嵌 |
| 变异分数 | mutmut | ✅ mutation_runner | ⚪ 报告内嵌 |

**Phase 3 收尾点**：整合 flaky/DORA/缺陷密度/变异分数到统一 dashboard（Grafana 或 静态 HTML）。

### 5. 质量门禁分层（Layered Quality Gates）

**为什么分层**：一刀切门禁要么过严卡死开发节奏，要么过松形同虚设。分层 = 不同阶段不同严苛度。

**Test-Agent 五层门禁**：

| 层 | 触发 | 关键阈值 | 不达标处置 | 实现 |
|----|------|---------|----------|------|
| **smoke** | 每次 commit/PR | P0 通过率 ≥95% + 0 新 P0 Bug + API ≤3000ms | 阻断后续 | `utils/ci_quality_gate.py::GATES['smoke']` |
| **regression** | merge 到 main / develop | P0=100% / P1≥95% / 总体≥90% / cov ≥80% / Flaky <5% | 评估遗留风险 | `utils/ci_quality_gate.py::GATES['regression_p0_p1']` |
| **performance_ci_quick** | CI 默认（5 并发） | TPS≥20 / P95≤800ms / err <1% | 警告不阻 | `utils/jmeter_result_parser.DEFAULT_GATES_CI_QUICK` |
| **performance_full** | release/* 分支 + 手动（50 并发） | TPS≥100 / P95≤500ms / 基线回归 <20% | 阻断 release | `utils/jmeter_result_parser.DEFAULT_GATES_FULL` |
| **release** | 上线前 | 上述全 PASS + bug-manager 审批 + test-lead 决策 | 不上线 | `02-专家定义/01-测试主管.md::上线决策` |

**门禁可配置性**：阈值集中在 `utils/ci_quality_gate.py::GATES` + `utils/jmeter_result_parser.py::DEFAULT_GATES_*`。Phase 2 抽 `quality_gate_engine.py` + yaml 驱动，让用户改阈值不需改代码。

**Flaky vs Reruns 设计哲学**：
- **冒烟阶段**：不开 reruns，**保留 flaky 信号**（Flaky 是质量问题，不是网络问题）
- **回归阶段**：开 reruns（`--reruns=2 --reruns-delay=5`），**追求快反馈**
- **Flaky 检测**：`utils/flaky_detector.py` 离线扫 history，失败率 >30% 标 quarantine
- **Quarantined 用例**：单独 marker `@flaky`，不计入门禁，每周清理

### 6. 调整路径（路线图 Phase 2-4 落地点）

> 详细路线见根目录战略地图（私有源 `Test-Agent工作流搭建.md` 第十三节）。

| 维度 | 现状 | 路线图阶段 | 关键交付 |
|------|------|----------|---------|
| **金字塔单元层** | 弱（utils 自身无测试） | Phase 2 (M4-M5) | `tests/test_utils_*.py` 全覆盖 + 变异测试反向用 |
| **Shift-Left L7 契约链路** | utils 雏形未串通 | Phase 2 (M5-M6) | OpenAPI 改动 → contract → PR 阻断 |
| **Shift-Right R1 合成监控** | 缺 | Phase 3 (M7-M8) | `utils/synthetic_monitor.py` |
| **Shift-Right R4 canary + feature flag** | 缺 | Phase 3 (M7-M8) | `utils/canary_runner.py` + `feature_flag_validator.py` |
| **可观测统一 dashboard** | 散落 HTML 报告 | Phase 3 (M8-M9) | DORA + 缺陷密度 + flaky + 变异分数 → Grafana / 静态 HTML 模板 |
| **门禁引擎抽象** | 阈值写死代码 | Phase 2 (M4) | `utils/quality_gate_engine.py` + yaml 驱动 |
| **AI 测试深化** | 漂移 + LLM eval | Phase 4 (M11) | + prompt 版本回归 + RAG 召回精度 + token 成本门禁 + hallucination rate |

---

## 📜 LICENSE / CHANGELOG / CONTRIBUTING / SECURITY

- **LICENSE**：MIT（详见 [`LICENSE`](LICENSE)）
- **CHANGELOG**：详见 [`CHANGELOG.md`](CHANGELOG.md)（V1.0.0 首版 + W1-W3 增量）
- **VERSION**：详见 [`VERSION`](VERSION)
- **CONTRIBUTING**：详见 [`CONTRIBUTING.md`](CONTRIBUTING.md)（含同步铁律 + RACI 矩阵）
- **SECURITY**：详见 [`SECURITY.md`](SECURITY.md)（漏洞报告流程 + GitHub Security Advisories 入口）
- **CODE_OF_CONDUCT**：详见 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)（基于 Contributor Covenant 2.1）
