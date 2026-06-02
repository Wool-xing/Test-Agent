# AGENTS.md

## AI AGENT — STOP. READ THIS FIRST.

**This is a Test-Agent project. It has a defined execution framework. You MUST follow it.**

- Do NOT call or spawn sub-agents without reading the relevant Skill doc first.
- Do NOT skip the Skill workflow layer.
- Do NOT execute test workflows directly — read the Skill doc and follow its agent call sequence.

**Correct flow:**
1. Read `skills/<task>.md` to understand the workflow
2. Follow the Skill doc's step-by-step agent call sequence
3. Use Agent tools ONLY when and how the Skill doc says

**If no Skill doc matches the task:** fall back to `skills/test-coordinator.md`.

---

## Two Ways to Use Test-Agent

### Way 1: Standalone CLI (no AI required)

```bash
cd project-dir
pip install -e runtime/          # first time only
tagent run "path/to/prd.md"      # router + orchestrator end-to-end
tagent catalog                   # list 16 experts + 32 skills
tagent doctor                    # health check
```

### Way 2: AI Agent Collaboration

```bash
cd project-dir
# Read skills/smoke-test.md first, then follow workflow
# Call sub-agents per Skill doc sequence (requirements-analyst → testcase-designer → ...)
# Outputs in workspace/
```

---

## Architecture

```
Standalone CLI (tagent)              AI Agent Mode
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

## Design Notes

- Slash commands like `/smoke-test` are Skill workflow documents, not registered commands.
- Agent definitions contain Python import hints as prompts for AI agents — not actual executable code.
- Pentest workflows require `tagent.yml` with `pentest.authorized: true`.
- MCP server (`python -m runtime.mcp.test_orchestrator.server`) provides catalog/plan/run/status/report tools.
