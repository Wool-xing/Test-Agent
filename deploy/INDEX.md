# Deploy — Deployment Materials

## Purpose
All files that `install.py` copies to the user's project directory at install time.
These are **templates** and **static assets**, not source code.
They get deployed to user projects — paths inside these files use **deploy-time paths** (e.g., `agents/` not `ai/agents/`).

## Structure
```
deploy/
├── config/                  ← Config templates (copied to user project root)
│   .env.example             ← Environment template
│   conftest.py              ← pytest global fixtures
│   pytest.ini               ← pytest configuration
│   quality_gates.yaml       ← Quality gate thresholds
│   check_version.py         ← Version check script
│   requirements.txt         ← Core pip dependencies
│   .mcp.json                ← MCP server configuration
│   settings.json            ← Claude Code project settings
│   llm-providers.md         ← LLM provider configuration guide
│   mcp-server-impl.md       ← MCP server implementation guide
│   └── templates/           ← Project templates (rendered by init)
│       STARTUP.md.tpl       ← Quick-start guide template
│       base.env.tpl         ← Base environment template
│       base.tagent.yml.tpl  ← Base project config template
│       matrix.yaml          ← Platform × preset compatibility matrix
│
├── marketplace/             ← Skill marketplace
│   INDEX.md                 ← Marketplace overview
│   registry.json            ← Skill registry
│   _safety_policy.yaml      ← Safety policy for marketplace
│
└── profiles/                ← Compliance profiles
    gdpr.yaml                ← GDPR compliance
    hipaa.yaml               ← HIPAA compliance
    soc2.yaml                ← SOC 2 compliance
    pci-dss.yaml             ← PCI DSS compliance
    ccpa.yaml                ← CCPA compliance
    pipl.yaml                ← PIPL (China) compliance
    iso-26262.yaml           ← ISO 26262 (automotive)
    iec-62304.yaml           ← IEC 62304 (medical)
    iec-61508.yaml           ← IEC 61508 (industrial)
    do-178c.yaml             ← DO-178C (aviation)
    INDEX.md                 ← Profiles overview
```

## Rules

### What goes here
- Config file templates (copied by install.py)
- Marketplace registry and policies
- Compliance profile definitions (.yaml)

### What does NOT go here
- Business logic or executable code — goes in `runtime/` or `utils/`
- AI agent/skill definitions — goes in `ai/`
- Application source code — goes in `apps/`
- Documentation — goes in `docs/`

### Path convention
- Files here use **deploy-time paths**: `agents/`, `skills/`, `workspace/`
- install.py copies them to the user's project root
- The user's deployed project has a flat structure (no `ai/`, `apps/`, `deploy/` directories)

### Adding a new config template
1. Add file to `deploy/config/`
2. Update `install.py` copy_config() if needed
3. Document in `deploy/config/` README
