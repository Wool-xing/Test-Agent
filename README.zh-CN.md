# 🤖 Test-Agent

> **AI 测试 Agent 框架 · 开源 · 多 LLM · 一键部署**

[![CI](https://github.com/Wool-xing/Test-Agent/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Wool-xing/Test-Agent/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/Wool-xing/Test-Agent?style=social)](https://github.com/Wool-xing/Test-Agent/stargazers)
[![Status: stable](https://img.shields.io/badge/status-brightgreen.svg)](VERSION)
[![English](https://img.shields.io/badge/Lang-English-blue.svg)](README.md)

[English](README.md) | **简体中文**

---

Test-Agent 将任何软件 / EXE / APK / Docker 镜像 / API 变成**完整测试过的项目**——从需求解析到 PoC 验证的 Bug 报告，由 16 个 AI Agent 全自主完成，ManifestV2 单源真理架构驱动。

- **全平台** — Web · API · Android · iOS · 微信小程序 · Windows · macOS · Linux · 车载 · IoT · AI/LLM · 区块链
- **全协议** — HTTP(S) · gRPC · WebSocket · TCP/UDP · GraphQL · MQTT · CAN-bus · Kafka · Modbus · …
- **多 LLM 无锁定** — 内置 6 厂商（Claude / OpenAI / Gemini / Qwen / DeepSeek / Ollama）+ OpenAI 兼容通道接任意厂商，3 个 env 零代码
- **边用边学** — `--mode learn` 每步含理论引用（22 卡跨 13 大类）
- **safe-by-default** — 沙箱执行 · PII 脱敏 · Prompt 注入扫描 · 哈希链审计 · SSO + RBAC

---

## 🚀 快速开始

> 前提：Python 3.x。Git / Node.js 缺失时自动安装（winget / brew / apt / apk）。
>
> ⚠️ 本项目含攻击面工具（渗透 skill / SSRF 探针 / AI 对抗模板）。运行 pentest 或 AI-adversarial 工作流前请阅 [SECURITY.md](SECURITY.md)。

```bash
# 下载部署脚本
curl -fsSL -o install.py https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.py

# 部署到你的项目目录（路径可任意指定）
python install.py D:\Test-Agent              # Windows 示例，可改为其他盘符或目录
python install.py ~/test-agent-project       # macOS / Linux 示例，可改为其他目录
```

> **Windows 用户**：如果 curl 报 `CRYPT_E_NO_REVOCATION_CHECK`，改用 PowerShell：
> ```powershell
> Invoke-WebRequest -Uri https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.py -OutFile install.py
> python install.py D:\Test-Agent   # 示例，可改为其他盘符或目录
> ```

**预期耗时**：约 10–15 min（含 pip 依赖 + Playwright 浏览器）。CN 网络自动配清华 PyPI 镜像。

部署后 `workspace/` 下即见产物：测试用例（Excel + xmind + markmap + opml）+ Word 报告 + 决策日志。

**下一步**：编辑 `.env` → 用任意支持 AGENTS.md/SKILL.md 标准的 AI 工具运行，或 `tagent run "你的需求文档"`

## 🖥 桌面应用（V2 — Tauri）

[![Download](https://img.shields.io/badge/下载-最新版本-blue)](https://github.com/Wool-xing/Test-Agent/releases)

无需 Python / Node / Docker。Tauri 2 桌面 — ~10MB 安装包，Windows/macOS/Linux。

## 📸 截图

| 上传 | 仪表盘 | 目录 | 历史 |
| ------ | -------- | ------ | ------ |
| ![上传](docs/assets/screenshots/upload.png) | ![仪表盘](docs/assets/screenshots/dashboard.png) | ![目录](docs/assets/screenshots/catalog.png) | ![历史](docs/assets/screenshots/history.png) |

## 📚 文档导航

| 角色 | 阅读 |
| ------ | ------ |
| **首次用户** | [快速开始](docs/getting-started/INDEX.md) → [部署说明](docs/getting-started/部署说明.md) |
| **QA 工程师** | [使用手册](docs/getting-started/使用手册.md) → [Skill 目录](ai/skills/) |
| **架构师 / SRE** | [架构深度](docs/charter/06-test-architecture.md) → [Runtime 模块](runtime/INDEX.md) |
| **安全研究员** | [渗透专家](ai/agents/15-渗透测试.md) → [pentest-coordinator](ai/skills/pentest-coordinator.md) |
| **车载测试** | [车载专家](ai/agents/16-车载测试.md) → [ASIL 工作流](ai/skills/automotive-test.md) |
| **贡献者** | [CONTRIBUTING.md](CONTRIBUTING.md) → [Marketplace](deploy/marketplace/INDEX.md) |

## 📊 覆盖度

- **产品形态**: Web · API · 移动 · 桌面 · IoT · AI · 区块链 · 车载 · 嵌入式 · Serverless
- **测试类型**: 功能 / 性能 / 安全 / 兼容 / 弱网 / 稳定性 / 可访问性 / 视觉 / i18n / 混沌 / 变异 / AI 特有 / 合规
- **质量门禁**: 6 个集中管理门禁（冒烟 / 回归 / 性能 / 安全 / CI / release），自动化评估

## 📂 项目结构

```text
Test-Agent/
├── specs/              ← ManifestV2 单源真理（16 agents + 32 skills）
├── ai/                 ← AI 模式界面层（agents/ + skills/ .md 定义）
├── runtime/            ← Python 运行时引擎（router · orchestrator · MCP · learning · intelligence）
├── engine/             ← Rust 核心（DAG executor · sandbox · PyO3 bridge）
├── utils/              ← 92 共享工具（12 子目录，双模式共用）
├── sdk/                ← Plugin SDK（scaffold · validate · install）
├── apps/               ← 分发应用（desktop-v2: Tauri, desktop: Electron, mobile: Capacitor）
├── deploy/             ← 部署物料（config 模板 · profiles 合规 · marketplace）
├── docs/               ← 文档（getting-started · charter · theory · site: VitePress）
├── ci/                 ← CI/CD（GitHub Actions 18 jobs · Jenkins）
├── scripts/            ← 开发脚本（迁移 · 渲染 · 一致性检查）
├── examples/           ← 示例 PRD + demo 项目
├── graphify-out/       ← 知识图谱输出（5,388 节点 · 8,902 边）
├── requirements/       ← Python 依赖
├── workspace/          ← 运行时产出（测试报告 · 决策日志）
├── install.py          ← 跨平台一键部署
├── VERSION             ← 版本号单源
└── README.md
```

详见 [FULL_GUIDE.md](FULL_GUIDE.md) 和 [CHANGELOG.md](CHANGELOG.md)。

## 🛠️ 技术栈

pytest 8.3 · Playwright 1.59 · Appium 5.3 · JMeter 5.6 · Allure · OpenCV · SQLAlchemy 2.0 · MCP 1.0 · LiteLLM · FastAPI · React 18 · Postgres+pgvector · Docker

## 🤝 贡献

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。社区 marketplace 走 4 关验证。

## 📜 许可

MIT License — 详见 [LICENSE](LICENSE)。上游组件保留各自协议，详见 [NOTICE.md](NOTICE.md)。

---

> **为测试而生 · 与测试者共建 · 由测试者测试**
