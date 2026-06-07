"""Slash command registry — single source of truth.

Single registry drives CLI + REPL autocomplete, help output, command dispatch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class CommandDef:
    name: str
    description: str              # English description
    description_zh: str = ""      # Chinese description
    aliases: list[str] = field(default_factory=list)
    args_hint: str = ""
    handler: Callable | None = None
    nl_triggers: list[str] = field(default_factory=list)  # 自然语言触发词


COMMAND_REGISTRY: list[CommandDef] = []


def register(name: str, description: str, *,
             description_zh: str = "",
             aliases: list[str] | None = None,
             args_hint: str = "",
             nl_triggers: list[str] | None = None):
    """Decorator: register a slash command handler with bilingual metadata."""

    def decorator(fn):
        COMMAND_REGISTRY.append(
            CommandDef(
                name=name,
                description=description,
                description_zh=description_zh or description,
                aliases=aliases or [],
                args_hint=args_hint,
                handler=fn,
                nl_triggers=nl_triggers or [],
            )
        )
        return fn

    return decorator


# ── Lookup ──────────────────────────────────────────────────────────


def resolve(name: str) -> CommandDef | None:
    """Look up command by name or alias."""
    name = name.lstrip("/").strip().lower()
    for cmd in COMMAND_REGISTRY:
        if cmd.name == name or name in cmd.aliases:
            return cmd
    return None


def resolve_nl(text: str) -> CommandDef | None:
    """Match natural language text to a command via trigger phrases."""
    text = text.strip().lower()
    for cmd in COMMAND_REGISTRY:
        for trigger in cmd.nl_triggers:
            if trigger in text:
                return cmd
    return None


def closest(name: str) -> str | None:
    """Find closest matching command via edit distance (thefuck pattern)."""
    name = name.lstrip("/").strip().lower()
    if not name:
        return None
    best, best_dist = None, 999
    for cmd in COMMAND_REGISTRY:
        d = _edit_distance(name, cmd.name)
        if d < best_dist:
            best, best_dist = cmd.name, d
        for alias in cmd.aliases:
            d = _edit_distance(name, alias)
            if d < best_dist:
                best, best_dist = alias, d
    return best if best_dist <= 3 else None


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein distance."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(
                prev[j] + 1,
                curr[-1] + 1,
                prev[j - 1] + (ca != cb),
            ))
        prev = curr
    return prev[-1]


def all_commands() -> list[CommandDef]:
    return list(COMMAND_REGISTRY)


def _run_with_argv(cmd: list[str], fn) -> None:
    """Execute fn with temporary sys.argv, restoring afterward."""
    import sys
    old = sys.argv[:]
    try:
        sys.argv = cmd
        fn()
    finally:
        sys.argv = old


# ═══════════════════════════════════════════════════════════════════
# Command handlers
# ═══════════════════════════════════════════════════════════════════


@register("help", "Show help",
          description_zh="显示帮助，列出所有命令",
          aliases=["h", "?"], nl_triggers=["帮助", "怎么用", "命令列表", "有啥命令", "help"])
def _cmd_help(args: str) -> None:
    from runtime.cli._shared import console
    from rich.table import Table
    from rich.text import Text

    table = Table(title="Commands", show_header=True)
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Args", style="dim")
    table.add_column("EN", style="green")
    table.add_column("中文", style="yellow")

    for cmd in sorted(COMMAND_REGISTRY, key=lambda c: c.name):
        aliases_str = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
        table.add_row(
            f"/{cmd.name}{aliases_str}",
            cmd.args_hint,
            cmd.description,
            cmd.description_zh,
        )

    console.print(table)
    console.print("[dim]Bare text (no /) → LLM routing → agent execution[/]")
    console.print("[dim]直接输入文字（无 /）→ LLM 路由 → 智能体执行[/]")


@register("quit", "Exit", description_zh="退出", aliases=["q", "exit"], nl_triggers=["退出", "再见", "拜拜", "走了", "关闭"])
def _cmd_quit(args: str) -> None:
    from runtime.cli._shared import console
    console.print("[dim]Goodbye.[/]")
    raise SystemExit(0)


@register("test", "Full test pipeline (11-step)",
          description_zh="完整测试流程（11步）",
          aliases=["tc"], args_hint="<target>", nl_triggers=["测试", "跑测试", "完整测试", "test"])
def _cmd_test(args: str) -> None:
    if not args.strip():
        from runtime.cli._shared import console
        console.print("[red]Usage: /test <path|URL|text>[/]")
        return
    from runtime.orchestrator.workflows.test_coordinator import TestCoordinatorPipeline
    TestCoordinatorPipeline().run(args.strip())


@register("run", "Plan + execute (quick)",
          description_zh="快速规划执行",
          aliases=["r"], args_hint="<target>", nl_triggers=["运行", "执行", "快速测试", "跑一下"])
def _cmd_run(args: str) -> None:
    if not args.strip():
        from runtime.cli._shared import console
        console.print("[red]Usage: /run <path|URL|text>[/]")
        return
    from runtime.cli.commands.run import run
    _run_with_argv(["tagent", "run"] + args.split(), run)


@register("plan", "Plan only",
          description_zh="仅规划不执行",
          aliases=["p"], args_hint="<target>", nl_triggers=["计划", "规划", "只规划", "不执行", "出计划"])
def _cmd_plan(args: str) -> None:
    if not args.strip():
        from runtime.cli._shared import console
        console.print("[red]Usage: /plan <path|URL|text>[/]")
        return
    from runtime.cli.commands.run import plan
    _run_with_argv(["tagent", "plan"] + args.split(), plan)


@register("doctor", "Health check",
          description_zh="健康检查",
          aliases=["health"], args_hint="[--agents] [--probe]", nl_triggers=["健康检查", "检查一下", "诊断", "体检", "环境检查"])
def _cmd_doctor(args: str) -> None:
    from runtime.cli.commands.doctor import doctor
    _run_with_argv(["tagent", "doctor"] + (args.split() if args.strip() else []), doctor)


@register("ls", "List experts + skills",
          description_zh="列出专家和技能",
          aliases=["list", "catalog"], nl_triggers=["列出", "列表", "目录", "有哪些", "显示所有"])
def _cmd_ls(args: str) -> None:
    from runtime.cli.commands.catalog import catalog
    _run_with_argv(["tagent", "catalog"], catalog)


@register("setup", "Generate config",
          description_zh="生成配置文件",
          aliases=["init"], args_hint="[--preset ...]", nl_triggers=["设置", "配置", "初始化", "生成配置"])
def _cmd_setup(args: str) -> None:
    from runtime.cli.commands.init import init_project
    _run_with_argv(["tagent", "init"] + (args.split() if args.strip() else []), init_project)


@register("ready", "Release readiness",
          description_zh="发布就绪检查",
          aliases=["readiness"], nl_triggers=["就绪", "发布检查", "准备好了吗", "上线检查"])
def _cmd_ready(args: str) -> None:
    from runtime.cli.commands.readiness import readiness
    _run_with_argv(["tagent", "readiness"] + (args.split() if args.strip() else []), readiness)


@register("check", "Framework self-test",
          description_zh="框架自检",
          aliases=["selftest"], args_hint="[--e2e] [--strict]", nl_triggers=["自检", "框架检查", "验证"])
def _cmd_check(args: str) -> None:
    from runtime.cli.commands.selftest import selftest
    _run_with_argv(["tagent", "selftest"] + (args.split() if args.strip() else []), selftest)


@register("demo", "Quick demo",
          description_zh="快速演示",
          args_hint="[--real-llm]", nl_triggers=["演示", "demo", "试一下"])
def _cmd_demo(args: str) -> None:
    from runtime.cli.commands.demo import demo
    _run_with_argv(["tagent", "demo"] + (args.split() if args.strip() else []), demo)


# ═══════════════════════════════════════════════════════════════════
# REPL-only commands (handlers in commands/slash_handlers.py)
# ═══════════════════════════════════════════════════════════════════

from runtime.cli.commands.slash_handlers import (
    _cmd_status, _cmd_model, _cmd_cache, _rerun_history, _cmd_history,
    _cmd_fc, _cmd_update, _cmd_hook, _cmd_skin, _cmd_lang,
    _cmd_personality, _cmd_tools, _cmd_context, _cmd_clear, _cmd_undo,
    _cmd_retry, _cmd_cost, _cmd_sessions, _cmd_resume, _cmd_export,
    _cmd_compact, _cmd_remember, _cmd_forget, _cmd_memory,
    _cmd_mcp_tools, _cmd_mcp_call, _cmd_cron, _cmd_cron_health,
    _cmd_model_router, _cmd_search, _cmd_skill_score, _cmd_speak,
    _cmd_distill, _cmd_api, _cmd_plugins_list, _cmd_alias, _cmd_ws,
    _cmd_gateway, _cmd_task, _cmd_cross, _cmd_clean, _cmd_data,
    _cmd_prioritize, _cmd_progress, _cmd_flaky, _cmd_regression,
    _cmd_insights, _cmd_nudge,
)

@register("status", "Session status + stats", description_zh="会话状态统计", nl_triggers=["状态", "会话", "当前状态", "怎么样"])
def _repl_status(args): _cmd_status(args)

@register("model", "Switch LLM provider/model", description_zh="切换大模型", nl_triggers=["模型", "切换模型", "大模型", "换模型", "改模型"])
def _repl_model(args): _cmd_model(args)

@register("cache", "LLM cache stats/clear", description_zh="缓存统计/清理", nl_triggers=["缓存", "清缓存", "缓存统计"])
def _repl_cache(args): _cmd_cache(args)

@register("history", "Command history", description_zh="命令历史", aliases=["!"], nl_triggers=["历史", "命令历史", "之前的命令"])
def _repl_history(args): _cmd_history(args)

@register("fc", "Fix last typo (thefuck)", description_zh="修复上次命令拼写", aliases=["fuck"], nl_triggers=["修复", "纠正", "修正", "打错了", "刚才那个"])
def _repl_fc(args): _cmd_fc(args)

@register("update", "Check for updates", description_zh="检查新版本", nl_triggers=["更新", "检查更新", "新版本"])
def _repl_update(args): _cmd_update(args)

@register("hook", "Lifecycle hooks", description_zh="钩子管理", nl_triggers=["钩子", "hook", "生命周期"])
def _repl_hook(args): _cmd_hook(args)

@register("skin", "Switch CLI theme", description_zh="切换皮肤", nl_triggers=["皮肤", "主题", "换皮肤", "切换主题"])
def _repl_skin(args): _cmd_skin(args)

@register("lang", "Switch UI language", description_zh="切换语言", nl_triggers=["语言", "切换语言", "中文", "英文"])
def _repl_lang(args): _cmd_lang(args)

@register("personality", "Set agent persona", description_zh="设置智能体人格", nl_triggers=["人格", "角色", "性格", "切换人格"])
def _repl_personality(args): _cmd_personality(args)

@register("tools", "List agents/skills", description_zh="列出智能体/技能", nl_triggers=["工具", "智能体", "技能列表", "agents"])
def _repl_tools(args): _cmd_tools(args)

@register("context", "Show conversation", description_zh="查看对话上下文", nl_triggers=["上下文", "对话记录", "聊天记录", "刚才说了啥"])
def _repl_context(args): _cmd_context(args)

@register("clear", "Reset memory", description_zh="清除对话记忆", nl_triggers=["清除", "清空", "重置", "忘掉", "重新开始"])
def _repl_clear(args): _cmd_clear(args)

@register("undo", "Remove last exchange", description_zh="撤销上一条", nl_triggers=["撤销", "撤回", "undo"])
def _repl_undo(args): _cmd_undo(args)

@register("retry", "Re-run last prompt", description_zh="重试上一条", nl_triggers=["重试", "再来一次", "retry"])
def _repl_retry(args): _cmd_retry(args)

@register("cost", "Token usage + cost", description_zh="费用统计", aliases=["usage"], nl_triggers=["费用", "成本", "花了多少", "token"])
def _repl_cost(args): _cmd_cost(args)

@register("sessions", "Saved sessions", description_zh="已保存会话", nl_triggers=["会话列表", "保存的会话", "存档"])
def _repl_sessions(args): _cmd_sessions(args)

@register("resume", "Load session", description_zh="恢复会话", nl_triggers=["恢复", "继续", "加载会话", "resume"])
def _repl_resume(args): _cmd_resume(args)

@register("export", "Export conversation", description_zh="导出对话", nl_triggers=["导出", "导出对话", "保存对话", "export"])
def _repl_export(args): _cmd_export(args)

@register("compact", "Compress context", description_zh="压缩上下文", nl_triggers=["压缩", "精简", "总结", "摘要"])
def _repl_compact(args): _cmd_compact(args)

@register("remember", "Save fact", description_zh="记住事实", nl_triggers=["记住", "记住这个", "记下来", "备忘"])
def _repl_remember(args): _cmd_remember(args)

@register("forget", "Remove fact", description_zh="忘记事实", nl_triggers=["忘记", "删掉记忆", "清除记忆"])
def _repl_forget(args): _cmd_forget(args)

@register("memory", "Show MEMORY.md", description_zh="查看记忆", nl_triggers=["记忆", "我的记忆", "查看记忆", "备忘录"])
def _repl_memory(args): _cmd_memory(args)

@register("nudge", "Suggest facts", description_zh="扫描会话建议记忆", nl_triggers=["提醒", "建议", "有什么要记的"])
def _repl_nudge(args): _cmd_nudge(args)

@register("mcp", "MCP tools list", description_zh="MCP工具列表", nl_triggers=["mcp", "MCP工具", "外部工具"])
def _repl_mcp(args): _cmd_mcp_tools(args)

@register("mcp-call", "Call MCP tool", description_zh="调用MCP工具", nl_triggers=["调用mcp", "mcp调用"])
def _repl_mcp_call(args): _cmd_mcp_call(args)

@register("cron", "Scheduled tasks", description_zh="定时任务", nl_triggers=["定时", "定时任务", "计划任务", "cron"])
def _repl_cron(args): _cmd_cron(args)

@register("cron-health", "Cron diagnostics", description_zh="定时任务诊断", nl_triggers=["定时诊断", "cron状态"])
def _repl_cron_health(args): _cmd_cron_health(args)

@register("model-router", "LLM routing config", description_zh="模型路由配置", nl_triggers=["路由", "模型路由", "路由配置"])
def _repl_model_router(args): _cmd_model_router(args)

@register("search", "Code search", description_zh="代码搜索", nl_triggers=["搜索", "查找", "搜索代码"])
def _repl_search(args): _cmd_search(args)

@register("skill-score", "Rate a skill", description_zh="技能评分", nl_triggers=["评分", "技能评分", "打分"])
def _repl_skill_score(args): _cmd_skill_score(args)

@register("speak", "Text-to-speech test", description_zh="语音测试", nl_triggers=["语音", "朗读", "说话", "tts"])
def _repl_speak(args): _cmd_speak(args)

@register("plugins", "Plugin list", description_zh="插件列表", nl_triggers=["插件", "插件列表", "扩展"])
def _repl_plugins(args): _cmd_plugins_list(args)

@register("distill", "Create skill", description_zh="蒸馏生成技能", nl_triggers=["蒸馏", "生成技能", "提炼"])
def _repl_distill(args): _cmd_distill(args)

@register("api", "API contract test", description_zh="API契约测试", nl_triggers=["api", "接口测试", "契约测试"])
def _repl_api(args): _cmd_api(args)

@register("alias", "Command shortcuts", description_zh="命令别名", nl_triggers=["别名", "命令别名", "快捷方式"])
def _repl_alias(args): _cmd_alias(args)

@register("ws", "Workspace manager", description_zh="工作区管理", nl_triggers=["工作区", "工作空间", "切换项目"])
def _repl_ws(args): _cmd_ws(args)

@register("gateway", "Gateway status", description_zh="网关状态", nl_triggers=["网关", "消息平台", "即时通讯"])
def _repl_gateway(args): _cmd_gateway(args)

@register("task", "Task list", description_zh="任务管理", nl_triggers=["任务", "任务列表", "代办", "todo"])
def _repl_task(args): _cmd_task(args)

@register("cross", "Cross-env test", description_zh="跨环境测试", nl_triggers=["跨环境", "跨平台", "环境对比"])
def _repl_cross(args): _cmd_cross(args)

@register("clean", "Clean temp data", description_zh="清理临时数据", nl_triggers=["清理", "打扫", "清理临时"])
def _repl_clean(args): _cmd_clean(args)

@register("data", "Generate test data", description_zh="生成测试数据", nl_triggers=["数据", "生成数据", "测试数据", "造数据"])
def _repl_data(args): _cmd_data(args)

@register("prioritize", "Priority by changes", description_zh="变更优先级排序", nl_triggers=["优先级", "排序", "先测哪个"])
def _repl_prioritize(args): _cmd_prioritize(args)

@register("progress", "Coverage matrix", description_zh="覆盖进度矩阵", nl_triggers=["进度", "覆盖率", "覆盖矩阵"])
def _repl_progress(args): _cmd_progress(args)

@register("flaky", "Flaky test mgmt", description_zh="不稳定测试管理", nl_triggers=["不稳定", "flaky", "抖动"])
def _repl_flaky(args): _cmd_flaky(args)

@register("regression", "Regression check", description_zh="回归检测", nl_triggers=["回归", "回归检测", "对比基线"])
def _repl_regression(args): _cmd_regression(args)

@register("insights", "Usage analytics", description_zh="使用分析", nl_triggers=["分析", "洞察", "使用分析", "统计"])
def _repl_insights(args): _cmd_insights(args)

# Numbered history: /1 through /9
@register("1", "Re-run command #1", description_zh="重跑第1条命令", nl_triggers=["第1条", "重跑1"])
def _repl_r1(args): _rerun_history(0)
@register("2", "Re-run command #2", description_zh="重跑第2条命令", nl_triggers=["第2条", "重跑2"])
def _repl_r2(args): _rerun_history(1)
@register("3", "Re-run command #3", description_zh="重跑第3条命令", nl_triggers=["第3条", "重跑3"])
def _repl_r3(args): _rerun_history(2)
@register("4", "Re-run command #4", description_zh="重跑第4条命令", nl_triggers=["第4条", "重跑4"])
def _repl_r4(args): _rerun_history(3)
@register("5", "Re-run command #5", description_zh="重跑第5条命令", nl_triggers=["第5条", "重跑5"])
def _repl_r5(args): _rerun_history(4)
@register("6", "Re-run command #6", description_zh="重跑第6条命令", nl_triggers=["第6条", "重跑6"])
def _repl_r6(args): _rerun_history(5)
@register("7", "Re-run command #7", description_zh="重跑第7条命令", nl_triggers=["第7条", "重跑7"])
def _repl_r7(args): _rerun_history(6)
@register("8", "Re-run command #8", description_zh="重跑第8条命令", nl_triggers=["第8条", "重跑8"])
def _repl_r8(args): _rerun_history(7)
@register("9", "Re-run command #9", description_zh="重跑第9条命令", nl_triggers=["第9条", "重跑9"])
def _repl_r9(args): _rerun_history(8)

# Done — no more registrations below this point.
