"""Onboarding wizard (§补-5) — first-run guided setup.

Steps:
  1. Language selection (zh/en)
  2. LLM provider configuration
  3. Run sample test
  4. Show next steps
"""

from __future__ import annotations

import typer

from runtime.cli._shared import console


def register(app: typer.Typer) -> None:
    @app.command()
    def onboard():
        """Interactive first-time setup wizard."""
        console.print("[bold cyan]Welcome to Test-Agent V2.0.0![/]")
        console.print()

        # Step 1: Language
        lang = _step_language()
        t = _Translations(lang)

        # Step 2: LLM provider
        provider = _step_llm_provider(t)

        # Step 3: Sample test
        _step_sample_test(t, provider)

        # Step 4: Next steps
        _step_next_steps(t)


class _Translations:
    def __init__(self, lang: str):
        self._lang = lang

    def _(self, zh: str, en: str) -> str:
        return zh if self._lang == "zh" else en


def _step_language() -> str:
    console.print("[bold]Step 1/4: Language / 语言[/]")
    console.print("  [1] 中文")
    console.print("  [2] English")
    choice = typer.prompt("Choose", default="1")
    return "zh" if choice == "1" else "en"


def _step_llm_provider(t: _Translations) -> str:
    console.print()
    console.print(f"[bold]Step 2/4: {t._('LLM Provider 配置', 'LLM Provider Setup')}[/]")
    console.print(f"  {t._('Test-Agent 需要 LLM 来理解测试需求', 'Test-Agent needs an LLM to understand test requests')}")
    console.print()
    console.print("  [1] Claude (Anthropic)")
    console.print("  [2] OpenAI (GPT)")
    console.print("  [3] DeepSeek")
    console.print("  [4] Ollama (本地免费, Local Free)")
    console.print(f"  [5] {t._('跳过, 稍后配置', 'Skip for now')}")
    choice = typer.prompt(t._("选择", "Choose"), default="4")

    providers = {"1": "claude", "2": "openai", "3": "deepseek", "4": "ollama", "5": "stub"}
    provider = providers.get(choice, "ollama")

    if provider != "stub":
        key = typer.prompt(
            t._(f"输入 {provider} API Key (输入后不显示)", f"Enter {provider} API Key (hidden)"),
            hide_input=True, default=""
        )
        if key:
            import os
            os.environ["TAGENT_LLM_PROVIDER"] = provider
            os.environ["TAGENT_LLM_API_KEY"] = key
            console.print(f"  [green]{t._('已配置', 'Configured')} ✓[/]")
        else:
            console.print(f"  [yellow]{t._('跳过, 使用默认配置', 'Skipped, using defaults')}[/]")
    else:
        console.print(f"  [dim]{t._('跳过LLM配置, 使用stub模式', 'Skipped LLM config, using stub mode')}[/]")

    return provider


def _step_sample_test(t: _Translations, provider: str) -> None:
    console.print()
    console.print(f"[bold]Step 3/4: {t._('运行示例测试', 'Run Sample Test')}[/]")
    console.print(f"  {t._('执行中...', 'Running...')}")
    try:
        import os
        os.environ.setdefault("TAGENT_LLM_PROVIDER", provider)
        from runtime.config.settings import get_settings
        issues = get_settings().validate_startup()
        errors = [i for i in issues if i["level"] == "error"]
        warnings = [i for i in issues if i["level"] == "warning"]
        if errors:
            console.print(f"  [red]✗ {len(errors)} {t._('个错误', ' errors')}[/]")
            for e in errors[:3]:
                console.print(f"    - {e['message']}")
        elif warnings:
            console.print(f"  [yellow]⚠ {len(warnings)} {t._('个警告', ' warnings')}[/]")
        else:
            console.print(f"  [green]✓ {t._('环境检查通过', 'Environment check passed')}[/]")
    except Exception as e:
        console.print(f"  [yellow]⚠ {t._('环境检查部分通过', 'Partial check')}: {e}[/]")


def _step_next_steps(t: _Translations) -> None:
    console.print()
    console.print(f"[bold]Step 4/4: {t._('下一步', 'Next Steps')}[/]")
    console.print()
    console.print(f"  tagent init --preset minimal     {t._('# 初始化项目', '# Initialize project')}")
    console.print(f"  tagent run '{t._('检查网站是否正常', 'Check if website is up')}'")
    console.print(f"  tagent chat                      {t._('# 进入对话模式', '# Enter chat mode')}")
    console.print(f"  tagent tui                       {t._('# 打开仪表盘', '# Open dashboard')}")
    console.print(f"  tagent help                      {t._('# 查看所有命令', '# View all commands')}")
    console.print()
    console.print(f"[bold green]{t._('✓ 设置完成!', '✓ Setup complete!')}[/]")
    console.print(f"[dim]{t._('详细文档: docs/getting-started/', 'Docs: docs/getting-started/')}[/]")
