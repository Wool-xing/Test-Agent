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
# install.py 已自动安装 tagent CLI 到 venv
tagent.bat                        # Windows
./tagent                          # macOS / Linux
tagent run "path/to/prd.md"      # router + orchestrator end-to-end
tagent plan "path/to/prd.md"     # plan only (no execution)
tagent catalog                   # list 16 experts + 32 skills
tagent doctor                    # health check
```

The CLI uses the same runtime (router + orchestrator + utils) without needing an AI agent.

### Way 2: AI Agent Collaboration

```bash
cd project-dir
# 任选其一:
claude                   # Claude Code (Anthropic)
cursor                   # Cursor (OpenAI / Claude / Gemini …)
# GitHub Copilot / Windsurf / CodeBuddy 等均可
```

**LLM Provider 配置:** 编辑 `.env` → 设 `TAGENT_LLM_PROVIDER` + 对应 API key.
内置 6 家: `claude` | `openai` | `gemini` | `deepseek` | `qwen` | `ollama`.
OpenAI 兼容端点 (智谱/豆包/Kimi/百川/讯飞): 设 `TAGENT_LLM_API_BASE` + `TAGENT_LLM_API_KEY`.
详见 `config/llm-providers.md`.

**Agent 工作流:**
1. Read `skills/<task>.md` to understand the workflow
2. Follow the Skill doc's step-by-step agent call sequence
3. Call `Agent(subagent_type="xxx")` ONLY when and how the Skill doc says

**⚠️ Critical:** AI agents WILL try to bypass the Skill layer and call Agent() directly. The main thread MUST enforce reading Skill docs first.

---

## Architecture

```
Standalone CLI (tagent)              AI Agent Mode (Claude / Cursor / Copilot ...)
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
| Skill workflow docs | `skills/` (32 skills + 3 meta-skill packages) |
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
