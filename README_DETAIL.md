# Test-Agent 测试全流程专家团队

**项目目录名**：`Test-Agent工作流搭建`
**版本**：V1.0.0
**更新日期**：2026-05-10
**模型**：Claude 4.x 系列（Opus 4.7 / Sonnet 4.6 / Haiku 4.5，由 Claude Code 默认管理）

---

## 📚 文档导航

| 路径 | 文档 | 说明 | 适用对象 |
|------|------|------|----------|
| 根目录 | README.md | 本文档（项目入口） | 所有用户 |
| 根目录 | **00-项目导航.md** | **按职责分类速查（通用流程 / 平台专项 / 协议 / 输入 / CI）** | **所有用户** |
| 根目录 | Test-Agent工作流搭建.md | 单文件全嵌入版（备查，副本会同步） | 所有用户 |
| `01-快速开始/` | 使用手册.md | 快速上手指南 + FAQ | 所有用户 |
| `01-快速开始/` | 部署说明.md | 跨平台部署（Win/Mac/Linux 含 Java/JMeter/Allure） | 运维/测试 |
| `01-快速开始/` | 配置清单.md | 一站式配置文档（.env 全字段 + Secrets + Webhook 申请） | 所有用户 |
| `01-快速开始/` | 交付物清单.md | 测试计划 / 测试报告 / Bug 等对外提交物落地位置与责任 | 所有用户 |
| `02-专家定义/` | 14 个 .md（9 核心 + 5 平台扩展） + README 索引 | Agent 定义文件 | 开发人员 |
| `03-技能定义/` | **13 个** Skill 文件 + README 索引 | 可复用测试技能 | 开发人员 |
| `04-配置文件/` | conftest.py / pytest.ini / .env.example / .mcp.json / requirements.txt | 配置文件集合 | 开发人员 |
| `04-配置文件/` | mcp-server-impl.md | MCP server 自实现教程（zentao/wechat/feishu/dingtalk 骨架） | 高级开发 |
| `05-代码示例/` | utils（24 个 .py + __init__）+ README 索引（4 类：核心/平台/协议/输入） | 完整可运行 Python 工具集 | 开发人员 |
| `06-CICD集成/` | github-actions-test.yml / jenkins-pipeline.groovy / 集成说明.md | CI/CD 流水线（含 JMeter 性能阶段） | DevOps |

---

## 🚀 核心特性

### 8 位专家 + 1 位协调者

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

## 🌐 全链路覆盖矩阵

