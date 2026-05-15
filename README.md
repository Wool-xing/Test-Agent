# 🤖 Test-Agent

> **AI Testing Agent Framework · Open-Source · Multi-LLM · 5-second setup**

[![CI](https://github.com/Wool-xing/Test-Agent/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Wool-xing/Test-Agent/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/Wool-xing/Test-Agent?style=social)](https://github.com/Wool-xing/Test-Agent/stargazers)
[![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)](VERSION)
[![中文](https://img.shields.io/badge/Lang-中文-red.svg)](README.zh-CN.md)

**English** | [简体中文](README.zh-CN.md)

---

## ⚡ 30-second demo

```bash
git clone https://github.com/Wool-xing/Test-Agent.git
bash Test-Agent/install.sh ~/test-agent-project

# Optional: enable autonomous runtime (alpha — 5 LLM-driven agents wired)
cd Test-Agent/runtime && pip install -e .
tagent demo            # 0 API key · stub LLM · 30s end-to-end
```

Outputs: test cases (Excel + xmind + markmap + opml) + Word report + decision logs, all under `workspace/`.

Ready to run on your project?

```bash
tagent init --preset 国内-web    # or: minimal / saas-web / mobile-android / security-pentest
# → produces .env + tagent.yml + STARTUP.md (5-step onboarding guide)
```

Matrix-driven config: 8 test types × 6 platforms × 5 LLMs × 6 trackers × 6 channels (8640 combinations on paper; not all are e2e-validated in this alpha). See [`04-配置文件/templates/INDEX.md`](04-配置文件/templates/INDEX.md).

---

## What is Test-Agent?

Test-Agent turns any software, EXE, APK, Docker image, or API into a **fully tested project** — autonomous from requirement parsing to PoC-validated bug reports. Built for QA teams, security researchers, automotive testers, and anyone who wants to **use AI testing while learning the theory behind it**.

- **16 expert agents** (11 production + 5 script — V1.x rollout 收尾,见 [ROADMAP.md](ROADMAP.md)) — functional · security · mobile · desktop · AI model · automotive · pentest …
- **32 business skills** (8 production + 7 script + 15 rollout + 2 vision — see [ROADMAP.md](ROADMAP.md)) **+ 3 meta-skills** — TDD · E2E · regression · pentest · car-CAN-bus · eval-harness · …
- **49 production utils** — pytest · Playwright · JMeter · Appium · Burp · Allure · OpenCV · …
- **Multi-LLM** — Claude / OpenAI / Gemini / Qwen / DeepSeek / Ollama(local,no vendor lock-in)
- **BugTracker** — 1 active adapter (Zentao); 5 planned (Jira · GitHub · GitLab · Linear · Webhook, see roadmap)
- **6 notify channels** — WeChat Work · Lark/Feishu · DingTalk · Slack · Email · MS Teams
- **MCP integration** — 6 server modules implemented (test-orchestrator active by default; 5 others under `_pending_servers_v1_2_0_alpha` in `.mcp.json`)
- **Self-test scaffolding** — L1 lint + L2 mock CI active in CI; L3 real-LLM + L4 weekly cron require `ANTHROPIC_API_KEY` secret (not configured in this repo by default)

## 🚀 Install (alpha)

> ⚠️ This project includes attack-surface utilities (pentest skills / SSRF probes / AI adversarial templates). See [SECURITY.md](SECURITY.md) for authorization requirements before running pentest or AI-adversarial workflows.

```bash
curl -fsSL https://raw.githubusercontent.com/Wool-xing/Test-Agent/main/install.sh | bash -s -- /path/to/your-test-project
```

**Expected duration**: ~10-15 min on global PyPI; ~10-15 min on CN networks (Tsinghua mirror auto-configured if `LANG=zh_*` or timezone `+0800`). Override via `export PIP_INDEX_URL=<url>` before running.

Then `tagent init` to scaffold `.env`/`tagent.yml`/`STARTUP.md` — no more 30 mins of hand-editing.

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

Coverage is broad across the listed categories above. The **"95%" figure is aspirational, not a measured number** — domain-specific gates (DO-178C avionics / HIPAA medical / IEC 61508 industrial) currently ship as **skeleton** compliance YAML profiles only.

## 📖 Design Documents

For project design rationale, architecture decisions, and methodology rationale, see [FULL_GUIDE.md](FULL_GUIDE.md). Inspirations from upstream OSS (hermes / gbrain / karpathy / etc.) are credited in [NOTICE.md](NOTICE.md).

## 📂 Project Structure

```text
Test-Agent/
├── 00-项目导航.md           ← 5-dimension category guide
├── 01-快速开始/             ← user manual / deploy / config / deliverables
├── 02-专家定义/             ← 16 expert agents (11 production + 5 script, V1.x rollout 收尾)
├── 03-技能定义/             ← 32 business skills (8 production + 7 script + 15 rollout + 2 vision) + 3 meta-skills
├── 04-配置文件/             ← conftest / pytest.ini / .env / .mcp.json
├── 05-代码示例/             ← 49 production utils
├── 06-CICD集成/             ← GitHub Actions + Jenkins
├── runtime/                ← V1.x runtime layer (router / orchestrator / MCP / web / scheduler / subagent / learning_loop / backends / gateway / tutor / essence_watcher / marketplace)
├── docs/charter/           ← Vision charter (7 split files: vision-dimensions / coverage-matrix / agentchat-protocol / skills-bugtracker / install-deploy / test-architecture / runtime-license)
├── docs/theory/            ← 22 teaching KB cards across 13 categories
├── profiles/compliance/    ← 10 industry compliance YAML profiles
├── marketplace/            ← Community skills / agents / mcp / hooks (4 lanes, 4-gate verify)
├── install.sh              ← one-line deploy
├── README.md               ← This file
├── FULL_GUIDE.md           ← Full engineering guide
├── CHANGELOG.md            ← Version log
└── LICENSE / SECURITY.md / CONTRIBUTING.md / CODE_OF_CONDUCT.md
```

> **Skill Lifecycle (meta-tools)**:
> - **Current (A · methodology reference)**: Each subdir's SKILL.md serves as skill-design reference material.
> - **Usable today (B · perspective extension)**: Use `nuwa-skill` to distill new mental-model perspectives (Naval / Munger / Feynman); use `darwin-skill` to optimize perspective skills.
> - **V2.x Roadmap (C · testing-domain adaptation)**: Re-target nuwa as a test skill/agent distiller; re-target darwin's 8-dim scoring to testing domain.

## 📚 Documentation

| Audience | Read |
|----------|------|
| **First-time user** | [Quick start](01-快速开始/INDEX.md) → [Deploy](01-快速开始/部署说明.md) |
| **QA engineer** | [User manual](01-快速开始/使用手册.md) → [Skill catalog](03-技能定义/) |
| **Architect / SRE** | [Architecture deep-dive](docs/charter/06-test-architecture.md) → [Runtime](docs/charter/07-runtime-license.md) → [Runtime modules](runtime/INDEX.md) |
| **Security researcher** | [Pentest expert](02-专家定义/15-渗透测试.md) → [pentest-coordinator](03-技能定义/pentest-coordinator.md) |
| **Automotive tester** | [Automotive expert](02-专家定义/16-车载测试.md) → [ASIL workflow](03-技能定义/automotive-test.md) |
| **Contributor** | [CONTRIBUTING.md](CONTRIBUTING.md) → [Marketplace](marketplace/INDEX.md) |

## 🛠️ Tech Stack

pytest 8.3 · Playwright 1.59 · Appium 5.3 · pywinauto · JMeter 5.6 · Allure · Airtest · OpenCV · Faker · SQLAlchemy 2.0 · MCP 1.0 · LiteLLM · Prefect · FastAPI · React 18 · Tailwind · Postgres+pgvector · MinIO · OpenTelemetry · Loguru · Docker Compose · GitHub Actions / Jenkins

## 🤝 Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the contribution workflow.

Community marketplace contributions (`marketplace/`) pass through **4 verification gates** (current implementation): signature presence (planned) → injection-regex scan → AST syntax-parse (V1.x: replace with real Docker sandbox) → frontmatter-presence score (V1.x: swap for real darwin-skill evaluator).

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
