"""Slash command handlers — extracted from interactive.py."""
from __future__ import annotations
import os, sys, time
from pathlib import Path
from runtime.cli._shared import console
from runtime.cli.slash_commands import _PROVIDERS
from runtime.cli.conversation import ConversationMemory
from runtime.config.settings import get_settings
from runtime.cli.interactive import _get_memory, _current_provider, _current_model, _handle_natural_language
_SESSION_FILE = get_settings().gateway_dir / "active_session.json"
_SESSION_DIR = _SESSION_FILE.parent
# Module-local mutable state (independent from interactive.py copies)
_command_history_list = []
_last_fix = None
_last_trace = None
_start_time = 0.0


def _get_memory():
    from runtime.cli.interactive import _get_memory as _m
    return _m()


def _current_provider():
    from runtime.cli.interactive import _current_provider as _f
    return _f()


def _current_model():
    from runtime.cli.interactive import _current_model as _f
    return _f()


def _closest_command(name: str) -> str | None:
    """Find closest matching command for typo correction. Returns name or None."""
    from runtime.cli.slash_commands import closest as _c
    return _c(name)


def _edit_distance(a: str, b: str) -> int:
    """Levenshtein distance between two strings."""
    if len(a) < len(b):
        a, b = b, a
    if len(b) == 0:
        return len(a)

    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(
                prev[j + 1] + 1,   # delete
                curr[j] + 1,        # insert
                prev[j] + (ca != cb),  # substitute
            ))
        prev = curr
    return prev[-1]


def _do_quit() -> None:
    _save_session()
    console.print("[dim]Session saved. Goodbye.[/]")
    raise SystemExit(0)


# ── !status ───────────────────────────────────────────────────────


def _cmd_status(args: str) -> None:
    from rich.panel import Panel

    mem = _get_memory()
    turns = len(mem.messages)
    chars = sum(len(m.content) for m in mem.messages)
    uptime_s = int(time.time() - _start_time)
    uptime = f"{uptime_s // 60}m {uptime_s % 60}s" if uptime_s > 0 else "just started"

    from runtime.cli.conversation import get_personality
    persona = get_personality()
    info = [
        f"Model:       [cyan]{_current_model()}[/]",
        f"Provider:    [cyan]{_current_provider()}[/]",
        f"Personality: [cyan]{persona or 'default'}[/]",
        f"Session:     [cyan]{mem.session_id}[/] · {turns} turns · {chars}/{mem.max_chars} chars",
        f"Uptime:      {uptime}",
    ]
    console.print(Panel("\n".join(info), title="Status", title_align="left"))

    if turns > 0:
        console.print(f"[bold]Recent ({min(turns, 5)} of {turns} turns):[/]")
        for m in mem.messages[-5:]:
            label = "[cyan]You[/]" if m.role == "user" else "[green]Agent[/]"
            text = m.content if len(m.content) <= 120 else m.content[:117] + "..."
            console.print(f"  {label}: {text}")
    else:
        console.print("[dim]No conversation yet.[/]")


# ── !model ────────────────────────────────────────────────────────


def _cmd_model(args: str) -> None:
    parts = args.strip().split()
    name = parts[0].lower() if parts else ""
    model_override = parts[1] if len(parts) > 1 else None
    current = _current_provider()

    if not name:
        console.print(f"Current: [cyan]{current}[/] → {_current_model()}\n")
        console.print("Available:")
        for p in _PROVIDERS:
            models = {
                "claude": "sonnet-4-6 / opus-4-8 / haiku-4-5",
                "openai": "gpt-4o / gpt-4.1 / o4-mini",
                "gemini": "gemini-1.5-pro / gemini-2.5-flash",
                "deepseek": "deepseek-chat / deepseek-reasoner",
                "qwen": "qwen-plus / qwen-max / qwen-turbo",
                "ollama": "any local model (e.g. qwen2.5:7b)",
            }
            marker = " [bold green]← current[/]" if p == current else ""
            detail = models.get(p, "")
            console.print(f"  [cyan]{p}[/]{marker}  [dim]{detail}[/]")
        console.print("\n[dim]Usage: !model <provider> [model]   e.g. !model deepseek deepseek-chat[/]")
        return

    # Check if user typed a model name instead of provider
    if name not in _PROVIDERS:
        # Try fuzzy match against known models → providers
        for p in _PROVIDERS:
            if name.startswith(p) or p.startswith(name):
                console.print(f"[yellow]'{name}' is a model name. Did you mean [cyan]!model {p}[/]?[/]")
                break
        else:
            console.print(f"[red]Unknown provider: {name}[/]")
            console.print(f"[dim]Available: {', '.join(_PROVIDERS)}[/]")
            console.print("[dim]Tip: provider first, then model — e.g. [cyan]!model deepseek deepseek-chat[/][/]")
        return

    os.environ["TAGENT_LLM_PROVIDER"] = name
    if model_override:
        os.environ["TAGENT_LLM_MODEL"] = model_override
    else:
        os.environ.pop("TAGENT_LLM_MODEL", None)  # use default

    # P3 #20: auto-learn provider preference
    try:
        from runtime.cli.user_profile import set_preference
        set_preference("provider", name)
        set_preference("model", _current_model())
    except Exception:
        pass

    console.print(f"[green]Switched[/] → provider: [cyan]{name}[/]  model: [cyan]{_current_model()}[/]")


