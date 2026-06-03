# CLAUDE.md

## AI AGENT — STOP. READ THIS FIRST.

**This is a Test-Agent project. It has a defined execution framework. You MUST follow it.**

- Do NOT call `Agent()` directly.
- Do NOT spawn sub-agents without reading the relevant Skill doc first.
- Do NOT skip the Skill workflow layer.

**Correct flow:**
1. Read `skills/<task>.md` to understand the workflow
2. Follow the Skill doc's step-by-step agent call sequence
3. Call `Agent(subagent_type="xxx")` ONLY when and how the Skill doc says

**If no Skill doc matches the task:** fall back to `skills/test-coordinator.md` (通用编排).

---

## Two Ways to Use Test-Agent

### Way 1: Standalone CLI (no AI required)

```bash
cd project-dir
pip install -e runtime/          # first time only
tagent run "path/to/prd.md"      # router + orchestrator end-to-end
tagent catalog                   # list 16 experts + 32 skills
tagent status <run_id>           # check run status
tagent report <run_id>           # full execution report
tagent doctor                    # health check
```

The CLI uses the same runtime (router + orchestrator + utils) without needing Claude Code.

### Way 2: Claude Code Agent Collaboration (AI-assisted)

```bash
cd project-dir && claude
# Inside Claude Code:
# 1. Read skills/smoke-test.md
# 2. Follow the workflow: call Agent(subagent_type="requirements-analyst"), then test-lead, etc.
# 3. Outputs in workspace/
```

**⚠️ Critical:** Claude Code agents WILL try to bypass the Skill layer and call Agent() directly. The main thread MUST enforce reading Skill docs first.

---

## Architecture

```
Standalone CLI (tagent)              AI Agent Mode (Claude Code)
        │                                      │
        ▼                                      ▼
   runtime/router                    Skill docs (skills/*.md)
        │                                      │
        ▼                                      ▼
   runtime/orchestrator              Agent defs (agents/*.md)
        │                                      │
        ▼                                      ▼
   utils/*.py (79 modules)           utils/*.py (79 modules)
```

Both paths converge at the utils execution layer.

## Directory Map

| What | Where |
|------|-------|
| Agent definitions | `agents/` (16 agents) |
| Skill workflow docs | `skills/` (35 skills) |
| Python utils | `utils/` (79 modules) |
| Runtime (CLI + orchestrator + MCP) | `runtime/` |
| Config templates | `config/` (incl. `.env.example`) |
| Test outputs | `workspace/` |
| CI pipelines | `ci/` |
| Docs | `docs/` |
| Marketplace | `marketplace/` |

## Design Notes

- Slash commands like `/smoke-test` are **not** registered. They are Skill workflow documents.
- Agent definitions contain Python import hints as prompts for AI agents — not actual executable code.
- `test-lead` cannot recursively spawn sub-agents (Claude Code limitation). Main thread orchestrates.
- Pentest workflows require `tagent.yml` with `pentest.authorized: true` — see `tagent.yml.example`.
- MCP server (`python -m runtime.mcp.test_orchestrator.server`) provides catalog/plan/run/status/report tools.
