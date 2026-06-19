# Getting Started

Test-Agent V2 is an AI-native testing framework that combines 16 specialized AI agents with 32 testing skills to automate the full testing lifecycle. Version 2.0.0 ships 38 completed feature phases across 8 tracks.

## Prerequisites

- **Python** 3.10 or later
- **Git** 2.30 or later
- **pip** 23.0 or later
- An LLM API key (Claude, OpenAI, Gemini, DeepSeek, Qwen, or Ollama)

## Quick Install

```bash
# Clone and bootstrap in one step
git clone https://github.com/test-agent/test-agent.git
cd test-agent
python install.py

# One-command bootstrap (Phase 6, #24)
tagent bootstrap
```

The `tagent bootstrap` command checks your Python/Git/pip versions, generates a `.env` template, and validates your LLM key — collapsing what was a 15-step process into 3.

## Verify Installation

```bash
# Health check
tagent doctor

# List available experts and skills
tagent catalog

# Run a self-test
tagent selftest
```

## Your First Test

```bash
# Run the built-in demo workflow
tagent demo

# Plan a test from a PRD
tagent plan "path/to/prd.md"

# Execute the full pipeline
tagent run "path/to/prd.md"
```

## What's New in V2

| Feature | Description |
|---------|-------------|
| AI Router (Phase 2, #8) | NL query to expert+skill mapping with stub mode |
| Self-Healing Engine (Phase 3, #9) | Exponential backoff retry, element locator fallback chains |
| Release Readiness (Phase 4, #15) | Weighted scoring with GREEN/YELLOW/RED gating |
| Flaky Detection (Phase 4, #16) | Pattern-based detection, auto-quarantine, pytest markers |
| RBAC (Phase 5, #19) | 4 roles (admin/lead/tester/viewer) with token-based auth |
| Audit Trail (Phase 5, #20) | JSONL audit log with query-by-action/resource/actor |
| Bootstrap (Phase 6, #24) | One-command setup from clone to ready |
| Plugins (Phase 8, #34) | Entry-point based discovery for community extensions |

## Desktop App

A Tauri 2 desktop shell is available in `apps/desktop-v2/`. It provides:

- Sidebar navigation (Dashboard, Tests, Agents, Marketplace, Settings)
- Engine status indicator with version display
- API proxy to the local backend on port 8000

```bash
cd apps/desktop-v2
npm install
npm run tauri:dev
```

## Next Steps

- Read the [Architecture](/guide/architecture) guide
- Browse the [API Reference](/api/overview)
- Explore the [Plugin System](/plugins/overview)
