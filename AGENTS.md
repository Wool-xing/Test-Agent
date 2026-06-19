# AGENTS.md

## AI AGENT — STOP. READ THIS FIRST.

**This is a Test-Agent project. It has a defined execution framework. You MUST follow it.**

- Do NOT call or spawn sub-agents without reading the relevant Skill doc first.
- Do NOT skip the Skill workflow layer.
- Do NOT execute test workflows directly — read the Skill doc and follow its agent call sequence.

**Correct flow:**
1. Read `ai/skills/<task>.md` to understand the workflow
2. Follow the Skill doc's step-by-step agent call sequence
3. Use Agent tools ONLY when and how the Skill doc says

**If no Skill doc matches the task:** fall back to `ai/skills/test-coordinator.md`.

---

## Two Ways to Use Test-Agent

### Way 1: Standalone CLI (no AI required)

```bash
cd project-dir
# install.py 已自动安装 tagent CLI 到 venv
tagent.bat                        # Windows
./tagent                          # macOS / Linux
tagent run "path/to/prd.md"      # router + orchestrator end-to-end
tagent catalog                   # list 16 experts + 32 skills
tagent doctor                    # health check
```

### Way 2: AI Agent Collaboration

```bash
cd project-dir
# 任选其一: claude | cursor | GitHub Copilot | Windsurf | CodeBuddy 等
# 配置 LLM Provider: 编辑 .env → TAGENT_LLM_PROVIDER + API key
# 内置: claude | openai | gemini | deepseek | qwen | ollama
# OpenAI 兼容: 智谱/豆包/Kimi/百川/讯飞 (设 TAGENT_LLM_API_BASE)
```

**Agent 工作流:**
1. Read `ai/skills/<task>.md` first
2. Follow Skill doc sequence (requirements-analyst → testcase-designer → ...)
3. Outputs in workspace/

---

## Architecture

```
Standalone CLI (tagent)              AI Agent Mode
        │                                      │
        ▼                                      ▼
   runtime/router                    Skill docs (ai/skills/*.md)
        │                                      │
        ▼                                      ▼
   runtime/orchestrator              Agent defs (ai/agents/*.md)
        │                                      │
        ▼                                      ▼
   utils/*.py (79 modules)           utils/*.py (79 modules)
```

Both paths converge at the utils execution layer.

## Directory Map

| What | Where |
| ------ | ------- |
| Agent definitions | `ai/agents/` (16 agents) |
| Skill workflow docs | `ai/skills/` (32 skills + 3 meta-skill packages) |
| Python utils | `utils/` (79 modules) |
| Runtime (CLI + orchestrator + MCP) | `runtime/` |
| Deploy templates | `deploy/config/` (incl. `.env.example`) |
| Distributable apps | `apps/` (desktop, mobile) |
| Test outputs | `workspace/` |
| CI pipelines | `ci/` |
| Docs | `docs/` |

## Design Notes

- Slash commands like `/smoke-test` are Skill workflow documents, not registered commands.
- Agent definitions contain Python import hints as prompts for AI agents — not actual executable code.
- Pentest workflows require `tagent.yml` with `pentest.authorized: true`.
- MCP server (`python -m runtime.mcp.test_orchestrator.server`) provides catalog/plan/run/status/report tools.
