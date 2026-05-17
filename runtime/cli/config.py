"""tagent config — LLM provider configuration (V1.22.0 · Step 2 multi-model onboarding).

5 sub-commands:
  list       — list 6 built-in + path-B compatible examples
  show       — show current .env config (keys fully redacted)
  use        — path A: switch to built-in provider, write TAGENT_LLM_PROVIDER + vendor key placeholder
  use-compat — path B: OpenAI-compatible fallback channel (any vendor, plug-and-play)
  unset      — remove specified key from .env (V1.25.0)

env file priority: CWD/.env -> repo-root/.env. Always backup to .env.bak before writing.
"""

from __future__ import annotations

from pathlib import Path

import typer

config_app = typer.Typer(add_completion=False, help="LLM provider config (path A: 6 built-in + path B: any OpenAI-compatible vendor)")

BUILTIN_PROVIDERS: dict[str, dict[str, str | None]] = {
    "claude": {
        "env_key": "ANTHROPIC_API_KEY",
        "model": "anthropic/claude-sonnet-4-6",
        "url": "https://console.anthropic.com/",
    },
    "openai": {
        "env_key": "OPENAI_API_KEY",
        "model": "openai/gpt-4o",
        "url": "https://platform.openai.com/",
    },
    "gemini": {
        "env_key": "GEMINI_API_KEY",
        "model": "gemini/gemini-1.5-pro",
        "url": "https://aistudio.google.com/apikey",
    },
    "deepseek": {
        "env_key": "DEEPSEEK_API_KEY",
        "model": "deepseek/deepseek-chat",
        "url": "https://platform.deepseek.com/",
    },
    "qwen": {
        "env_key": "DASHSCOPE_API_KEY",
        "model": "dashscope/qwen-plus",
        "url": "https://dashscope.aliyun.com/",
    },
    "ollama": {
        "env_key": None,
        "model": "ollama/qwen2.5:7b",
        "url": "http://localhost:11434",
    },
}

COMPAT_EXAMPLES: dict[str, str] = {
    "zhipu (智谱)": "https://open.bigmodel.cn/api/paas/v4 · glm-4-flash",
    "doubao (豆包)": "https://ark.cn-beijing.volces.com/api/v3 · doubao-pro",
    "kimi (Moonshot)": "https://api.moonshot.cn/v1 · moonshot-v1-8k",
    "baichuan (百川)": "https://api.baichuan-ai.com/v1 · Baichuan2-Turbo",
    "xunfei (讯飞)": "https://spark-api-open.xf-yun.com/v1 · 4.0Ultra",
}

TRACKED_KEYS = (
    "TAGENT_LLM_PROVIDER",
    "TAGENT_LLM_API_BASE",
    "TAGENT_LLM_API_KEY",
)

VENDOR_KEYS = (
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "DEEPSEEK_API_KEY",
    "DASHSCOPE_API_KEY",
)


def _find_env_file(cwd: Path | None = None) -> Path:
    """优先 CWD/.env. 不存仍返回此路径 (调用者据存在性决定写/读)."""
    base = cwd or Path.cwd()
    return base / ".env"


def _parse_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def _write_env(path: Path, env: dict[str, str]) -> None:
    """写 env 文件. 已存则先备份 .env.bak (覆盖). 保留 insertion 序."""
    if path.exists():
        backup = path.with_name(path.name + ".bak")
        backup.write_bytes(path.read_bytes())
    lines = [f"{key}={value}" for key, value in env.items() if value is not None]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _mask(secret: str) -> str:
    if not secret or len(secret) < 8:
        return "***"
    return f"{secret[:4]}...{secret[-4:]}"


@config_app.command("list")
def cmd_list() -> None:
    """List 6 built-in providers (path A) + path B compatible examples."""
    typer.echo("📦 Built-in providers (path A · litellm direct):")
    for name, spec in BUILTIN_PROVIDERS.items():
        env_hint = spec["env_key"] or "(no key needed, local)"
        model = spec["model"] or ""
        typer.echo(f"  {name:10s} model={model:40s} key_env={env_hint}")
    typer.echo("")
    typer.echo("🌐 Compatible providers (path B · OpenAI protocol, use 'use-compat'):")
    for name, info in COMPAT_EXAMPLES.items():
        typer.echo(f"  {name:18s} {info}")
    typer.echo("")
    typer.echo("📖 Full cookbook: config/llm-providers.md")


