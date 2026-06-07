"""tagent config CLI 测试 (V1.22.0 · 4 子命令 list/show/use/use-compat).

本文件中所有 API key/secret 均为虚构测试数据，不是真实凭据。
All API keys and secrets in this file are fake test fixtures — not real credentials.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from runtime.cli.config import (
    BUILTIN_PROVIDERS,
    _find_env_file,
    _mask,
    _parse_env,
    _write_env,
    config_app,
)

runner = CliRunner()


def test_mask_short_returns_stars():
    assert _mask("") == "***"
    assert _mask("abc") == "***"
    assert _mask("1234567") == "***"


def test_mask_long_preserves_head_tail():
    assert _mask("sk-1234567890abcdef") == "sk-1...cdef"


def test_parse_env_strips_quotes_and_comments(tmp_path: Path):
    p = tmp_path / ".env"
    p.write_text(
        '# comment\nTAGENT_LLM_PROVIDER=claude\nANTHROPIC_API_KEY="sk-foo"\nOTHER=\'bar\'\n',
        encoding="utf-8",
    )
    env = _parse_env(p)
    assert env["TAGENT_LLM_PROVIDER"] == "claude"
    assert env["ANTHROPIC_API_KEY"] == "sk-foo"
    assert env["OTHER"] == "bar"
    assert "# comment" not in env


def test_parse_env_missing_file_returns_empty(tmp_path: Path):
    assert _parse_env(tmp_path / "nonexistent.env") == {}


def test_write_env_creates_backup(tmp_path: Path):
    p = tmp_path / ".env"
    p.write_text("OLD=1\n", encoding="utf-8")
    _write_env(p, {"NEW": "2"})
    assert p.read_text(encoding="utf-8").strip() == "NEW=2"
    assert (tmp_path / ".env.bak").read_text(encoding="utf-8").strip() == "OLD=1"


def test_write_env_no_backup_when_fresh(tmp_path: Path):
    p = tmp_path / ".env"
    _write_env(p, {"NEW": "1"})
    assert p.exists()
    assert not (tmp_path / ".env.bak").exists()


def test_find_env_uses_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    assert _find_env_file().resolve() == (tmp_path / ".env").resolve()


def test_list_shows_six_builtins_and_compat_examples():
    result = runner.invoke(config_app, ["list"])
    assert result.exit_code == 0
    for name in BUILTIN_PROVIDERS:
        assert name in result.stdout
    assert "zhipu" in result.stdout
    assert "doubao" in result.stdout
    assert "deploy/config/llm-providers.md" in result.stdout


def test_show_missing_env_hints_creation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(config_app, ["show"])
    assert result.exit_code == 0
    assert "file not found" in result.stdout


def test_show_masks_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "TAGENT_LLM_PROVIDER=claude\nANTHROPIC_API_KEY=sk-supersecretkey12345\n",
        encoding="utf-8",
    )
    result = runner.invoke(config_app, ["show"])
    assert result.exit_code == 0
    assert "TAGENT_LLM_PROVIDER=claude" in result.stdout
    assert "sk-supersecretkey12345" not in result.stdout
    assert "sk-s...2345" in result.stdout


def test_use_writes_provider_and_placeholder_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(config_app, ["use", "claude"])
    assert result.exit_code == 0
    env = _parse_env(tmp_path / ".env")
    assert env["TAGENT_LLM_PROVIDER"] == "claude"
    assert env["ANTHROPIC_API_KEY"] == "<your-key-here>"


def test_use_clears_compat_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "TAGENT_LLM_API_BASE=https://old.example/v1\nTAGENT_LLM_API_KEY=oldkey\n",
        encoding="utf-8",
    )
    result = runner.invoke(config_app, ["use", "openai"])
    assert result.exit_code == 0
    env = _parse_env(tmp_path / ".env")
    assert env["TAGENT_LLM_PROVIDER"] == "openai"
    assert "TAGENT_LLM_API_BASE" not in env
    assert "TAGENT_LLM_API_KEY" not in env


def test_use_ollama_no_key_message(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(config_app, ["use", "ollama"])
    assert result.exit_code == 0
    assert "runs locally" in result.stdout


def test_use_unknown_provider_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(config_app, ["use", "nonexistent-vendor"])
    assert result.exit_code == 2
    assert "unknown provider" in result.stdout


def test_use_compat_writes_three_envs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        config_app,
        [
            "use-compat",
            "--base",
            "https://open.bigmodel.cn/api/paas/v4",
            "--key",
            "zhipu-supersecret-key-1234",
            "--model",
            "glm-4-flash",
        ],
    )
    assert result.exit_code == 0
    env = _parse_env(tmp_path / ".env")
    assert env["TAGENT_LLM_PROVIDER"] == "openai/glm-4-flash"
    assert env["TAGENT_LLM_API_BASE"] == "https://open.bigmodel.cn/api/paas/v4"
    assert env["TAGENT_LLM_API_KEY"] == "zhipu-supersecret-key-1234"
    assert "zhipu-supersecret-key-1234" not in result.stdout
    assert "zhip...1234" in result.stdout
