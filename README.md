# 🤖 Test-Agent

>**AI Testing Agent Framework · Open-Source · Multi-LLM · One-command deploy**

[![CI](https://github.com/Wool-xing/Test-Agent/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Wool-xing/Test-Agent/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/Wool-xing/Test-Agent?style=social)](https://github.com/Wool-xing/Test-Agent/stargazers)
[![Status: stable](https://img.shields.io/badge/status-brightgreen.svg)](VERSION)
[![中文](https://img.shields.io/badge/Lang-中文-red.svg)](README.zh-CN.md)

**English**| [简体中文](README.zh-CN.md)

---

Test-Agent turns any software, EXE, APK, Docker image, or API into a**fully tested project**— autonomous from requirement parsing to PoC-validated bug reports, powered by 16 AI agents with a ManifestV2 single-source architecture.

-**All-platform**— Web · API · Android · iOS · WeChat Mini Program · Windows · macOS · Linux · Automotive · IoT · AI/LLM · Blockchain
-**All-protocol**— HTTP(S) · gRPC · WebSocket · TCP/UDP · GraphQL · MQTT · CAN-bus · Kafka · Modbus · …
-**Multi-LLM no lock-in**— 6 built-in (Claude / OpenAI / Gemini / Qwen / DeepSeek / Ollama) + OpenAI-compatible fallback for any provider, 3 env vars, zero code
-**Learn while using**— `--mode learn` outputs theory references at every step (22 KB cards across 13 domains)
-**Safe-by-default**— sandboxed exec · PII scrub · prompt-injection scan · hash-chain audit trail · SSO + RBAC

---

## 🚀 Quick Start

> Prerequisite: Python 3.x. Git & Node.js auto-installed if missing (winget / brew / apt / apk).
>
> ⚠️ This project includes offensive security tools (pentest skill / SSRF probes / AI adversarial templates). Read [SECURITY.md](SECURITY.md) before running pentest or AI-adversarial workflows.

```bash
# Download install script

curl -fsSL -o install.py https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.py

# Deploy to your project directory (any path works)

python install.py D:\Test-Agent              # Windows example, any drive or folder
python install.py ~/test-agent-project       # macOS / Linux example, any folder

```text

>**Windows users**: if curl fails with `CRYPT_E_NO_REVOCATION_CHECK`, use PowerShell:
> ```powershell
> Invoke-WebRequest -Uri https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.py -OutFile install.py
> python install.py D:\Test-Agent   # example, any drive or folder works
> ```

**Expected duration**: ~10–15 min (includes pip deps + Playwright browser). CN networks auto-use Tsinghua PyPI mirror.

After deployment, outputs under `workspace/`: test cases (Excel + xmind + markmap + opml) + Word report + decision logs.

**Next**: `cp config/.env.example .env` → edit `.env` → run with any AI tool supporting AGENTS.md/SKILL.md standard, or `tagent run "your PRD"`

## 🖥 Desktop App (V2 — Tauri)

[![Download](https://img.shields.io/badge/Download-Latest%20Release-blue)](https://github.com/Wool-xing/Test-Agent/releases)

No Python / Node / Docker required. Tauri 2 desktop — ~10MB binary, Windows/macOS/Linux.

## 📸 Screenshots

| Upload | Dashboard | Catalog | History |
| -------- | ----------- | --------- | --------- |
| ![Upload](docs/assets/screenshots/upload.png) | ![Dashboard](docs/assets/screenshots/dashboard.png) | ![Catalog](docs/assets/screenshots/catalog.png) | ![History](docs/assets/screenshots/history.png) |

## 📚 Documentation

| Audience | Read |
| ---------- | ------ |
|**First-time user**| [Quick start](docs/getting-started/INDEX.md) → [Deploy](docs/getting-started/部署说明.md) |
|**QA engineer**| [User manual](docs/getting-started/使用手册.md) → [Skill catalog](ai/skills/) |
|**Architect / SRE**| [Architecture deep-dive](docs/charter/06-test-architecture.md) → [Runtime modules](runtime/INDEX.md) |
|**Security researcher**| [Pentest expert](ai/agents/15-渗透测试.md) → [pentest-coordinator](ai/skills/pentest-coordinator.md) |
|**Automotive tester**| [Automotive expert](ai/agents/16-车载测试.md) → [ASIL workflow](ai/skills/automotive-test.md) |
|**Contributor**| [CONTRIBUTING.md](CONTRIBUTING.md) → [Marketplace](deploy/marketplace/INDEX.md) |

## 📊 Coverage

-**Product types**: Web · API · Mobile · Desktop · IoT · AI · Blockchain · Automotive · Embedded · Serverless
-**Test types**: functional / performance / security / compatibility / weak-network / stability / accessibility / visual / i18n / chaos / mutation / AI-specific / compliance
-**Quality gates**: 6 centralized gates (smoke / regression / performance / security / CI / release) with automated evaluation

## 📂 Project Structure

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

```text

See [FULL_GUIDE.md](FULL_GUIDE.md) and [CHANGELOG.md](CHANGELOG.md) for details.

## 🛠️ Tech Stack

pytest 8.3 · Playwright 1.59 · Appium 5.3 · JMeter 5.6 · Allure · OpenCV · SQLAlchemy 2.0 · MCP 1.0 · LiteLLM · FastAPI · React 18 · Postgres+pgvector · Docker

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Community marketplace passes 4-gate verification.

## 📜 License

MIT License — see [LICENSE](LICENSE). Upstream components retain their own licenses; see [NOTICE.md](NOTICE.md).

---

>**Made for testers · Built with testers · Tested by testers**
