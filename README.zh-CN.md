# 🤖 Test-Agent

> **AI 测试 Agent 框架 · 开源 · 多 LLM · 边用边学**

[![CI](https://github.com/Wool-xing/Test-Agent/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Wool-xing/Test-Agent/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/Wool-xing/Test-Agent?style=social)](https://github.com/Wool-xing/Test-Agent/stargazers)
[![English](https://img.shields.io/badge/Lang-English-blue.svg)](README.md)

[English](README.md) | **简体中文**

---

## Test-Agent 是什么?

Test-Agent 让任何软件 / EXE / APK / Docker 镜像 / API,变成**完整测试过的项目**——从需求解析到 PoC 验证的 Bug 报告,全自主。为 QA 团队、安全研究员、车载测试工程师、以及任何想**用 AI 测试同时学测试理论**的人而生。

- **16 个专家 Agent**(功能 / 安全 / 移动 / 桌面 / AI 模型 / 车载 / 渗透 …)
- **34 个可复用 Skill**(TDD / E2E / 回归 / 渗透 / 车载 CAN 总线 / eval-harness …)
- **49 个生产工具**(pytest / Playwright / JMeter / Appium / Burp / Allure / OpenCV …)
- **多 LLM**(Claude / OpenAI / Gemini / Qwen / DeepSeek / Ollama — 无厂商锁定)
- **MCP 原生**(6 件套:test-orchestrator / protocol-adapter / evidence-vault / defect-tracker / knowledge-base / compliance-checker)

## ✨ 30 秒 Demo

> _Demo gif 下个 release 加_
>
> 暂时:
> ```bash
> tagent run "测 ./app.exe" --mode learn --lang zh
> ```
> 每步带:**原因 + 理论引用 + 替代方案 + 深度阅读**

## 🚀 安装

```bash
curl -fsSL https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.sh | bash -s -- /path/to/your-test-project
```

或本地:

```bash
git clone https://github.com/Wool-xing/Test-Agent.git
cd Test-Agent && bash install.sh /path/to/your-test-project
```

3 步首测:

```bash
cd /path/to/your-test-project
vim .env                    # 填 8 个必填字段(LLM key / Bug tracker / Webhook)
claude /login               # 首次登录 Claude
claude                      # 启动
> /smoke-test               # 10 分钟 P0 冒烟
```

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

总覆盖率 ≈ **95%** — 剩 5%(航空 DO-178C / 医疗 HIPAA / 工业 IEC 61508)由领域专家补。

## 🏛️ 宪章驱动

Test-Agent 带 31 节**项目宪章**,覆盖:

- §10–§12 · 灵魂底色(三公理 + 五条铭文 + 16 关键术语)
- §13–§17 · 架构(专家 / 技能 / 按需安装 / darwin 自进化 / AgentChat / MCP)
- §18–§21 · 方法论(九大簇地图 / 测试金字塔 2024 / 18 闭环约定 / 9 行业适配 / 50+ 测试类型 / 4 深度级)
- §22 · Hermes 派生(scheduler / subagent / learning-loop / 7 后端 / 8 平台)
- §23 · 教学层(KB 13 大类 + 反幻觉 3 层 + 双语)
- §24 · GBrain 派生(KB 自连图谱 + eval 回放 + PII scrub)
- §25–§26 · 渗透 & 车载垂直
- §27 · Karpathy 4 原则(先想再写 / 简洁优先 / 外科手术 / 目标驱动)
- §28 · ECC 测试加固(tdd-workflow / verification-loop / e2e / eval-harness / security-review)
- §29 · Essence 自动汲取(自动追踪上游开源)
- §30 · Marketplace 4 lane(4 关安全门)
- §31 · Build-your-own-X 教学层

## 📂 项目结构

```text
Test-Agent/
├── 00-项目导航.md           ← 5 维度分类速查
├── 01-快速开始/             ← 使用手册 / 部署 / 配置 / 交付物
├── 02-专家定义/             ← 16 个专家 Agent
├── 03-技能定义/             ← 34 个 Skill(含 darwin-skill / karpathy-guidelines upstream)
├── 04-配置文件/             ← conftest / pytest.ini / .env / .mcp.json
├── 05-代码示例/             ← 49 个生产工具
├── 06-CICD集成/             ← GitHub Actions + Jenkins
├── runtime/                ← V1.x 运行时(router/orchestrator/MCP/web/scheduler/subagent/learning_loop/backends/gateway/tutor/essence_watcher/marketplace)
├── docs/theory/            ← 22 教学 KB 卡片跨 13 大类
├── profiles/compliance/    ← 10 行业合规 YAML
├── marketplace/            ← 社区 skills / agents / mcp / hooks(4 lane,4 关验证)
├── install.sh              ← 一键部署
├── README.md / README.zh-CN.md
├── FULL_GUIDE.md           ← 完整工程指南
├── CHANGELOG.md            ← 版本日志
└── LICENSE / SECURITY.md / CONTRIBUTING.md / CODE_OF_CONDUCT.md
```

## 📚 文档导航

| 角色 | 阅读 |
|------|------|
| **首次用户** | [快速开始](01-快速开始/INDEX.md) → [部署说明](01-快速开始/部署说明.md) |
| **QA 工程师** | [使用手册](01-快速开始/使用手册.md) → [Skill 目录](03-技能定义/) |
| **架构师 / SRE** | [架构深度](FULL_GUIDE.md) → [Runtime 模块](runtime/INDEX.md) |
| **安全研究员** | [渗透专家](02-专家定义/15-渗透测试.md) → [pentest-coordinator](03-技能定义/pentest-coordinator.md) |
| **车载测试** | [车载专家](02-专家定义/16-车载测试.md) → [ASIL 工作流](03-技能定义/automotive-test.md) |
| **贡献者** | [CONTRIBUTING.md](CONTRIBUTING.md) → [Marketplace](marketplace/INDEX.md) |

## 🛠️ 技术栈

pytest 8.3 · Playwright 1.59 · Appium 5.3 · pywinauto · JMeter 5.6 · Allure · Airtest · OpenCV · Faker · SQLAlchemy 2.0 · MCP 1.0 · LiteLLM · Prefect · FastAPI · React 18 · Tailwind · Postgres+pgvector · MinIO · OpenTelemetry · Loguru · Docker Compose · GitHub Actions / Jenkins

## 🤝 贡献

详见 [`CONTRIBUTING.md`](CONTRIBUTING.md)(同步铁律 + RACI 矩阵 + 6 层依赖政策 + Karpathy 4 原则)。

社区 marketplace 贡献(`marketplace/`)走 **4 关安全门**:签名 → 注入扫 → Docker 沙箱 → darwin-skill 评分。

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