# ── !cache — LLM response cache stats/clear ─────────────────────────


def _cmd_cache(args: str) -> None:
    """Show or clear the LLM response cache. Usage: !cache [clear]."""
    from runtime.router.llm_cache import cache_stats, clear_cache
    if args.strip() == "clear":
        n = clear_cache()
        console.print(f"[green]Cache cleared:[/] {n} entries removed")
        return
    stats = cache_stats()
    console.print(f"[bold]LLM Cache:[/] {stats['entries']} entries, {stats['size_kb']} KB, TTL={stats['ttl_hours']}h")
    if stats["entries"] > 0:
        console.print("[dim]Use !cache clear to flush.[/]")


# ── /! — command history ────────────────────────────────────────────


def _rerun_history(index: int) -> None:
    """Re-run a command from history by index (0=most recent)."""
    if not _command_history_list:
        console.print("[dim]No commands in history.[/]")
        return
    try:
        cmd = list(reversed(_command_history_list))[index]
        console.print(f"[dim]Re-running: [cyan]{cmd[:80]}{'...' if len(cmd) > 80 else ''}[/][/]")
        _handle_natural_language(cmd)
    except IndexError:
        console.print(f"[dim]History index {index + 1} not available.[/]")


def _cmd_history(args: str) -> None:
    """Show recent command history. Use /1..9 to re-run."""
    if not _command_history_list:
        console.print("[dim]No commands in history yet.[/]")
        return
    for i, cmd in enumerate(reversed(_command_history_list[-9:]), 1):
        preview = cmd[:100] + ("..." if len(cmd) > 100 else "")
        console.print(f"  [cyan]/{i}[/]  {preview}")
    console.print(f"[dim]Run /1 (most recent) through /{min(9, len(_command_history_list))} to re-execute.[/]")


# ── !fc — fix last command typo (thefuck-style) ────────────────────


# TheFuck-style correction rules: (match_pattern, correction, description)
_FC_RULES: list[tuple[str, str, str]] = [
    # Test-Agent specific typos
    (r"^/?tagent\b", "tagent", "tagnt → tagent"),
    (r"^!pentest-recno\b", "!pentest-recon", "recno → recon"),
    (r"^!regeresion\b", "!regression", "regeresion → regression"),
    (r"^!model\s+cluade\b", "!model claude", "cluade → claude"),
    (r"^!model\s+deepseek\b", "!model deepseek", "deepsek → deepseek"),
    # CLI command typos
    (r"^tagentr un\b", "tagent run", "tagentr → tagent"),
    (r"^python -m runtime.cli.main\s+run\b", "tagent run", "use: tagent run"),
]


def _apply_fc_rules(text: str) -> tuple[str | None, str | None]:
    """Apply TheFuck-style correction rules. Returns (corrected, reason) or (None, None)."""
    import re
    for pattern, correction, reason in _FC_RULES:
        if re.match(pattern, text, re.IGNORECASE):
            corrected = re.sub(pattern, correction, text, count=1, flags=re.IGNORECASE)
            if corrected != text:
                return corrected, reason
    return None, None


def _cmd_fc(args: str) -> None:
    """Fix last command typo. TheFuck-style: rule-based + edit-distance fallback."""
    global _last_fix
    if _last_fix is None:
        console.print("[dim]Nothing to fix. Type a command to get suggestions.[/]")
        return
    suggestion = _last_fix
    _last_fix = None
    console.print(f"[green]Running: /{suggestion}[/]")
    from runtime.cli.interactive import _BUILTIN_MAP
    _BUILTIN_MAP.get(suggestion, lambda a: None)("")


# ── /ready — release readiness score ─────────────────────────────────


def _cmd_ready(args: str) -> None:
    """Multi-dimensional release readiness check. Usage: !ready [--fast]."""
    from runtime.cli.readiness import run_readiness
    from rich.table import Table

    fast = "--fast" in args
    with console.status("[bold]Checking readiness...", spinner="dots"):
        report = run_readiness(fast=fast)

    table = Table(title="Release Readiness", show_header=True)
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")

    for g in report.gates:
        icon = "[green]✓[/]" if g.passed else "[red]✗[/]"
        table.add_row(f"{icon} {g.label}", f"{g.score:.0%}", g.detail)

    console.print(table)

    score_pct = report.overall_score * 100
    color = "green" if report.ready else "red"
    verdict = "✓ Ready to release" if report.ready else "✗ Not ready"
    console.print(f"\n[{color}]Overall: {score_pct:.0f}% — {verdict}[/]")
    if not report.ready:
        console.print("[dim]Fix failing checks above before release.[/]")


# ── /update — check for new version ──────────────────────────────────


def _cmd_update(args: str) -> None:
    """Check GitHub for newer version. Thin wrapper around deploy/config/check_version.py."""
    import subprocess
    import sys
    from runtime.config.settings import get_settings
    checker = get_settings().config_dir / "check_version.py"
    if not checker.is_file():
        console.print("[dim]Version checker not found.[/]")
        return
    r = subprocess.run([sys.executable, str(checker)], capture_output=True, text=True)
    if r.stdout.strip():
        console.print(r.stdout.strip())
    else:
        console.print("[green]Already up to date.[/]")
