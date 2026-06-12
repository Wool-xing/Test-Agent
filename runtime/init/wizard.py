"""交互向导 · 问 5-6 题然后给 InitAnswers."""

from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console
from rich.prompt import Confirm, IntPrompt

from runtime.init.matrix import Matrix, load_matrix

console = Console()


@dataclass(slots=True)
class InitAnswers:
    test_type: str
    platform: str
    llm_provider: str
    bug_tracker: str
    notifiers: list[str]
    sample_target: str = ""


def _pick_one(prompt: str, options: list[tuple[str, str]], default_key: str = "") -> str:
    """options: [(key, label)]。返回选中的 key。"""
    console.print(f"\n[bold cyan]{prompt}[/]")
    default_idx = 1
    for i, (k, label) in enumerate(options, 1):
        marker = ""
        if k == default_key:
            marker = " [dim](默认)[/]"
            default_idx = i
        console.print(f"  [yellow]{i}[/]) {label}{marker}")
    idx = IntPrompt.ask("选编号", default=default_idx, show_default=True)
    idx = max(1, min(len(options), idx))
    return options[idx - 1][0]


def _pick_many(prompt: str, options: list[tuple[str, str]], default_keys: list[str] | None = None) -> list[str]:
    """多选,默认空。输入逗号分隔编号(如 `1,3`),空 = 默认。"""
    default_keys = default_keys or []
    console.print(f"\n[bold cyan]{prompt}[/]")
    default_indices: list[int] = []
    for i, (k, label) in enumerate(options, 1):
        marker = ""
        if k in default_keys:
            marker = " [dim](默认)[/]"
            default_indices.append(i)
        console.print(f"  [yellow]{i}[/]) {label}{marker}")
    default_str = ",".join(str(i) for i in default_indices) or "1"
    raw = console.input(f"逗号分隔编号(默认 {default_str},按 Enter 用默认): ").strip()
    if not raw:
        return default_keys or [options[0][0]]
    picks: list[str] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk.isdigit():
            continue
        i = max(1, min(len(options), int(chunk)))
        picks.append(options[i - 1][0])
    return picks or [options[0][0]]


def run_wizard(matrix: Matrix | None = None) -> InitAnswers:
    m = matrix or load_matrix()
    console.print("[bold green]Test-Agent · `tagent init` 配置向导[/]")
    console.print("[dim]5-6 题 · 全部用回车选默认 · 后悔可重跑覆盖[/]\n")

    test_type = _pick_one(
        "1) 你要测什么?(8 选)",
        [(k, f"{v.label} — [dim]{v.description}[/]") for k, v in m.test_types.items()],
        default_key="web",
    )
    chosen_test = m.test_types[test_type]

    platform = _pick_one(
        "2) 跑在哪个平台?(6 选)",
        [(k, v.label) for k, v in m.platforms.items()],
        default_key=chosen_test.default_platform,
    )

    llm_provider = _pick_one(
        "3) 用哪个 LLM provider?(5 选)",
        [(k, v.label) for k, v in m.llm_providers.items()],
        default_key="claude",
    )

    bug_tracker = _pick_one(
        "4) BugTracker?",
        [(k, v.label) for k, v in m.bug_trackers.items()],
        default_key="zentao",
    )

    notifiers = _pick_many(
        "5) 通知渠道?",
        [(k, v.label) for k, v in m.notifiers.items()],
        default_keys=["wechat"],
    )

    if Confirm.ask("\n6) 想顺便填个 sample target 用于 selftest?(空跳过)", default=False):
        sample_target = console.input("sample target (URL / path / 描述): ").strip()
    else:
        sample_target = ""

    return InitAnswers(
        test_type=test_type,
        platform=platform,
        llm_provider=llm_provider,
        bug_tracker=bug_tracker,
        notifiers=notifiers,
        sample_target=sample_target,
    )


def from_args(
    test_type: str,
    platform: str,
    llm_provider: str,
    bug_tracker: str,
    notifiers: list[str],
    sample_target: str = "",
    matrix: Matrix | None = None,
) -> InitAnswers:
    """非交互(--test-type 等参数 / preset / 测试)调本。"""
    m = matrix or load_matrix()
    if test_type not in m.test_types:
        raise KeyError(f"test_type {test_type!r} not in matrix; available={sorted(m.test_types)}")
    if platform not in m.platforms:
        raise KeyError(f"platform {platform!r} not in matrix; available={sorted(m.platforms)}")
    if llm_provider not in m.llm_providers:
        raise KeyError(f"llm_provider {llm_provider!r} not in matrix; available={sorted(m.llm_providers)}")
    if bug_tracker not in m.bug_trackers:
        raise KeyError(f"bug_tracker {bug_tracker!r} not in matrix; available={sorted(m.bug_trackers)}")
    for n in notifiers:
        if n not in m.notifiers:
            raise KeyError(f"notifier {n!r} not in matrix; available={sorted(m.notifiers)}")
    return InitAnswers(
        test_type=test_type,
        platform=platform,
        llm_provider=llm_provider,
        bug_tracker=bug_tracker,
        notifiers=list(notifiers),
        sample_target=sample_target,
    )


PRESETS: dict[str, dict] = {
    "minimal": {
        "test_type": "web",
        "platform": "linux",
        "llm_provider": "ollama",
        "bug_tracker": "webhook",
        "notifiers": ["email"],
    },
    "saas-web": {
        "test_type": "web",
        "platform": "linux",
        "llm_provider": "claude",
        "bug_tracker": "github",
        "notifiers": ["slack", "email"],
    },
    "国内-web": {
        "test_type": "web",
        "platform": "linux",
        "llm_provider": "qwen",
        "bug_tracker": "zentao",
        "notifiers": ["wechat", "feishu", "dingtalk"],
    },
    "mobile-android": {
        "test_type": "mobile",
        "platform": "android",
        "llm_provider": "claude",
        "bug_tracker": "jira",
        "notifiers": ["slack"],
    },
    "security-pentest": {
        "test_type": "security",
        "platform": "linux",
        "llm_provider": "claude",
        "bug_tracker": "github",
        "notifiers": ["email"],
    },
}


def from_preset(name: str, matrix: Matrix | None = None) -> InitAnswers:
    if name not in PRESETS:
        raise KeyError(f"preset {name!r} not found; available={sorted(PRESETS)}")
    return from_args(matrix=matrix, **PRESETS[name])