| 平台 | 工具栈 | Agent | Skill | 状态 |
|------|-------|-------|-------|------|
| Web（PC + 移动 H5） | Playwright | automation-engineer | python-script-gen | ✅ |
| REST/GraphQL API | requests | automation-engineer | python-script-gen | ✅ |
| 数据库 | SQLAlchemy | data-preparer | data-preparation | ✅ |
| 性能压测 | JMeter（主） + Locust（备） | automation-engineer | jmeter-script-gen | ✅ |
| Mock 服务 | wiremock + pytest-mock | env-manager | - | ✅ |
| **Android APP** | Appium | mobile-tester | mobile-test | ✅ |
| **iOS APP** | Appium + XCUITest | mobile-tester | mobile-test | ✅ |
| **微信 / 支付宝小程序** | 微信开发者工具 CLI | mobile-tester | mobile-test | ✅ |
| **Windows EXE** | pywinauto / uiautomation | desktop-tester | desktop-test | ✅ |
| **macOS GUI** | PyAutoGUI + AppleScript | desktop-tester | desktop-test | ✅ |
| **Electron** | Playwright Electron API | desktop-tester | desktop-test | ✅ |
| **WebSocket 协议**（含同步/异步/重连/并发） | websocket-client + websockets | desktop-tester / automation-engineer | desktop-test / python-script-gen | ✅ |
| **gRPC** | grpcio + 项目 proto | automation-engineer | python-script-gen | ✅ |
| **TCP / UDP** | socket 标准库 | system-tester / automation-engineer | system-test | ✅ |
| **GraphQL** | requests + body | automation-engineer | python-script-gen | ✅ |
| **SOAP** | requests + envelope | automation-engineer | python-script-gen | ✅ |
| **Modbus**（工业协议） | pymodbus | system-tester | system-test | ✅ |
| **游戏 / Canvas / WebGL** | Airtest | visual-tester | visual-test | ✅ |
| **OCR / 视觉回归** | Tesseract + OpenCV SSIM | visual-tester | visual-test | ✅ |
| **IoT / 嵌入式** | paramiko + pyserial + paho-mqtt | system-tester | system-test | ✅ |
| **音视频** | FFmpeg + ffprobe | system-tester | system-test | ✅ |
| **链路追踪** | Jaeger / Zipkin HTTP API | system-tester | system-test | ✅ |
| **消息队列** | Kafka / RabbitMQ | system-tester | system-test | ✅ |
| **AI/ML 模型** | scikit-learn + scipy | ai-tester | ai-test | ✅ |
| **数据漂移检测** | KS / PSI | ai-tester | ai-test | ✅ |
| **LLM 应用** | 格式 / 拒答 / 事实性 | ai-tester | ai-test | ✅ |
| Bug 闭环 | 禅道 SDK | bug-manager | zentao-bug-submission | ✅ |
| 报告通知 | Allure + Word + 三端 webhook | report-generator | - | ✅ |
| CI/CD | GitHub Actions / Jenkins | - | - | ✅ |

**全链路覆盖率：≈ 90%**（剩 10% 为高度专业领域：航空/医疗/工业控制等）

---

## 🏗️ 架构图（运行时）

```
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
curl -fsSL https://raw.githubusercontent.com/YOUR-USER/Test-Agent工作流搭建/main/install.sh | bash -s -- /path/to/your-test-project

# 或先 clone 再本地跑
git clone https://github.com/YOUR-USER/Test-Agent工作流搭建.git
bash Test-Agent工作流搭建/install.sh /path/to/your-test-project
```

> 替换 `YOUR-USER` 为你的 GitHub 用户名。Windows / 手动方式见 `01-快速开始/部署说明.md`。

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

```
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

```
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
2. **覆盖率**：cov 指向 `$APP_SRC_PATH`（被测系统源码，**不是测试脚本本身**）
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

```
your-test-project/
├── .claude/{agents,skills}/           ← 9 agent + 8 skill
├── .github/workflows/test.yml
├── Jenkinsfile
├── utils/                             ← 12 个 .py + __init__
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

升级会**覆盖**：`.claude/agents/`、`.claude/skills/`、`utils/`、`conftest.py`、`pytest.ini`、`requirements.txt`、`.mcp.json`、`.github/workflows/test.yml`、`Jenkinsfile`。
**不会覆盖**：`.env`、`workspace/`、`src/`。

---

## 🤝 协作与反馈

- 文档结构、Bug 反馈：在仓库内提 issue
- 功能扩展：先在 `02-专家定义/` 加 agent / `03-技能定义/` 加 skill，再同步到 `Test-Agent工作流搭建.md` 内嵌副本
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
| `utils/*.py`（12 个） | ❌ 纯 Python | **跨工具完全可用** |
| pytest / Playwright / JMeter / Allure | ❌ 跨工具 | **完全可用** |
| CI/CD（yml / groovy） | ❌ 跨工具 | **完全可用** |
| conftest.py / .env / requirements.txt | ❌ 标准 Python | **完全可用** |

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

## 📜 LICENSE / CHANGELOG / CONTRIBUTING

- LICENSE：项目按需选择（推荐 MIT / Apache-2.0）
- CHANGELOG：建议建 `CHANGELOG.md` 记录版本演进（V1.0.0 首版）
- CONTRIBUTING：维护者按需补充贡献流程
