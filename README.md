# 🤖 Test-Agent 工作流

> **项目代号**：`test-agent-team` · **版本**：V1.7.0-alpha · **License**：MIT
>
> **Claude Code 驱动的全链路软件测试自动化工作流 + 可执行运行时 + MCP 6 件套 + Web UI + 渗透&安全 + 车载&自动驾驶**
> **16 Agent**(核心 9+扩展 7 含渗透+车载) · **26 Skill** · 49 Utils · runtime/ + MCP 6 件套 + Web UI + 2 垂直 skill 集 · 全平台覆盖 · 一键部署

[![CI](https://github.com/Wool-xing/Test-Agent/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Wool-xing/Test-Agent/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-1.0+-purple.svg)](https://docs.anthropic.com/claude-code)
[![Pytest](https://img.shields.io/badge/Pytest-8.3-green.svg)](https://pytest.org)
[![JMeter](https://img.shields.io/badge/JMeter-5.6.3-orange.svg)](https://jmeter.apache.org)
[![Dependabot](https://img.shields.io/badge/Dependabot-enabled-brightgreen.svg)](https://github.com/Wool-xing/Test-Agent/security/dependabot)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/Wool-xing/Test-Agent/main)](https://github.com/Wool-xing/Test-Agent/commits/main)

---

## ✨ V1.7.0-alpha 新增:Karpathy 4 原则 + ECC 测试加固 + Essence 自动汲取

派生自 [`D:/项目文件/_精髓库/karpathy-skills.md`](../../_精髓库/karpathy-skills.md)(125k★)+ [`everything-claude-code.md`](../../_精髓库/everything-claude-code.md)(179k★)。

| 能力 | 路径 | 来源 |
|------|------|------|
| **Karpathy 4 原则** | `03-技能定义/karpathy-guidelines/SKILL.md` | karpathy-skills(主宪章 §27 元层) |
| **tdd-workflow** | `03-技能定义/tdd-workflow.md` | ECC §28 |
| **verification-loop** | `03-技能定义/verification-loop.md` | ECC §28 |
| **e2e-testing** | `03-技能定义/e2e-testing.md` | ECC §28 |
| **eval-harness** | `03-技能定义/eval-harness.md` | ECC + gbrain eval 回放融合 |
| **security-review** | `03-技能定义/security-review.md` | ECC(与 §25 pentest 应用层互补) |
| **agent-introspection-debugging** | `03-技能定义/agent-introspection-debugging.md` | ECC §28 |
| **Essence 自动汲取** | `runtime/essence_watcher/` | §29 闭环治理 |

主宪章 §27 §28 §29 收录铁律(4 原则贯穿 / Tests BEFORE Code / 5-phase verify / opt-in 不偷数据)。

数字:14 skill → **32**(+7 pentest +5 automotive +6 ECC) + karpathy-guidelines upstream。

---

## ✨ V1.6.0-alpha 新增:渗透&安全 + 车载&自动驾驶 双垂直专家+skill 集

派生自 [`D:/项目文件/_精髓库/pentest-ai-agents.md`](../../_精髓库/pentest-ai-agents.md):

### 渗透安全(7 skill + 1 专家)
- 专家:`02-专家定义/15-渗透测试.md` `pentest-tester`
- 主 skill:`/pentest-coordinator` → 子 6:`recon` / `vuln` / `exploit` / `web` / `api` / `report`
- **白盒 + 黑盒** + 5 攻击域(Injection/XSS/SSRF/Auth/Authz)并发 + **PoC-only** 报告

### 车载&自动驾驶(5 skill + 1 专家)
- 专家:`02-专家定义/16-车载测试.md` `automotive-tester`
- 主 skill:`/automotive-test` → 子 4:`can-bus` / `adas-scenario` / `ota-update` / `hil-loop`
- ISO 26262 ASIL D + SOTIF + UN R155/R156 + AUTOSAR + V2X

主宪章 §25 §26 收录铁律(授权前置 / 沙箱 / PoC-only / ASIL C/D 必 HIL / OTA 必回退)。

---

## ✨ V1.5.0-alpha 新增:GBrain-inspired 强化(自连图谱 / eval 回放 / safe-by-default)

派生自 [`D:/项目文件/_精髓库/gbrain.md`](../../_精髓库/gbrain.md):

| 能力 | 路径 | 用途 |
|------|------|------|
| KB 自连图谱 | `runtime/tutor/graph.py` | 零 LLM 抽 6 种 typed link;walk + backlink boost |
| eval 回放 | `runtime/tutor/eval_replay.py` | `TAGENT_EVAL_CAPTURE=1` opt-in;PII scrub;3 数评估 |
| safe-by-default | `runtime/config/safety.py` + `tagent.yml.example` | scheduler/backends/destructive 默认 deny,显式 yaml 放行 |

主宪章 §24 收录铁律。

---

## ✨ V1.4.0-alpha 新增:教学层 · 用户边用边学

```bash
tagent run "测 ./app.exe" --mode learn --lang zh   # 新手:每步详解+权威引用+替代方案
tagent run "测 ./app.exe" --mode exec --lang en    # 老手:每步一句 why(≤30 字)
tagent run "..." --mode silent                       # CI:无解释
```

| 维度 | 实现 |
|------|------|
| 双模式 | exec(老手默认)/ learn(新手)/ silent(CI) |
| 双语 | zh / en / zh-en(双栏对照) |
| Theory KB | `docs/theory/{01-tools..12-process}/` 12 大类 |
| 权威源白名单 | ISTQB/IEEE/ISO/NIST/OWASP/MITRE/Google/Fowler + GB/T/等保/阿里/腾讯/美团/字节/CCF + 经典书 |
| 反幻觉 3 层 | L1 KB 引用约束 / L2 自检 / L3 用户回报 |
| 持续累积 | 未收录概念自动产 `llm-draft-unreviewed` 卡待审 |

主宪章 §23 收录完整准则。详见 [`docs/theory/INDEX.md`](docs/theory/INDEX.md)。

---

## ✨ V1.3.0-alpha 新增:Hermes-inspired 5 模块 + 跨项目精髓库

派生自 [`D:/项目文件/_精髓库/hermes-agent.md`](../../_精髓库/hermes-agent.md):

| 模块 | 用途 | 来源 |
|------|------|------|
| `runtime/scheduler/` | cron 定时任务 + 运行时 prompt 注入扫 | hermes §1.2 |
| `runtime/subagent/` | 并行子代理 + 隔离 client | hermes §1.3 |
| `runtime/learning_loop/` | 封闭学习循环(curator+FTS5+用户画像) | hermes §1.1 |
| `runtime/backends/` | 7 执行后端(含 Modal/Daytona hibernate) | hermes §1.4 |
| `runtime/gateway/` | 8 平台 messaging(中文 4 + 西方 3 + 通用) | hermes §1.5 |

主宪章 §22 收录铁律(运行时 prompt 全扫 / 决策不可逆禁止 / 隔离 client / Backend+Platform 抽象统一)。

---

## ✨ V1.2.0-alpha 新增:MCP 6 件套 + Web UI

主宪章 §16 预留的 6 件 MCP 服务全部 ship:

| MCP server | 工具 | 路径 |
|------------|------|------|
| test-orchestrator | catalog / plan / run / status / report | `runtime/mcp/test_orchestrator/` |
| protocol-adapter | list_protocols / ping(http/grpc/ws/mqtt/kafka) | `runtime/mcp/protocol_adapter/` |
| evidence-vault | upload / list / get / search | `runtime/mcp/evidence_vault/` |
| defect-tracker | create_bug / get / update / query / list_trackers | `runtime/mcp/defect_tracker/` |
| knowledge-base | embed / index_case / index_defect / search_similar | `runtime/mcp/knowledge_base/` |
| compliance-checker | list_profiles / get_profile / check_compliance | `runtime/mcp/compliance_checker/` |

10 合规框架 profile(SOC2/PCI-DSS/HIPAA/IEC 62304/IEC 61508/ISO 26262/DO-178C/GDPR/PIPL/CCPA)→ `profiles/compliance/`(空载,真规则由领域专家供)

Web UI MVP(`runtime/web/`):Vite+React+shadcn,4 页(Upload/RunStatus/Report/Catalog),Playwright+axe-core 测试套件(§21 L2)

```bash
cd runtime/web && npm install && npm run dev
```

---

## ✨ V1.1.0-alpha 新增:运行时层(`runtime/`)

从"文档+脚本工具箱"升级为"可执行运行时",**已有 14 专家 / 14 Skill / 49 脚本不动**(宪章铁律),runtime 仅作调度。

```bash
# 列 14 专家 + 14 Skill 目录
python -m runtime.cli.main catalog

# 路由 Demo (stub provider, 不连真 LLM)
TAGENT_LLM_PROVIDER=stub python -m runtime.cli.main run "Web 系统 https://example.com 登录流程"

# 起本地依赖(Postgres+MinIO+Prefect)+ 服务
cd runtime && docker compose up -d
uvicorn runtime.api.main:app --port 8800
```

**能力**:多厂商 LLM 路由(LiteLLM:Claude/OpenAI/Gemini/Qwen/DeepSeek/Ollama 本地) · Prefect 2.x 编排 + Direct 降级模式 · 飞轮存储(Postgres+pgvector+MinIO) · OpenTelemetry · FastAPI + Typer CLI 双入口 · 多格式输入(PDF/Word/MD/exe/APK/IPA/Docker/URL/口头)

详见 [`runtime/INDEX.md`](runtime/INDEX.md)

---

## ✨ 核心特性

- 🎯 **9 核心 + 5 平台扩展 = 14 个测试专家 Agent**,test-lead 智能调度
- 📋 **13 个一键技能**：冒烟 / 回归 / 完整流程 / 用例生成 / 性能 / Bug 提交 / 多平台专项
- 🌐 **全链路覆盖**：Web · API · Android/iOS · 微信小程序 · Windows EXE · macOS · Electron · 游戏 · IoT · AI/LLM
- 📡 **20+ 协议**：HTTP · WebSocket · gRPC · TCP/UDP · GraphQL · SOAP · MQTT · Kafka · Modbus · 串口 等
- 📄 **多格式 PRD**：md · pdf · docx · xlsx · pptx · zip · png · html · URL（自动平台识别 + 路由）
- 📊 **多格式输出**：Word · Excel · PDF · PPTX · HTML · JSON · Markdown · 邮件 · 三端 webhook
- 🚦 **分层质量门禁**：smoke ≥95% · regression ≥90% · 覆盖率 ≥80% · 性能 TPS/P95 双模式
- 🔁 **JMeter 双模式**：CI 快验（5 并发）+ Release 完整压测（50 并发，含基线对比）
- 📦 **一键部署**：单行 curl 命令，自动建目录、装依赖、配 CI
- 🔄 **依赖自治**：Dependabot 周扫描 + pip-audit/safety 拦 CVE + 季度人工评审 SOP

---

## 🚀 Quick Start（一行命令）

```bash
curl -fsSL https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.sh | bash -s -- /path/to/your-test-project
```

`install.sh` 自动完成：

1. ✅ 检查工具（git/python3/node/npm/Java）
2. ✅ 装 Claude Code CLI
3. ✅ 克隆模板
4. ✅ 部署 14 agent + 14 skill(含 darwin-skill) + 49 utils + CI/CD 文件
5. ✅ 创建 `.venv` + 装 Python 依赖 + Playwright

完成后 3 步开测：

```bash
cd /path/to/your-test-project
notepad .env                                  # 填 8 个必填字段
claude /login                                  # 首次登录 Claude
claude                                         # 启动
> /smoke-test                                  # 在 Claude 提示符里跑冒烟
```

---

## 📁 项目结构

```text
Test-Agent/
├── 00-项目导航.md           ← 5 维度分类速查
├── 01-快速开始/             ← 使用手册 / 部署 / 配置清单 / 交付物 + INDEX
├── 02-专家定义/             ← 14 个 Agent（核心 9 + 平台扩展 5）+ README
├── 03-技能定义/             ← 13 个 Skill（通用 8 + 平台 5）+ README
├── 04-配置文件/             ← conftest / pytest.ini / .env / .mcp.json + INDEX
├── 05-代码示例/             ← 49 个 utils（含 __init__）+ README
├── 06-CICD集成/             ← GitHub Actions + Jenkins + INDEX
├── runtime/                 ← V1.1.0-alpha 运行时层(AI 路由+Prefect+飞轮+FastAPI/CLI)
├── install.sh               ← 一键部署脚本
├── README.md                ← 本文件（简明入口）
├── FULL_GUIDE.md            ← 完整详细指南（架构/矩阵/技术栈深度）
├── CHANGELOG.md / VERSION   ← 版本变更记录
└── LICENSE / SECURITY.md / CODE_OF_CONDUCT.md / CONTRIBUTING.md
```

---

## 🎯 测试技能速查

### 通用流程

| Skill | 用途 |
|-------|-----|
| `/smoke-test` | 10 分钟 P0 冒烟（≥95% 门禁） |
| `/test-coordinator` | 完整流程编排（自动平台路由） |
| `/regression-test` | P0+P1 回归 + Flaky + JMeter |
| `/testcase-design` | 4 Sheet Excel 用例 |
| `/python-script-gen` | pytest UI/API 脚本 |
| `/jmeter-script-gen` | JMeter 性能脚本（双模式） |
| `/data-preparation` | 测试数据 + JMeter CSV |
| `/zentao-bug-submission` | 禅道 Bug 规范提交 |

### 平台专项

| Skill | 平台 |
|-------|------|
| `/mobile-test` | Android · iOS · 微信/支付宝小程序 |
| `/desktop-test` | Windows EXE · macOS .app · Linux GUI · Electron |
| `/visual-test` | 游戏 · Canvas/WebGL · OCR · 视觉回归 |
| `/system-test` | IoT 嵌入式 · 音视频 · 链路追踪 · 消息队列 |
| `/ai-test` | AI/ML 模型 · 数据漂移 · LLM 应用 |

---

## 📚 文档导航

| 文档 | 用途 |
|------|------|
| [FULL_GUIDE.md](FULL_GUIDE.md) | **完整详细指南**（架构 / 三视角矩阵 / 技术栈 / 闭环约定 / 跨工具兼容） |
| [00-项目导航.md](00-项目导航.md) | 按职责分类速查（按通用流程 / 平台专项 / 协议 / 输入 / CI 五维分类） |
| [01-快速开始/INDEX.md](01-快速开始/INDEX.md) | 使用手册 / 部署 / 配置 / 交付物索引 |
| [02-专家定义/README.md](02-专家定义/README.md) | 14 个 Agent 索引 + 流程依赖关系 |
| [03-技能定义/README.md](03-技能定义/README.md) | 13 个 Skill 索引 + 用法速查 |
| [05-代码示例/README.md](05-代码示例/README.md) | 49 个 utils 分类索引 |
| [04-配置文件/INDEX.md](04-配置文件/INDEX.md) | conftest / pytest / mcp / requirements 配置索引 |
| [06-CICD集成/INDEX.md](06-CICD集成/INDEX.md) | GitHub Actions + Jenkins 流水线索引 |
| [runtime/INDEX.md](runtime/INDEX.md) | **V1.1.0-alpha 运行时层**:AI 路由 / Prefect 编排 / 飞轮 / FastAPI/CLI |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 添加 agent / skill / utils / marker / .env 流程 + 同步铁律 |
| [SECURITY.md](SECURITY.md) | 漏洞报告流程 |
| [CHANGELOG.md](CHANGELOG.md) | 版本变更日志 |

---

## 🛠️ 技术栈速览

pytest · Playwright · Appium · pywinauto · JMeter · Allure · Airtest · OpenCV · Faker · SQLAlchemy · 禅道 SDK · GitHub Actions · Jenkins · Claude 4.x（Opus 4.7 / Sonnet 4.6 / Haiku 4.5）

完整版本号 + 跨工具兼容性矩阵 + 三视角覆盖矩阵 → [FULL_GUIDE.md](FULL_GUIDE.md)

---

## 📊 覆盖能力（速览）

- **产品形态**：Web · API · Android · iOS · 小程序 · Windows EXE · macOS · Linux · Electron · 游戏 · IoT · 音视频 · AI/LLM · 区块链
- **测试类型**：功能 · 性能 · 安全 · 兼容 · 弱网 · 稳定 · 可靠性 · 混沌 · 灾备 · UX · A11y · i18n · 契约 · 视觉回归 · AI对抗 · 变异测试 · DORA
- **用例方法**：等价类 · 边界值 · 判定表 · 场景法 · 状态迁移 · 配对测试 · 正交 · SBTM · 风险矩阵
- **测试金字塔**：E2E 10% / 集成 20% / 单元 70%
- **总覆盖率 ≈ 95%**（剩 5% 为合规领域：DO-178C / HIPAA / IEC61508，业务方按需自加）

详细矩阵 + 工具映射 → [FULL_GUIDE.md](FULL_GUIDE.md)

---

## 🤝 Contributing

详见 [`CONTRIBUTING.md`](CONTRIBUTING.md)（添加 agent / skill / utils / marker / .env 流程 + 提交规范 + PR 自检脚本）。

---

## 📜 License

MIT License - 详见 [LICENSE](LICENSE)

---

## 🙏 致谢

- [Claude Code](https://docs.anthropic.com/claude-code) - Anthropic 官方 CLI
- [pytest](https://pytest.org) - Python 测试框架之王
- [Playwright](https://playwright.dev) - 跨浏览器自动化
- [Appium](https://appium.io) - 移动端自动化
- [Apache JMeter](https://jmeter.apache.org) - 性能测试
- [Airtest](https://airtest.netease.com) - 跨平台图像识别测试

---

> **Made with Wool · Tested for Everything**
