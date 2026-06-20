"""Slash command handlers — facade re-exporting from sub-modules.

Sub-modules (each ≤800 lines):
- slash_handlers_core.py:   utilities + session/state + fix/ready/update
- slash_handlers_config.py: hook/skin/lang + tools/context + cost/sessions + memory
- slash_handlers_ops.py:    MCP + cron/task/model/search + API/plugins/alias/ws/gateway
- slash_handlers_data.py:   data/prioritize/progress/flaky/regression/insights + doctor/nudge
"""

from runtime.cli.commands.slash_handlers_core import (  # noqa: F401
    _apply_fc_rules,
    _closest_command,
    _cmd_cache,
    _cmd_fc,
    _cmd_history,
    _cmd_model,
    _cmd_ready,
    _cmd_status,
    _cmd_update,
    _current_model,
    _current_provider,
    _do_quit,
    _edit_distance,
    _get_memory,
    _rerun_history,
)

from runtime.cli.commands.slash_handlers_config import (  # noqa: F401
    _cmd_clear,
    _cmd_compact,
    _cmd_context,
    _cmd_cost,
    _cmd_export,
    _cmd_forget,
    _cmd_hook,
    _cmd_lang,
    _cmd_memory,
    _cmd_personality,
    _cmd_remember,
    _cmd_resume,
    _cmd_sessions,
    _cmd_skin,
    _cmd_tools,
    _cmd_undo,
    _cmd_retry,
    _estimate_cost,
    _PRICE_PER_1K,
)

from runtime.cli.commands.slash_handlers_ops import (  # noqa: F401
    _cmd_alias,
    _cmd_api,
    _cmd_cron,
    _cmd_cron_health,
    _cmd_cross,
    _cmd_distill,
    _cmd_gateway,
    _cmd_mcp_call,
    _cmd_mcp_tools,
    _cmd_model_router,
    _cmd_plugins_list,
    _cmd_search,
    _cmd_skill_score,
    _cmd_speak,
    _cmd_task,
    _cmd_ws,
)

from runtime.cli.commands.slash_handlers_data import (  # noqa: F401
    _cmd_clean,
    _cmd_data,
    _cmd_doctor,
    _cmd_flaky,
    _cmd_insights,
    _cmd_nudge,
    _cmd_prioritize,
    _cmd_progress,
    _cmd_regression,
)
