<!--
本文件由 `FULL_GUIDE.md` 拆分而来 (W7-d 文档重构, 2026-05-14)。
原始单文件 1252 行 → 7 子文件; 主 FULL_GUIDE.md 改为索引。
内容与原 FULL_GUIDE.md 对应段完全一致, 仅拆不动语义。
-->

## 📦 按需安装与依赖分层

> install.sh 不再一次性装全。**用户选了什么形态，才装什么依赖**——避免 mobile 用户被强装 desktop 工具，反之亦然。

### 1. 依赖六层划分（Phase 2 规划）

> **当前状态**：`install.sh` 通过 `pip install -r requirements.txt` 统一安装。分层按需安装（按产品形态选择性装依赖）为 Phase 2 路线图项。`requirements/` 目录含规划文档。

| 层 | requirements 文件 | 触发条件 | 关键包 |
|----|----------------|---------|--------|
| **base**（必装） | `requirements/base.txt` | 永远装 | pytest / requests / playwright / faker / openpyxl / python-docx / allure-pytest |
| **mobile** | `requirements/mobile.txt` | 选择 mobile / mini-program | Appium-Python-Client / 微信开发者 CLI（外部） |
| **desktop** | `requirements/desktop.txt` | 选择 desktop | pywinauto / uiautomation / PyAutoGUI |
| **visual** | `requirements/visual.txt` | 选择 game / visual-regression | airtest / opencv-python / pytesseract |
| **system** | `requirements/system.txt` | 选择 IoT / 音视频 / blockchain | paho-mqtt / pyserial / web3 / kafka-python / ffmpeg-python |
| **ai** | `requirements/ai.txt` | 选择 AI / LLM 测试 | scikit-learn / scipy + LLM eval lib |
| **perf**（推荐装） | `requirements/perf.txt` | 选择性能测试 | locust（JMeter 走外部 Java，不进 pip） |

### 2. install.sh 交互流程

```bash
$ bash install.sh /path/to/your-test-project

[1/5] 检测 Python / Java / Node 环境...
[2/5] 选择你要测试的产品形态（多选，空格分隔）：
  1) Web + API（base，默认必选）
  2) Mobile（Android / iOS / 小程序）
  3) Desktop（Win / Mac / Linux GUI / Electron）
  4) Visual / Game / OCR
  5) System / IoT / 音视频 / Blockchain
  6) AI / LLM 模型
  7) Performance（JMeter 主 + Locust 备）
> 1 2 7   ← 用户输入

[3/5] 将安装：base + mobile + perf 三层
[4/5] 装 Python 依赖...（仅装上述三层）
[5/5] 装 Playwright browsers / Appium（按选择装）
完成。可用 skills：core 8 + mobile-test（其他平台 skill 不装）
```

### 3. agent / skill 级依赖元数据

每个 agent .md / skill .md 头部 frontmatter 声明依赖层：

```yaml
---
name: mobile-tester
requires_layer: [base, mobile]
optional_layer: [visual]   # 跨平台时按需
---
```

install.sh 反向计算：用户选了哪些 skill / agent → 自动算出最小必装层并集。

### 4. 后期补装

```bash
$ bash install.sh --add visual,ai
```

不重装 base，只增量补 visual / ai。dependency 冲突走 `pip install --upgrade-strategy only-if-needed` 防止已稳定包被改版本。

### 5. 验收（对应闭环约定第 14/15 条）

- 装完跑 `pytest --collect-only` 必须 0 错误
- 装完跑 `python -c "import utils.<对应层>"` 全模块必须 import 通过
- 不影响已有 workspace/.env

### 6. 运行时按需补装（agent / skill 入口自检）

> 装机时未选的层，**运行时仍可触发** —— 不强迫用户重新跑 install.sh，但也不静默自动装。

**自检与补装回路**（5 步）：

1. **依赖自检**：agent / skill 启动时读取自身 frontmatter `requires_layer`，与已装层并集对比
2. **缺则反问**：缺失则停下反问，列层级 + 关键包 + 预估安装时间 + 影响范围

   > 示例："`/visual-test` 需要 visual 层（airtest + opencv-python + pytesseract，约 80MB / 2-5 分钟）。现在补装？(Y/n)"
