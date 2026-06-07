# Workspace — Runtime Output

## Purpose
ALL runtime-generated data lives here. This directory is **completely gitignored**.
The only exception is `_demo/` — a reference demo project used by `runtime/` for demos and smoke tests.

## Structure
```
workspace/
├── _demo/                   ← Demo project fixture (referenced by runtime)
│   .env                     ← Demo environment config
│   STARTUP.md               ← Demo quick-start
│   tagent.yml               ← Demo project config
│
├── 测试报告/                ← Test reports (gitignored)
├── 测试用例/                ← Test cases (gitignored)
├── 测试数据/                ← Test data (gitignored)
├── 测试计划/                ← Test plans (gitignored)
├── 需求分析/                ← Requirements analysis (gitignored)
├── 自动化脚本/              ← Generated automation scripts (gitignored)
└── gateway/                 ← Export history + runtime state (gitignored)
```

## Rules

### What goes here
- Test execution output (reports, logs, screenshots)
- Generated test data and automation scripts
- Runtime state (cron jobs, feedback, export history)
- Demo project fixtures (`_demo/`)

### What does NOT go here
- Source code — goes in `runtime/`, `utils/`, `ai/`, `apps/`
- Configuration — goes in `deploy/`
- Documentation — goes in `docs/`

### Cleanup
- Use `tagent clean` or `python -m runtime.cli.data_cleaner` to purge runtime output
- Everything except `_demo/` can be safely deleted
- This directory is created by `install.py` during deployment
