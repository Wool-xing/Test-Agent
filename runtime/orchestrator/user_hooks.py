"""User-facing hook management — register, list, remove lifecycle hooks.

Hooks persist to workspace/gateway/hooks.json.
Phases: before (pre-execution), after (post-execution), on_error (failure).
Pre-built useful hooks included.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class UserHook:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    phase: str = "after"  # before | after | on_error
    label: str = ""       # human-readable description
    command: str = ""     # shell command or Python code
    enabled: bool = True
    created_at: float = field(default_factory=time.time)


PREBUILT_HOOKS = [
    {
        "label": "Log node results to file",
        "phase": "after",
        "command": "python -c \"import json, sys; data=json.loads(sys.argv[1]); "
                   "open('workspace/gateway/hook_log.jsonl', 'a').write(json.dumps(data)+chr(10))\"",
    },
    {
        "label": "Notify on failure",
        "phase": "on_error",
        "command": "python -c \"import json, sys; d=json.loads(sys.argv[1]); "
                   "print('FAILED: ' + d.get('name','?') + ': ' + d.get('error','?')[:200])\"",
    },
    {
        "label": "Send webhook on completion",
        "phase": "after",
        "command": "python -c \"import json, os, sys, urllib.request; "
                   "url=os.getenv('HOOK_WEBHOOK_URL',''); "
                   "urllib.request.urlopen(urllib.request.Request(url, "
                   "data=json.dumps(json.loads(sys.argv[1])).encode(), "
                   "headers={'Content-Type':'application/json'})) if url else None\"",
    },
]


def _hooks_file() -> Path:
    d = Path(__file__).resolve().parents[2] / "workspace" / "gateway"
    d.mkdir(parents=True, exist_ok=True)
    return d / "hooks.json"


def _load() -> list[dict]:
    p = _hooks_file()
    if not p.is_file():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _save(hooks: list[dict]) -> None:
    _hooks_file().write_text(json.dumps(hooks, ensure_ascii=False, indent=2), encoding="utf-8")


def list_hooks() -> list[UserHook]:
    hooks = _load()
    return [UserHook(**{k: v for k, v in h.items() if k in UserHook.__dataclass_fields__}) for h in hooks]


def add_hook(phase: str, command: str, label: str = "") -> UserHook:
    hook = UserHook(phase=phase, command=command, label=label)
    hooks = _load()
    hooks.append(asdict(hook))
    _save(hooks)
    _activate_hook(hook)
    return hook


def remove_hook(hook_id: str) -> bool:
    hooks = _load()
    for i, h in enumerate(hooks):
        if h.get("id") == hook_id:
            hooks.pop(i)
            _save(hooks)
            return True
    return False


def _activate_hook(hook: UserHook) -> None:
    """Register hook with the global HookRegistry."""
    from runtime.orchestrator.hooks import get_hook_registry
    registry = get_hook_registry()

    ctx_str = json.dumps  # will be called with ctx dict

    def _hook_fn(node_id: str, ctx: dict[str, Any]) -> None:
        try:
            data = json.dumps({"node_id": node_id, "timestamp": time.time(), "context": ctx})
            subprocess.run(
                [sys.executable, "-c", hook.command, data],
                timeout=30, capture_output=True,
            )
        except Exception as e:
            logger.debug("user hook %s failed: %s", hook.id, e)

    if hook.phase == "before":
        registry.register_before(_hook_fn)
    elif hook.phase == "after":
        registry.register_after(_hook_fn)
    elif hook.phase == "on_error":
        registry.register_error(_hook_fn)


def activate_all() -> int:
    """Activate all enabled hooks from persistence. Returns count activated."""
    hooks = list_hooks()
    count = 0
    for h in hooks:
        if h.enabled:
            _activate_hook(h)
            count += 1
    return count
