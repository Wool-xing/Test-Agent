# CLAUDE.md

## Entry Point

This project uses **Skill workflow documents → manual Agent calls** pattern. Slash commands like `/smoke-test` are **not registered** as Claude Code commands — they are workflow documents in `skills/` that describe step-by-step processes. The main thread reads the Skill doc, then calls `Agent(subagent_type="xxx")` sequentially.

There is **no auto-orchestration engine**. The main thread reads Skill docs and calls Agents sequentially. Agents may invoke utils but often implement equivalent logic themselves.

## Directory Map

| What | Where |
|------|-------|
| Agent definitions | `agents/` (16 agents) |
| Skill workflow docs | `skills/` (35 skills) |
| Python utils | `utils/` (78 modules) |
| Config templates | `config/` (incl. `.env.example`) |
| Test outputs | `workspace/` |
| Runtime / MCP | `runtime/` |
| CI pipelines | `ci/` |
| Docs | `docs/` |
| Marketplace | `marketplace/` |

## How to Run

1. Copy `config/.env.example` to `.env` and fill in required values
2. Read the relevant Skill doc in `skills/` to understand the workflow
3. Call agents manually via `Agent(subagent_type="xxx")` following the Skill flow
4. Outputs land in `workspace/`

## Architecture

```
Skill docs (skills/*.md)  →  define workflows
Agent defs (agents/*.md)  →  define roles + tool access
Utils (utils/*.py)        →  executable implementations
```

## Design Limitations

- `/smoke-test` etc. are **not** registered slash commands. They are workflow documents.
- Agent definitions contain Python import hints (e.g. `from utils.prd_loader import load_prd`) as prompts for AI agents, not actual executable code.
- `test-lead` cannot recursively spawn sub-agents (Claude Code architecture limitation).
- Pentest workflows require `tagent.yml` with `pentest.authorized: true` — see `tagent.yml.example`.
