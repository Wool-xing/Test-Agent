# 🤖 Test-Agent

> **AI 测试 Agent 框架 · 开源 · 多 LLM · 5 秒上手**

[![CI](https://github.com/Wool-xing/Test-Agent/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Wool-xing/Test-Agent/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/Wool-xing/Test-Agent?style=social)](https://github.com/Wool-xing/Test-Agent/stargazers)
[![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)](VERSION)
[![English](https://img.shields.io/badge/Lang-English-blue.svg)](README.md)

[English](README.md) | **简体中文**

---

## ⚡ 30 秒 demo

```bash
git clone https://github.com/Wool-xing/Test-Agent.git
bash Test-Agent/install.sh ~/test-agent-project

# 可选:启用自主运行时 (alpha — 5 个真 LLM-driven agent)
cd Test-Agent/runtime && pip install -e .
tagent demo            # 0 API key · stub LLM · 30 秒看完整产物
```

产物:测试用例(Excel + xmind + markmap + opml)+ Word 报告 + 决策日志,全在 `workspace/`。

要在自己项目跑?

```bash
tagent init --preset 国内-web    # 或:minimal / saas-web / mobile-android / security-pentest
# → 产 .env + tagent.yml + STARTUP.md(5 步上手指南)
```

矩阵驱动配置:8 测试类型 × 6 平台 × 5 LLM × 6 tracker × 6 通道(理论 8640 组合;并非全部已 e2e 验证)。见 [`04-配置文件/templates/INDEX.md`](04-配置文件/templates/INDEX.md)。

---

## Test-Agent 是什么?

Test-Agent 让任何软件 / EXE / APK / Docker 镜像 / API,变成**完整测试过的项目**——从需求解析到 PoC 验证的 Bug 报告,全自主。为 QA 团队、安全研究员、车载测试工程师、以及任何想**用 AI 测试同时学测试理论**的人而生。

- **16 专家 Agent** — 功能 · 安全 · 移动 · 桌面 · AI 模型 · 车载 · 渗透 ……(当前实装状态见 [ROADMAP.md](ROADMAP.md))
- **33 业务 Skill + 3 元 Skill** — TDD · E2E · 回归 · 渗透 · 车载 CAN · eval-harness ……
- **49 生产工具** — pytest · Playwright · JMeter · Appium · Burp · Allure · OpenCV ……
- **多 LLM** — Claude / OpenAI / Gemini / Qwen / DeepSeek / Ollama(无厂商锁定)
- **BugTracker** — 1 已实装(禅道);5 计划(Jira · GitHub · GitLab · Linear · Webhook,见 roadmap)
- **6 通知渠道** — 企微 · 飞书 · 钉钉 · Slack · 邮件 · Teams
- **MCP 集成** — 6 模块已实现(test-orchestrator 默认启用;其余 5 件套写在 `.mcp.json` 的 `_pending_servers_v1_2_0_alpha` 段)
- **自检脚手架** — L1 lint + L2 mock CI 已在 CI 激活;L3 真 LLM + L4 周自检需配置 `ANTHROPIC_API_KEY` secret(本仓默认未配)

## 🚀 安装 (alpha)

> ⚠️ 本项目含攻击面工具(渗透 skill / SSRF 探针 / AI 对抗模板)。运行 pentest 或 AI-adversarial 工作流前请阅 [SECURITY.md](SECURITY.md) 中的授权要求。

```bash
curl -fsSL https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.sh | bash -s -- /path/to/your-test-project
```

**预期耗时**: 全球 PyPI 约 10-15 min; CN 网络约 10-15 min (自动检测 `LANG=zh_*` 或时区 `+0800` 配清华镜像). 自定义 `export PIP_INDEX_URL=<url>` 覆盖.

然后 `tagent init` 自动生成 `.env`/`tagent.yml`/`STARTUP.md`——不用再花 30 分钟手填字段。

## 🎯 5 大核心能力

1. **全平台** — Web / API / Android / iOS / 微信小程序 / Windows EXE / macOS / Linux / Electron / 游戏 / IoT / 音视频 / AI/LLM / 区块链 / 车载
2. **全协议** — HTTP(S) / gRPC / WebSocket / TCP / UDP / GraphQL / SOAP / MQTT / SSH / 串口 / Kafka / RabbitMQ / Modbus / CAN-bus / SOME-IP / DoIP / UDS
3. **多 LLM 无锁定** — `tagent model` 切换 Claude / OpenAI / Gemini / Qwen / DeepSeek / Ollama
4. **边用边学** — `--mode learn` 每步输出含**理论引用**(22 卡跨 13 大类:工具 / 编程 / 基础理论 / 策略 / 方法 / 协议 / 平台 / 门禁 / 安全 / AI 测试 / 合规 / 流程 / Build-Your-Own)
5. **safe-by-default** — 沙箱 / PII 脱敏 / 运行时 Prompt 注入扫描 / 4 关 Marketplace 验证 / decisions 审计链

## 📊 覆盖度

- **产品形态**:Web · API · 移动 · 桌面 · IoT · AI · 区块链 · 车载 · 嵌入式 · Serverless
- **测试类型**:功能 / 性能 / 安全 / 兼容 / 弱网 / 稳定 / 可靠性 / 可访问性 / 契约 / 视觉 / i18n / 可观测性 / 混沌 / 变异 / AI 特有(幻觉 / Prompt 注入 / 漂移 / 公平性)/ 合规
- **用例设计方法**:等价类 · 边界值 · 判定表 · 状态迁移 · 配对 · 正交 · 探索性 SBTM · 风险驱动 · TDD · BDD · ATDD
- **质量门禁**:冒烟 → 回归 → performance_ci_quick → performance_full → release(5 层)

覆盖面在上述类别广。**「95%」是目标值,不是测量值** — 领域专项门禁(航空 DO-178C / 医疗 HIPAA / 工业 IEC 61508)当前仅以 **skeleton** 合规 YAML 形态提供。

## 📖 设计文档

项目设计思路、架构决策、方法论详见 [FULL_GUIDE.md](FULL_GUIDE.md)。上游开源致谢见 [NOTICE.md](NOTICE.md)。

## 📂 项目结构

```text
Test-Agent/
├── 00-项目导航.md           ← 5 维度分类速查
├── 01-快速开始/             ← 使用手册 / 部署 / 配置 / 交付物
├── 02-专家定义/             ← 16 个专家 Agent
├── 03-技能定义/             ← 33 个业务 Skill + 3 个元 Skill
├── 04-配置文件/             ← conftest / pytest.ini / .env / .mcp.json
├── 05-代码示例/             ← 49 个生产工具
├── 06-CICD集成/             ← GitHub Actions + Jenkins
├── runtime/                ← V1.x 运行时(router/orchestrator/MCP/web/scheduler/subagent/learning_loop/backends/gateway/tutor/essence_watcher/marketplace)
├── docs/charter/           ← 愿景宪章(7 子文件: vision-dimensions / coverage-matrix / agentchat-protocol / skills-bugtracker / install-deploy / test-architecture / runtime-license)
├── docs/theory/            ← 22 教学 KB 卡片跨 13 大类
├── profiles/compliance/    ← 10 行业合规 YAML
├── marketplace/            ← 社区 skills / agents / mcp / hooks(4 lane,4 关验证)
├── install.sh              ← 一键部署
├── README.md / README.zh-CN.md
├── FULL_GUIDE.md           ← 完整工程指南
├── CHANGELOG.md            ← 版本日志
└── LICENSE / SECURITY.md / CONTRIBUTING.md / CODE_OF_CONDUCT.md
```

> **Skill 全生命周期(元工具)**:
> - **现状(A · 方法论参考)**:各子目录 SKILL.md 为 skill 设计参考材料。
> - **当下可用(B · 人物视角扩展)**:用 `nuwa-skill` 蒸馏新人物视角(Naval / 芒格 / 费曼);用 `darwin-skill` 优化人物视角 skill。
> - **V2.x 路线图(C · 测试领域适配)**:改造 nuwa 为测试 skill / agent 蒸馏器;改造 darwin 为测试领域 8 维评分。

## 📚 文档导航

| 角色 | 阅读 |
|------|------|
| **首次用户** | [快速开始](01-快速开始/INDEX.md) → [部署说明](01-快速开始/部署说明.md) |
| **QA 工程师** | [使用手册](01-快速开始/使用手册.md) → [Skill 目录](03-技能定义/) |
| **架构师 / SRE** | [架构深度](docs/charter/06-test-architecture.md) → [Runtime 章节](docs/charter/07-runtime-license.md) → [Runtime 模块](runtime/INDEX.md) |
| **安全研究员** | [渗透专家](02-专家定义/15-渗透测试.md) → [pentest-coordinator](03-技能定义/pentest-coordinator.md) |
| **车载测试** | [车载专家](02-专家定义/16-车载测试.md) → [ASIL 工作流](03-技能定义/automotive-test.md) |
| **贡献者** | [CONTRIBUTING.md](CONTRIBUTING.md) → [Marketplace](marketplace/INDEX.md) |

## 🛠️ 技术栈

pytest 8.3 · Playwright 1.59 · Appium 5.3 · pywinauto · JMeter 5.6 · Allure · Airtest · OpenCV · Faker · SQLAlchemy 2.0 · MCP 1.0 · LiteLLM · Prefect · FastAPI · React 18 · Tailwind · Postgres+pgvector · MinIO · OpenTelemetry · Loguru · Docker Compose · GitHub Actions / Jenkins

## 🤝 贡献

详见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。

社区 marketplace 贡献(`marketplace/`)走 **4 验证关**(当前实现):签名存在性检查(计划中)→ 注入正则扫 → AST 语法解析(V1.x:替换为真 Docker 沙箱)→ frontmatter 检测评分(V1.x:替换为真 darwin-skill 评估器)。

## 📜 许可

MIT License — 详见 [LICENSE](LICENSE)。

上游组件保留各自协议;详见 [NOTICE.md](NOTICE.md) 致谢。

## 🙏 灵感来源(精髓汲取)

- [hermes-agent](https://github.com/NousResearch/hermes-agent) — 封闭学习循环 + 7 后端 + 多平台 gateway
- [gbrain](https://github.com/garrytan/gbrain) — KB 自连图谱 + eval 回放 + safe-by-default
- [andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) — LLM 写代码 4 原则
- [everything-claude-code](https://github.com/affaan-m/everything-claude-code) — TDD / verification / harness-first
- [pentagi](https://github.com/vxcontrol/pentagi) + [shannon](https://github.com/KeygraphHQ/shannon) — 渗透 agent 黑盒+白盒
- [build-your-own-x](https://github.com/codecrafters-io/build-your-own-x) — 深度学习路径

---

> **为测试而生 · 与测试者共建 · 由测试者测试**
