"""Real LLM-driven skill runners (V1.36.0 · ALL 14/14 rollout complete).

16 production runners across 3 domains:
- General: mobile-test, visual-test, system-test, eval-harness
- Pentest: pentest-coordinator, pentest-recon, pentest-vuln, pentest-exploit, pentest-api, pentest-web, pentest-report
- Automotive: automotive-test, automotive-can-bus-test, automotive-adas-scenario, automotive-ota-update-test, automotive-hil-loop-test
"""

from runtime.orchestrator.agents.base import (  # noqa: F401
    AgentRunner,
    RunnerContext,
    RunnerResult,
    SKILL_RUNNERS,
    get_skill_runner,
    register_skill,
)

# Trigger registration (each module registered via @register_skill on import)
from runtime.orchestrator.skills import (  # noqa: F401,E402
    automotive_adas_scenario,
    automotive_can_bus_test,
    automotive_hil_loop_test,
    automotive_ota_update_test,
    automotive_test,
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
