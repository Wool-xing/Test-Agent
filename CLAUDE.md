# CLAUDE.md — Test-Agent Project Entry Point

> **AI 编程助理必须先读 [`ai/CLAUDE.md`](ai/CLAUDE.md)** — 包含强制开发约束（禁止硬编码、文件放置规则、防污染机制等）。

## ⚠️ READ THIS FIRST

This project has a **dual-mode architecture**. Two independent paths converge at `utils/`.

### 🔵 AI Mode — `ai/`
AI agents read skill docs and agent definitions to orchestrate testing.

- `ai/agents/` — 16 agent prompt definitions (.md)
- `ai/skills/` — 32 skill workflow definitions (.md)
- These are READ-ONLY for AI agents. Do NOT modify unless explicitly asked.

**Correct flow:**
1. Read `ai/skills/<task>.md` to understand the workflow
2. Follow the Skill doc's step-by-step agent call sequence
3. Call `Agent(subagent_type="xxx")` ONLY when and how the Skill doc says

**If no Skill doc matches the task:** fall back to `ai/skills/test-coordinator.md`.

### 🟢 CLI Mode — `runtime/` + `utils/`
Standalone CLI that works without AI.

```bash
tagent run "path/to/prd.md"      # router + orchestrator end-to-end
tagent plan "path/to/prd.md"     # plan only (no execution)
tagent catalog                   # list 16 experts + 32 skills
tagent doctor                    # health check
```

### 🟡 Deployment — `deploy/`
Files copied by `install.py` to user projects. Do NOT put source code here.

---

## Architecture

```
┌─────────────────────────────────────────┐
│  ai/          AI Mode Interface          │
│  agents/ + skills/   .md only           │
│              ↓                           │
├─────────────────────────────────────────┤
│  runtime/     CLI Engine                 │
│  utils/       Shared Tools               │
│              ↑                           │
├─────────────────────────────────────────┤
│  apps/        Distributable Apps         │
│  desktop/ + mobile/                      │
├─────────────────────────────────────────┤
│  deploy/      Install Materials          │
│  config/ + marketplace/ + profiles/      │
└─────────────────────────────────────────┘

Both paths converge at utils/ execution layer.
```

## Directory Map

| What | Where |
|------|-------|
| Agent definitions | `ai/agents/` (16 agents) |
| Skill workflow docs | `ai/skills/` (32 skills + 3 meta-skill packages) |
| Python runtime engine | `runtime/` (CLI + orchestrator + MCP + API) |
| Python utilities | `utils/` (79 modules, 12 subdirectories) |
| Distributable apps | `apps/` (desktop, mobile) |
| Deploy templates | `deploy/config/` (.env.example, pytest.ini, ...) |
| Deploy marketplace | `deploy/marketplace/` |
| Deploy profiles | `deploy/profiles/` (gdpr, hipaa, soc2, ...) |
| Test outputs | `workspace/` (gitignored) |
| CI pipelines | `ci/` |
| Documentation | `docs/` |
| Dev scripts | `scripts/` |

---

## Development Rules (MUST FOLLOW)

1. **No new files in root.** Root has only entry points + project metadata.
2. **New agent?** → `ai/agents/NN-name.md`
3. **New skill?** → `ai/skills/name.md` (+ optional `runtime/orchestrator/skills/name.py`)
4. **New CLI command?** → `runtime/cli/commands/name.py` + register in `main.py`
5. **New utility?** → appropriate subdirectory under `utils/`
6. **New app?** → `apps/name/` (self-contained)
7. **New deploy template?** → `deploy/config/` or `deploy/profiles/`
8. **Never commit:** build artifacts, caches, logs, node_modules, .coverage, workspace data
9. **Read `ai/INDEX.md`** before touching ai/ files
10. **Read `deploy/INDEX.md`** before touching deploy/ files

## Quick Reference

| Task | Where |
|------|-------|
| Add test capability | `ai/skills/` + `utils/<domain>/` |
| Add agent role | `ai/agents/` |
| Fix CLI bug | `runtime/` |
| Add deployment config | `deploy/config/` |
| Add compliance profile | `deploy/profiles/` |
| Build desktop app | `apps/desktop/` |
| Write docs | `docs/` |
| Run tests | `pytest runtime/tests/` |

## Design Notes

- Slash commands like `/smoke-test` are Skill workflow documents, not registered commands.
- Agent definitions contain Python import hints as prompts — not executable code.
- `test-lead` cannot recursively spawn sub-agents (Claude Code limitation). Main thread orchestrates.
- Pentest workflows require `tagent.yml` with `pentest.authorized: true` — see `tagent.yml.example`.
- MCP server: `python -m runtime.mcp.test_orchestrator.server` (catalog/plan/run/status/report).
- LLM providers: edit `.env` → `TAGENT_LLM_PROVIDER`. Built-in: claude/openai/gemini/deepseek/qwen/ollama.
- See `deploy/config/llm-providers.md` for OpenAI-compatible endpoints.