@config_app.command("show")
def cmd_show() -> None:
    """显当前 .env (TAGENT_LLM_* + 厂商 key 全脱敏)."""
    env_path = _find_env_file()
    typer.echo(f"📄 .env: {env_path.resolve()}")
    if not env_path.exists():
        typer.echo("  (文件不存, 用 'tagent config use <provider>' 创建)")
        return
    env = _parse_env(env_path)
    for key in TRACKED_KEYS:
        value = env.get(key, "")
        if key.endswith("KEY"):
            value = _mask(value) if value else ""
        typer.echo(f"  {key}={value or '(未设)'}")
    for vendor_key in VENDOR_KEYS:
        if vendor_key in env:
            typer.echo(f"  {vendor_key}={_mask(env[vendor_key])}")


@config_app.command("use")
def cmd_use(
    provider: str = typer.Argument(..., help=f"内置 6 之一: {', '.join(BUILTIN_PROVIDERS.keys())}"),
) -> None:
    """Path A: switch to specified built-in provider, write .env."""
    if provider not in BUILTIN_PROVIDERS:
        typer.echo(f"❌ unknown provider: {provider}")
        typer.echo(f"   available: {', '.join(BUILTIN_PROVIDERS.keys())}")
        typer.echo("   compatible providers: use 'tagent config use-compat'")
        raise typer.Exit(2)

    spec = BUILTIN_PROVIDERS[provider]
    env_path = _find_env_file()
    env = _parse_env(env_path)
    env["TAGENT_LLM_PROVIDER"] = provider
    env.pop("TAGENT_LLM_API_BASE", None)
    env.pop("TAGENT_LLM_API_KEY", None)
    vendor_key = spec["env_key"]
    if vendor_key and vendor_key not in env:
        env[vendor_key] = "<your-key-here>"

    _write_env(env_path, env)
    typer.echo(f"✅ wrote {env_path}: TAGENT_LLM_PROVIDER={provider}")
    if vendor_key:
        typer.echo(f"⚠️  set {vendor_key} with real key, then run 'tagent demo'")
        typer.echo(f"   sign up: {spec['url']}")
    else:
        typer.echo(f"   {provider} runs locally, start: {spec['url']}")


@config_app.command("use-compat")
def cmd_use_compat(
    base: str = typer.Option(..., "--base", help="OpenAI 兼容 endpoint URL"),
    key: str = typer.Option(..., "--key", help="API key"),
    model: str = typer.Option(..., "--model", help="model 名 (不含 openai/ 前缀)"),
) -> None:
    """Path B: OpenAI-compatible fallback channel (Zhipu / Doubao / Kimi / Baichuan / Xunfei / ...)."""
    env_path = _find_env_file()
    env = _parse_env(env_path)
    env["TAGENT_LLM_PROVIDER"] = f"openai/{model}"
    env["TAGENT_LLM_API_BASE"] = base
    env["TAGENT_LLM_API_KEY"] = key

    _write_env(env_path, env)
    typer.echo(f"✅ 写 {env_path}: 路径 B 通用通道")
    typer.echo(f"   TAGENT_LLM_PROVIDER=openai/{model}")
    typer.echo(f"   TAGENT_LLM_API_BASE={base}")
    typer.echo(f"   TAGENT_LLM_API_KEY={_mask(key)}")
    typer.echo("")
    typer.echo("验路由: tagent demo")


@config_app.command("unset")
def cmd_unset(
    key: str = typer.Argument(..., help="要移除的 key (TAGENT_LLM_PROVIDER / TAGENT_LLM_API_BASE / TAGENT_LLM_API_KEY / 厂商 key)"),
) -> None:
    """移除 .env 中指定 key (自动备份 .env.bak)."""
    env_path = _find_env_file()
    if not env_path.exists():
        typer.echo(f"❌ .env 不存在: {env_path.resolve()}")
        raise typer.Exit(2)

    env = _parse_env(env_path)
    if key not in env:
        typer.echo(f"⚠️  key 不存在: {key} (当前 env 中未设)")
        raise typer.Exit(0)

    old_value = _mask(env[key]) if key.endswith("KEY") or key.endswith("API_KEY") else env[key]
    del env[key]
    _write_env(env_path, env)
    typer.echo(f"✅ 已移除 {key} (原值: {old_value})")
    typer.echo(f"   备份: {env_path}.bak")
    typer.echo(f"   下一步: tagent config use <provider> 重设, 或 tagent config show 验证")
