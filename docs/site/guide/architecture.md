# Architecture

Test-Agent V2 follows a dual-mode architecture with two independent execution paths converging at a shared utility layer.

## High-Level Structure

```
ai/                         AI Mode (read-only agent definitions)
  agents/                   16 agent prompt definitions (.md)
  skills/                   32 skill workflow definitions (.md)
  INDEX.md                  Agent index and constraints

runtime/                    CLI Engine
  cli/                      Typer CLI with 9 subcommands
  router/                   V2 AI router + prompt construction
  orchestrator/             Prefect-based execution engine
  api/                      FastAPI server with auth/RBAC
  observability/            Dashboard, audit, logging, APM export
  intelligence/             Impact analysis, risk matrix, journey mapper
  self_healing/             Retry policies and locator chains

utils/                      Shared Tools (79 modules, 12 subdirectories)
  testing/                  BDD, state machines, classification trees
  security/                 API security scanner, fuzzer
  performance/              Chaos helper, load profiles
  data_synthesizer.py       PII masking, test data generation
  traceability_matrix.py    Requirements-to-tests bidirectional trace
  flaky_detector.py         Pattern detection and quarantine generation

apps/                       Distributable Apps
  desktop/                  Electron v1 (deprecated by desktop-v2)
  desktop-v2/               Tauri 2 desktop shell

deploy/                     Install Materials
  config/                   .env templates, pytest.ini
  marketplace/              Entry-point plugin registry
  profiles/                 GDPR, HIPAA, SOC2 compliance templates
```

## Execution Flow

```
User Input (NL / PRD / CLI)
       |
       v
   AI Router (v2_router.py)
   Maps query to expert + skill
       |
       v
   Orchestrator (direct.py / flows.py)
   DAG execution with self-healing
       |
       v
   Backend (local / SSH / Docker / Modal)
       |
       v
   Report Generator + Dashboard
```

## Key Modules

### AI Router (Phase 2, #8)

The V2 router (`runtime/router/v2_router.py`) accepts natural language and maps it to the appropriate expert agent and skill workflow. It supports:

- **Stub mode**: Offline matching without LLM calls (set `TAGENT_LLM_PROVIDER=stub`)
- **Dispatch table**: 8-entry lookup replacing a 77-line if/elif chain
- **Prompt construction**: `v2_prompt.py` builds context-aware prompts from skill docs

### Self-Healing Engine (Phase 3, #9-#13)

- **Retry**: Exponential backoff (2^n seconds, 3 attempts) via `with_retry()`
- **Locator**: Multi-attribute element location with fallback chains
- **Circuit Breaker**: `MAX_FAILURES=3` halts execution to prevent cascading failures
- **Progress Tracking**: DAG node-level progress with skipped/failed independent tracking

### Release Readiness (Phase 4, #15)

```
Score = smoke(0.4) + regression(0.3) + perf(0.2) + security(0.1)

GREEN  >= 0.85  Ship it
YELLOW >= 0.60  Review required
RED    <  0.60  Blocked
```

### Enterprise Features (Phase 5, #19-#23)

- **RBAC**: 4 roles (admin/lead/tester/viewer) with `require_role()` decorator
- **Audit**: JSONL append-only audit log with query interface
- **Multi-tenancy**: Context-var based tenant propagation
- **Hooks**: Before/after/on_error lifecycle hooks that don't interrupt execution

### Plugin System (Phase 8, #34)

Third-party packages register via `importlib.metadata` entry points under the `tagent` group:

```python
# In a plugin's pyproject.toml
[project.entry-points.tagent]
agents = "my_plugin.agents"
skills = "my_plugin.skills"
```