3. **触发补装**：用户同意 → 调 `install.sh --add visual` → 增量补装
4. **落档**：补装请求 + 用户决定 + 时间戳 → `workspace/测试报告/discussions/{date}_dependency-asks.md`
5. **拒绝处置**：用户拒绝 → agent / skill 降级（如可降级，例如 `/visual-test` 退化为纯 pytest）或拒绝执行并落 `decisions/`，**不静默继续假装能跑**

**为什么不静默自动装**：跨平台环境差异大（特别是 system 层涉及系统级工具 Java / Node / FFmpeg），强行装可能污染用户环境。符合「Agent 能力越强谦卑义务越重」公理。

**用户配置一站式清单**（首次部署后必查）：

| 配置项 | 文件 | 必填字段 |
|--------|------|---------|
| 被测系统 | `.env` | `TEST_APP_URL` / `APP_SRC_PATH` / `TEST_DB_*` |
| Bug Tracker | `.env` | `BUG_TRACKER` + 对应 adapter 字段（zentao_/jira_/github_/linear_/webhook_） |
| 多端通知 | `.env` | `WECHAT_WEBHOOK_URL` / `FEISHU_WEBHOOK_URL` / `DINGTALK_WEBHOOK_URL` / `SLACK_WEBHOOK_URL` / `EMAIL_SMTP_*` / `TEAMS_WEBHOOK_URL`（至少一个） |
| 性能门禁 | `utils/jmeter_result_parser.py::DEFAULT_GATES_*` | 阈值微调 |
| 功能门禁 | `utils/ci_quality_gate.py::GATES` | 阈值微调 |
| 回归范围 | `workspace/regression_modules.yaml` | 模块白名单 |
| CI/CD | `.github/workflows/test.yml` 或 `Jenkinsfile` | secrets 注入 |

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
                  Allure + JMeter HTML + Word + 多端通知
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
bash Test-Agent/install.sh /path/to/your-test-project
```

> 默认仓库为 `Wool-xing/Test-Agent`。fork 后将路径替换为你自己用户名（或用 `TEST_AGENT_REPO_URL` 环境变量覆盖）。Windows / 手动方式见 `docs/getting-started/部署说明.md`。

`install.sh` 自动完成：克隆模板 → 装 Claude Code → 建目录 → 拷贝全部文件 → 装 Python 依赖 + Playwright。

### 2. 配置 .env（敏感信息）

```bash
cd your-test-project
cp .env.example .env
# 编辑 .env，填入 TEST_APP_URL / TEST_DB_* / BUG_TRACKER + 对应字段 / WECHAT_WEBHOOK_URL 等
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
> /bug-submission                      # 按 BUG_TRACKER 路由提交 Bug
```

或自然语言：

```text
> 帮我对用户登录功能进行完整测试。需求：手机号+密码登录，记住密码，
> 连续失败 5 次锁定 30 分钟。
```

> 注：`>` 后面是 Claude Code 提示符的输入（斜杠技能或自然语言），**不是 shell 命令**。

详细启动指引（含 Java/JMeter/Allure 安装、.env 必填、首次跑通验证）→ `docs/getting-started/使用手册.md` 顶部「🚀 启动指引」章节。

---

## 📋 工作流选择指南

| 场景 | 推荐工作流 | 耗时 | 用例范围 | 触发 |
|------|-----------|------|---------|------|
| 上线前快速验证 | `/smoke-test` | ~10 分钟 | P0 | 手动 / CI |
| 新功能完整测试 | `/test-coordinator` | ~2-4 小时 | 全部 | 手动 |
| 迭代后回归 | `/regression-test` | ~1-2 小时 | P0+P1 | CI 自动 |
| 数据准备 | `/data-preparation` | ~5 分钟 | - | 测试前自动 |
| Bug 提交 | `/bug-submission` | ~2 分钟/个 | - | 失败后 |

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
| Bug 管理 | 5 adapter 工厂（禅道 默认 / Jira / GitHub Issues / Linear / Webhook） | - | utils/bug_manager + bug_tracker_*.py，由 `.env BUG_TRACKER` 选择 |
| 通知 | webhook curl 直连 | - | utils/generate_report.send_*（企微/飞书/钉钉） |
| 重试 | tenacity / 自实现 | 8.2.3 | utils/api_retry_util（10/20/40s） |
| AI 模型 | Claude 4.x 系列 | Opus 4.7 / Sonnet 4.6 | Claude Code 默认管理 |
| MCP | filesystem | npm @modelcontextprotocol | 仅启用 filesystem |

---

## 🔐 闭环约定（设计原则）

> 18 条全栈闭环约定（数据/cov/重试/severity/error_rate/基线/门禁/MCP/prod禁/Flaky/铭文/决策追溯/三筐/修改四关/工具兼容/纪要不可删/自进化棘轮/依赖补装）— 已迁入主宪章 §19，FULL_GUIDE 不再重复维护。

---

## 📂 部署后目录速览

```text
your-test-project/
├── .claude/{agents,skills}/           ← 16 agent + 32 skill（业务） + 3 元 skill
├── .github/workflows/test.yml
├── Jenkinsfile
├── utils/                             ← 78 个 .py + __init__
├── src/                               ← 被测系统源码（cov 指向）
├── workspace/
│   ├── 测试计划/  需求分析/  测试用例/  测试数据/
│   ├── 自动化脚本/python/  jmeter/
│   ├── regression_modules.yaml        ← 回归范围配置（可选）
│   └── 测试报告/
│       ├── allure-results/  allure-report/
│       ├── jmeter-results/  jmeter-report/
│       ├── coverage.xml  coverage-report/
│       ├── baselines/perf_baseline.json
│       ├── history/                   ← junit-xml 归档
│       ├── discussions/               ← AgentChat 讨论纪要 + 反问澄清 + 依赖补装记录
│       ├── decisions/                 ← 放行/拒绝决策日志（闭环约定 12）
│       ├── skill-evolution/           ← darwin-skill results.tsv + 成果卡片
│       ├── 截图/  报告/
├── conftest.py / pytest.ini / requirements.txt
├── .mcp.json / .env
```

---

## 🛠️ 升级 / 回滚 / 卸载

详见 `docs/getting-started/部署说明.md` "升级 / 回滚 / 卸载" 章节。

升级会覆盖：`.claude/agents/`、`.claude/skills/`、`utils/`、`conftest.py`、`pytest.ini`、`requirements.txt`、`.mcp.json`、`.github/workflows/test.yml`、`Jenkinsfile`。
不会覆盖：`.env`、`workspace/`、`src/`。

---

## 🤝 协作与反馈

- 文档结构、Bug 反馈：在仓库内提 issue
- 功能扩展：先在 `agents/` 加 agent / `skills/` 加 skill，详见 `CONTRIBUTING.md`
- 改动 `utils/` 时同步更新 `config/requirements.txt` 与 `ci/` 中的引用

---

## 🔄 跨 AI 工具兼容性

**Claude Code 是默认 / 推荐 runtime，但本项目不强制绑定**。

| 组件 | Claude Code 依赖 | 跨工具适配 |
|------|----------------|----------|
| `.claude/agents/*.md`（YAML frontmatter） | ✅ Claude Code spec | Cursor 用 `.cursorrules`；Continue.dev 用 `.continue/`；通用 LLM 拼接为 system prompt |
| `.claude/skills/*.md`（斜杠技能） | ✅ Claude Code 独有 | 其他工具无对等机制 |
| `.mcp.json`（MCP 协议） | 半依赖 | MCP 是开放协议；Claude Desktop / Cursor 部分支持；OpenAI 系也开始支持 |
| `Agent` 工具（test-lead 调用子专家） | ✅ Claude Code 独有 | 其他工具用人工编排 / 多 agent 框架替代 |
| `utils/*.py`（76 个，含 `__init__.py`） | ❌ 纯 Python | 跨工具完全可用 |
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
