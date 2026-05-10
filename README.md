# 🤖 Test-Agent 工作流

> **项目代号**：`test-agent-team` · **版本**：V1.0.0 · **License**：MIT
>
> **Claude Code 驱动的全链路软件测试自动化工作流**
> 14 Agent · 13 Skill · 49 Utils · 全平台覆盖（Web/API/移动/桌面/小程序/游戏/IoT/AI）· 一键部署

[![CI](https://github.com/Wool-xing/Test-Agent/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Wool-xing/Test-Agent/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-1.0+-purple.svg)](https://docs.anthropic.com/claude-code)
[![Pytest](https://img.shields.io/badge/Pytest-8.3-green.svg)](https://pytest.org)
[![JMeter](https://img.shields.io/badge/JMeter-5.6.3-orange.svg)](https://jmeter.apache.org)
[![Dependabot](https://img.shields.io/badge/Dependabot-enabled-brightgreen.svg)](https://github.com/Wool-xing/Test-Agent/security/dependabot)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/Wool-xing/Test-Agent/main)](https://github.com/Wool-xing/Test-Agent/commits/main)

---

## ✨ 核心特性

- 🎯 **9 核心 + 5 平台扩展 = 14 个测试专家 Agent**，test-lead 智能调度
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
4. ✅ 部署 14 agent + 13 skill + 49 utils + CI/CD 文件
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
