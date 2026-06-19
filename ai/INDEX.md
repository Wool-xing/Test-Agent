# AI Mode — Interface Layer

## Purpose
Contains ALL files that AI coding tools read to operate in AI mode — any tool supporting AGENTS.md / SKILL.md standard.
These are **prompt definitions** and **workflow documents** (.md only).
Not executable code.

## Structure
```
ai/
├── agents/                  ← 16 Agent role definitions
│   01-测试主管.md           ← test-lead: orchestrate full flow
│   02-需求分析.md           ← requirements-analyst: parse PRD
│   03-用例设计.md           ← testcase-designer: design test cases
│   04-环境管理.md           ← env-manager: environment health
│   05-数据准备.md           ← data-preparer: generate test data
│   06-自动化脚本.md         ← automation-engineer: Playwright + JMeter
│   07-测试执行.md           ← test-executor: four-phase execution
│   08-Bug管理.md            ← bug-manager: BugTracker submit + track
│   09-报告生成.md           ← report-generator: Allure + Word + notify
│   10-移动测试.md           ← mobile-tester: iOS/Android
│   11-桌面测试.md           ← desktop-tester: Windows/macOS/Linux
│   12-视觉游戏测试.md       ← visual-tester: game + visual regression
│   13-系统集成测试.md       ← system-tester: integration + contract
│   14-AI模型测试.md         ← ai-model-tester: hallucination + fairness
│   15-渗透测试.md           ← pentest-tester: security testing
│   16-车载测试.md           ← automotive-tester: CAN bus + ADAS + OTA
│
└── skills/                  ← 32 Skill workflow definitions
    smoke-test.md            ← P0 smoke test (>=95% gate)
    test-coordinator.md      ← Full flow orchestration
    regression-test.md       ← P0+P1 regression + Flaky + JMeter baseline
    testcase-design.md       ← Default 4-sheet Excel
    python-script-gen.md     ← pytest UI/API script generation
    jmeter-script-gen.md     ← JMeter JMX generation (dual-mode)
    data-preparation.md      ← Test data + JMeter CSV
    zentao-bug-submission.md ← Zentao BugTracker submit
    e2e-testing.md           ← End-to-end testing
    ai-test.md               ← AI model testing
    mobile-test.md           ← Mobile testing
    desktop-test.md          ← Desktop testing
    visual-test.md           ← Visual regression + game testing
    system-test.md           ← System integration testing
    security-review.md       ← Security review
    tdd-workflow.md          ← Test-Driven Development workflow
    verification-loop.md     ← Verification loop
    eval-harness.md          ← Evaluation harness
    build-your-own-x-explorer.md ← Build-your-own-X explorer
    agent-introspection-debugging.md ← Agent introspection
    pentest-api.md           ← API penetration testing
    pentest-coordinator.md   ← Penetration test coordinator
    pentest-exploit.md       ← Exploit execution
    pentest-recon.md         ← Reconnaissance
    pentest-report.md        ← Penetration test report
    pentest-vuln.md          ← Vulnerability assessment
    pentest-web.md           ← Web penetration testing
    automotive-test.md       ← Automotive testing
    automotive-adas-scenario.md ← ADAS scenario testing
    automotive-can-bus-test.md ← CAN bus testing
    automotive-hil-loop-test.md ← HIL loop testing
    automotive-ota-update-test.md ← OTA update testing
    ├── darwin-skill/        ← Meta-skill: self-evolution engine
    ├── karpathy-guidelines/ ← Meta-skill: coding discipline
    └── nuwa-skill/          ← Meta-skill: persona distillation

## Rules

### What goes here
- Agent role prompt files (.md with YAML frontmatter)
- Skill workflow documents (.md with step-by-step instructions)
- Meta-skill packages (self-contained directories)

### What does NOT go here
- Python code (.py) — goes in `runtime/` or `utils/`
- Config files (.json, .yaml) — goes in `deploy/`
- Test data or output — goes in `workspace/`
- Build artifacts

### Convention
- Agent files: numbered `01-` to `16-`, Chinese names
- Skill files: lowercase-hyphenated English names
- Each .md has YAML frontmatter: `id`, `category`, `agent_count`
- Meta-skills are self-contained in their own subdirectory
