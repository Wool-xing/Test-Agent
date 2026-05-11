# 🤖 Test-Agent

> **AI Testing Agent Framework · Open-Source · Multi-LLM · Learn-While-Using**

[![CI](https://github.com/Wool-xing/Test-Agent/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Wool-xing/Test-Agent/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/Wool-xing/Test-Agent?style=social)](https://github.com/Wool-xing/Test-Agent/stargazers)
[![中文](https://img.shields.io/badge/Lang-中文-red.svg)](README.zh-CN.md)

**English** | [简体中文](README.zh-CN.md)

---

## What is Test-Agent?

Test-Agent turns any software, EXE, APK, Docker image, or API into a **fully tested project** — autonomous from requirement parsing to PoC-validated bug reports. Built for QA teams, security researchers, automotive testers, and anyone who wants to **use AI testing while learning the theory behind it**.

- **16 expert agents** (functional / security / mobile / desktop / AI model / automotive / pentest …)
- **34 reusable skills** (TDD / E2E / regression / pentest / car-can-bus / eval-harness …)
- **49 production utils** (pytest / Playwright / JMeter / Appium / Burp / Allure / OpenCV …)
- **Multi-LLM** (Claude, OpenAI, Gemini, Qwen, DeepSeek, Ollama — no vendor lock-in)
- **MCP-native** (6-server suite: test-orchestrator / protocol-adapter / evidence-vault / defect-tracker / knowledge-base / compliance-checker)

## ✨ 30-second Demo

> _Demo gif coming next release._
>
> Until then:
> ```bash
> tagent run "test ./app.exe" --mode learn --lang zh
> ```
> Every step explained with theory references + alternatives considered + further reading.

## 🚀 Install

```bash
curl -fsSL https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.sh | bash -s -- /path/to/your-test-project
```

Or local:

```bash
git clone https://github.com/Wool-xing/Test-Agent.git
cd Test-Agent && bash install.sh /path/to/your-test-project
```

Three steps to first test:

```bash
cd /path/to/your-test-project
vim .env                    # fill 8 required fields (LLM key, bug tracker, webhook)
claude /login               # first-time Claude login
claude                      # start
> /smoke-test               # 10-min P0 smoke
```

## 🎯 5 Key Capabilities

1. **All-platform** — Web / API / Android / iOS / WeChat-miniprogram / Windows EXE / macOS / Linux / Electron / game / IoT / audio-video / AI/LLM / blockchain / 车载
2. **All-protocol** — HTTP(S) / gRPC / WebSocket / TCP / UDP / GraphQL / SOAP / MQTT / SSH / serial / Kafka / RabbitMQ / Modbus / CAN-bus / SOME-IP / DoIP / UDS
3. **Multi-LLM no lock-in** — switch with `tagent model` between Claude / OpenAI / Gemini / Qwen / DeepSeek / Ollama
4. **Learn while using** — `--mode learn` outputs every step with theory references (22 KB cards across 13 domains: tools / coding / foundation / strategy / methods / protocols / platforms / gates / security / AI testing / compliance / process / build-your-own)
5. **Safe-by-default** — sandboxed exec / PII scrub / runtime prompt-injection scan / 4-gate marketplace verify / decisions audit trail

## 📊 Coverage

- **Product types**: Web · API · Mobile · Desktop · IoT · AI · Blockchain · Vehicle · Embedded · Serverless
- **Test types**: functional / performance / security / compatibility / weak-network / stability / reliability / accessibility / contract / visual / i18n / observability / chaos / mutation / AI-specific (hallucination / prompt-injection / drift / fairness) / compliance
- **Test design methods**: equivalence-partitioning · boundary-value · decision-table · state-transition · pairwise · orthogonal · exploratory SBTM · risk-based · TDD · BDD · ATDD
- **Quality gates**: smoke → regression → performance_ci_quick → performance_full → release (5-layer)

Total ≈ **95% coverage** — remaining 5% (DO-178C avionics / HIPAA medical / IEC 61508 industrial) added by your domain experts.

## 🏛️ Charter-Driven

Test-Agent ships with a 31-section **charter** (`CHARTER.md`-equivalent) covering:

- §10–§12 · Soul (3 axioms + 5 inscriptions + 16 key terms)
- §13–§17 · Architecture (experts / skills / installs / darwin self-evolution / AgentChat / MCP)
- §18–§21 · Methodology (9-cluster map / test pyramid 2024 / 18 closed-loop rules / 9-industry adapter / 50+ test types / 4 depth levels)
- §22 · Hermes-inspired (scheduler / subagent / learning-loop / 7 backends / 8 platforms)
- §23 · Teaching layer (KB 13 categories + anti-hallucination 3 layers + bilingual)
- §24 · GBrain-inspired (KB self-wiring graph + eval replay + PII scrub)
- §25–§26 · Pentest & Automotive verticals
- §27 · Karpathy 4 principles (think-before / simplicity-first / surgical / goal-driven)
- §28 · ECC test hardening (tdd-workflow / verification-loop / e2e / eval-harness / security-review)
- §29 · Essence watcher (auto-track upstream OSS for delta extraction)
- §30 · Marketplace 4-lane (4-gate security)
- §31 · Build-your-own-X learning layer

## 📂 Project Structure

```text
Test-Agent/
├── 00-项目导航.md           ← 5-dimension category guide
├── 01-快速开始/             ← user manual / deploy / config / deliverables
├── 02-专家定义/             ← 16 expert agents
├── 03-技能定义/             ← 34 skills (incl. darwin-skill / karpathy-guidelines upstream)
├── 04-配置文件/             ← conftest / pytest.ini / .env / .mcp.json
├── 05-代码示例/             ← 49 production utils
├── 06-CICD集成/             ← GitHub Actions + Jenkins
├── runtime/                ← V1.x runtime layer (router / orchestrator / MCP / web / scheduler / subagent / learning_loop / backends / gateway / tutor / essence_watcher / marketplace)
├── docs/theory/            ← 22 teaching KB cards across 13 categories
├── profiles/compliance/    ← 10 industry compliance YAML profiles
├── marketplace/            ← Community skills / agents / mcp / hooks (4 lanes, 4-gate verify)
├── install.sh              ← one-line deploy
├── README.md               ← This file
├── FULL_GUIDE.md           ← Full engineering guide
├── CHANGELOG.md            ← Version log
└── LICENSE / SECURITY.md / CONTRIBUTING.md / CODE_OF_CONDUCT.md
```

## 📚 Documentation

| Audience | Read |
|----------|------|
| **First-time user** | [Quick start](01-快速开始/INDEX.md) → [Deploy](01-快速开始/部署说明.md) |
| **QA engineer** | [User manual](01-快速开始/使用手册.md) → [Skill catalog](03-技能定义/) |
| **Architect / SRE** | [Architecture deep-dive](FULL_GUIDE.md) → [Runtime](runtime/INDEX.md) |
| **Security researcher** | [Pentest expert](02-专家定义/15-渗透测试.md) → [pentest-coordinator](03-技能定义/pentest-coordinator.md) |
| **Automotive tester** | [Automotive expert](02-专家定义/16-车载测试.md) → [ASIL workflow](03-技能定义/automotive-test.md) |
| **Contributor** | [CONTRIBUTING.md](CONTRIBUTING.md) → [Marketplace](marketplace/INDEX.md) |

## 🛠️ Tech Stack

pytest 8.3 · Playwright 1.59 · Appium 5.3 · pywinauto · JMeter 5.6 · Allure · Airtest · OpenCV · Faker · SQLAlchemy 2.0 · MCP 1.0 · LiteLLM · Prefect · FastAPI · React 18 · Tailwind · Postgres+pgvector · MinIO · OpenTelemetry · Loguru · Docker Compose · GitHub Actions / Jenkins

## 🤝 Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full workflow (sync rules + RACI matrix + 6-layer dependency policy + Karpathy 4 principles).

Community marketplace contributions (`marketplace/`) go through **4 safety gates**: signature → injection scan → docker sandbox → darwin-skill scoring.

## 📜 License

MIT License — see [LICENSE](LICENSE).

Upstream components retain their own licenses; see [NOTICE.md](NOTICE.md) for attributions.

## 🙏 Inspirations (essence absorbed)

- [hermes-agent](https://github.com/NousResearch/hermes-agent) — closed learning loop + 7 backends + multi-platform gateway
- [gbrain](https://github.com/garrytan/gbrain) — self-wiring KB graph + eval replay + safe-by-default
- [andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) — 4 LLM-coding principles
- [everything-claude-code](https://github.com/affaan-m/everything-claude-code) — TDD / verification / harness-first
- [pentagi](https://github.com/vxcontrol/pentagi) + [shannon](https://github.com/KeygraphHQ/shannon) — pentest agent black-box + white-box
- [build-your-own-x](https://github.com/codecrafters-io/build-your-own-x) — deep-dive learning path

---

> **Made for testers · Built with testers · Tested by testers**
