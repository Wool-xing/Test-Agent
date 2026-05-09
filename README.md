# 🤖 Test-Agent 工作流

> **Claude Code 驱动的全链路软件测试自动化工作流**
> 14 Agent · 13 Skill · 24 Utils · 全平台覆盖（Web/API/移动/桌面/小程序/游戏/IoT/AI）· 一键部署

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-1.0+-purple.svg)](https://docs.anthropic.com/claude-code)
[![Pytest](https://img.shields.io/badge/Pytest-7.4-green.svg)](https://pytest.org)
[![JMeter](https://img.shields.io/badge/JMeter-5.6.3-orange.svg)](https://jmeter.apache.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ 核心特性

- 🎯 **9 核心 + 5 平台扩展 = 14 个测试专家 Agent**，test-lead 智能调度
- 📋 **13 个一键技能**：冒烟 / 回归 / 完整流程 / 用例生成 / 性能 / Bug 提交 / 多平台专项
- 🌐 **全链路覆盖**：Web · API · Android/iOS · 微信小程序 · Windows EXE · macOS · Electron · 游戏 · IoT · AI/LLM
- 📡 **20+ 协议**：HTTP · WebSocket · gRPC · TCP/UDP · GraphQL · SOAP · MQTT · Kafka · Modbus · 串口 等
- 📄 **多格式 PRD**：md · pdf · docx · xlsx · zip · png · html · URL（自动平台识别 + 路由）
- 🚦 **分层质量门禁**：smoke ≥95% · regression ≥90% · 覆盖率 ≥80% · 性能 TPS/P95 双模式
- 🔁 **JMeter 双模式**：CI 快验（5 并发）+ Release 完整压测（50 并发，含基线对比）
- 📦 **一键部署**：单行 curl 命令，自动建目录、装依赖、配 CI

---

## 🚀 Quick Start（一行命令）

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR-USER/Test-Agent工作流搭建/main/install.sh | bash -s -- /path/to/your-test-project
```

`install.sh` 自动完成：

1. ✅ 检查工具（git/python3/node/npm/Java）
2. ✅ 装 Claude Code CLI
3. ✅ 克隆模板
4. ✅ 部署 14 agent + 13 skill + 24 utils + CI/CD 文件
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

```
Test-Agent工作流搭建/
├── 00-项目导航.md           ← 5 维度分类速查
├── 01-快速开始/             ← 使用手册 / 部署 / 配置清单 / 交付物
├── 02-专家定义/             ← 14 个 Agent（核心 9 + 平台扩展 5）
├── 03-技能定义/             ← 13 个 Skill（通用 8 + 平台 5）
├── 04-配置文件/             ← conftest / pytest.ini / .env / .mcp.json / requirements
├── 05-代码示例/             ← 24 个 utils（核心 11 + 平台 9 + 协议 2 + 输入 1 + __init__）
├── 06-CICD集成/             ← GitHub Actions + Jenkins
├── install.sh               ← 一键部署脚本
└── README.md / Test-Agent工作流搭建.md
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
| [00-项目导航.md](00-项目导航.md) | 按职责分类速查（强烈推荐） |
| [01-快速开始/使用手册.md](01-快速开始/使用手册.md) | 启动指引 + 13 skill 详解 + FAQ |
| [01-快速开始/部署说明.md](01-快速开始/部署说明.md) | 跨平台部署（Win/Mac/Linux）+ Java/JMeter/Allure 安装 |
| [01-快速开始/配置清单.md](01-快速开始/配置清单.md) | .env 全字段 + Secrets / Webhook 申请 |
| [01-快速开始/交付物清单.md](01-快速开始/交付物清单.md) | 测试计划 / 报告 / Bug 提交位置 |
| [Test-Agent工作流搭建.md](Test-Agent工作流搭建.md) | 单文件全嵌入版（备查/分发） |

---

## 🛠️ 技术栈

| 类型 | 工具 |
|------|------|
| 测试框架 | pytest 7.4 + pytest-xdist + pytest-rerunfailures + pytest-mock + pytest-playwright |
| UI 自动化 | Playwright 1.40（Web/Electron）/ Appium 4.0（移动）/ pywinauto 0.6（Windows EXE）/ PyAutoGUI（macOS） |
| API | requests 2.31 + websocket-client + websockets + grpcio + paho-mqtt + paramiko + kafka-python + pika |
| 性能 | JMeter 5.6.3（主） + Locust 2.25（备） |
| 视觉 | Airtest 1.3 + OpenCV 4.8 + scikit-image + Tesseract |
| AI | scikit-learn + scipy（漂移） + LLM 评估 |
| 数据 | Faker + Factory Boy + SQLAlchemy + pdfplumber + python-docx + openpyxl |
| 报告 | Allure 2.13 + python-docx 1.1 + 三端 webhook（企微/飞书/钉钉） |
| Bug | 禅道 SDK |
| CI/CD | GitHub Actions + Jenkins |
| AI 模型 | Claude 4.x（Opus 4.7 / Sonnet 4.6 / Haiku 4.5，由 Claude Code 默认管理） |

---

## 🔄 跨工具兼容性

Claude Code 是**默认推荐**而非强制：

- ✅ **`utils/` + pytest + JMeter + CI** 完全跨工具（纯 Python / 标准 CI 文件）
- ⚠️ **`.claude/agents/` + `.claude/skills/`** 是 Claude Code 独有，迁移其他工具（Cursor / Continue）需重写为对应格式
- 🔌 **`.mcp.json`** 是 MCP 开放协议，Claude Desktop / Cursor 部分支持

---

## 📊 全链路覆盖矩阵

| 平台 | 工具栈 | 状态 |
|------|-------|------|
| Web（PC + 移动 H5） | Playwright | ✅ |
| REST/GraphQL/SOAP API | requests / protocol_helper | ✅ |
| Android APP（含 Monkey 稳定性） | Appium + adb | ✅ |
| iOS APP | Appium + XCUITest | ✅ |
| 微信/支付宝小程序 | 微信开发者工具 CLI | ✅ |
| Windows EXE（含 WS 协议） | pywinauto + websocket_helper | ✅ |
| macOS GUI | PyAutoGUI + AppleScript | ✅ |
| Electron | Playwright Electron API | ✅ |
| 游戏/Canvas/WebGL | Airtest + OpenCV | ✅ |
| OCR + 视觉回归 | Tesseract + SSIM | ✅ |
| 性能压测（双模式） | JMeter 5.6.3 | ✅ |
| IoT/嵌入式 | SSH + 串口 + MQTT + Modbus | ✅ |
| 音视频 | FFmpeg + ffprobe | ✅ |
| 链路追踪 | Jaeger / Zipkin | ✅ |
| 消息队列 | Kafka + RabbitMQ | ✅ |
| AI/ML 模型 + LLM | scikit-learn + scipy + LLM eval | ✅ |
| Bug 闭环 | 禅道 | ✅ |
| 三端通知 | 企业微信 + 飞书 + 钉钉 webhook | ✅ |
| CI/CD | GitHub Actions + Jenkins | ✅ |

**覆盖率约 90%**

---

## 🤝 Contributing

欢迎 PR：

1. Fork → 新建分支
2. 在 `02-专家定义/` 加 agent 或 `03-技能定义/` 加 skill
3. 同步 `00-项目导航.md` + 各子目录 `README.md` + `install.sh`
4. 提交 PR

详细添加流程见各子目录 `README.md` 末尾"添加新 X 流程"。

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

> **Made with Claude · Tested for Everything**
