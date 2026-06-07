# Copilot Instructions

This is a Test-Agent project with a defined Skill → Agent → Utils execution framework.

## When generating code or answering questions:

1. **Read Skill docs first** — Check `skills/<task>.md` to understand the workflow before generating any test code or calling agents.
2. **Follow the framework** — Do not skip the Skill workflow layer. Agent definitions are in `ai/agents/`, utils in `utils/`.
3. **Use existing utils** — The project has 79 utility modules in `utils/`. Prefer using them over generating new code.
4. **Match the project structure** — Test outputs go to `workspace/`, config in `deploy/config/`, apps in `apps/`.
5. **Config first** — Check `deploy/config/.env.example` for required environment variables before generating code that depends on them.

## Standalone CLI

The project has a CLI at `runtime/cli/main.py` (entry point: `tagent`):
```bash
tagent run "path/to/prd.md"
tagent catalog
tagent doctor
```

## Key directories

| What | Where |
|------|-------|
| Agent definitions | `agents/` |
| Skill workflow docs | `skills/` |
| Python utils | `utils/` |
| Runtime (CLI + MCP) | `runtime/` |
| Config templates | `config/` |
| Test outputs | `workspace/` |
