"""Real LLM-driven skill runners.

18 production runners across 4 domains:
- General: mobile-test, visual-test, system-test, eval-harness
- Pentest: pentest-coordinator, pentest-recon, pentest-vuln, pentest-exploit, pentest-api, pentest-web, pentest-report
- Automotive: automotive-test, automotive-can-bus-test, automotive-adas-scenario, automotive-ota-update-test, automotive-hil-loop-test
- Meta: agent-introspection-debugging, build-your-own-x-explorer
"""

from runtime.orchestrator.agents.base import (  # noqa: F401
    SKILL_RUNNERS,
    AgentRunner,
    RunnerContext,
    RunnerResult,
    get_skill_runner,
    register_skill,
)

# Alias for external consumers that expect 'registry'
registry = SKILL_RUNNERS

# Trigger registration (each module registered via @register_skill on import)
from runtime.orchestrator.skills import (  # noqa: F401,E402
    agent_introspection_debugging,
    automotive_adas_scenario,
    automotive_can_bus_test,
    automotive_hil_loop_test,
    automotive_ota_update_test,
    automotive_test,
    build_your_own_x_explorer,
    eval_harness,
    mobile_test,
    pentest_api,
    pentest_coordinator,
    pentest_exploit,
    pentest_recon,
    pentest_report,
    pentest_vuln,
    pentest_web,
    system_test,
    visual_test,
)
