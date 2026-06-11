"""Runtime settings (env-driven, pydantic-settings)."""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_project_root() -> Path:
    """Resolve project root — handles PyInstaller onefile bundles."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Centralized runtime config.

    All env vars prefixed `TAGENT_`. `.env` at project root is auto-loaded.
    """

    model_config = SettingsConfigDict(
        env_prefix="TAGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    project_root: Path = Field(default_factory=_get_project_root)
    experts_dir: Path = Field(default=Path("ai/agents"))
    skills_dir: Path = Field(default=Path("ai/skills"))
    scripts_dir: Path = Field(default=Path("utils"))
    workspace_dir: Path = Field(default=Path("workspace"))
    config_dir: Path = Field(default=Path("deploy/config"))
    templates_dir: Path = Field(default=Path("deploy/config/templates"))

    llm_provider: str = Field(default="claude")
    llm_provider_fallback: str = Field(default="ollama")
    llm_model: str = Field(default="claude-sonnet-4-6")
    llm_model_fallback: str = Field(default="qwen2.5:7b")
    llm_timeout_seconds: int = Field(default=60)
    llm_max_retries: int = Field(default=2)

    db_url: str = Field(default="")
    minio_endpoint: str = Field(default="localhost:9000")
    minio_access_key: str = Field(default="")
    minio_secret_key: str = Field(default="")
    minio_bucket: str = Field(default="tagent-evidence")
    minio_secure: bool = Field(default=False)

    prefect_api_url: str = Field(default="http://localhost:4200/api")
    otel_endpoint: str = Field(default="http://localhost:4317")
    otel_enabled: bool = Field(default=False)

    api_host: str = Field(default="127.0.0.1")
    api_port: int = Field(default=8800)
    api_auth_token: str = Field(default="")
    log_level: str = Field(default="INFO")

    # ── Agent runtime ──
    agent_max_tokens: int = Field(default=1500)
    test_timeout_seconds: int = Field(default=3600)
    max_concurrent_runs: int = Field(default=4)

    # ── Safety gates ──
    chaos_authorized: bool = Field(default=False)
    pentest_authorized: bool = Field(default=False)

    # ── Artifacts & reporting ──
    artifact_retention_days: int = Field(default=30)
    max_artifact_size_mb: int = Field(default=100)
    report_format: str = Field(default="markdown")

    # ── Notifications ──
    notification_webhook_url: str = Field(default="")
    error_report_recipients: str = Field(default="")

    # ── External integrations ──
    dingtalk_app_key: str = Field(default="")
    dingtalk_app_secret: str = Field(default="")
    dingtalk_agent_id: str = Field(default="")
    dingtalk_webhook_url: str = Field(default="")
    telegram_bot_token: str = Field(default="")
    telegram_chat_id: str = Field(default="")
    zentao_url: str = Field(default="")
    zentao_account: str = Field(default="")
    zentao_password: str = Field(default="")
    github_token: str = Field(default="")
    github_repo: str = Field(default="")
    prd_http_token: str = Field(default="")

    # ── Enterprise / CI ──
    proxy_url: str = Field(default="")
    trusted_ca_bundle: str = Field(default="")
    selenium_hub_url: str = Field(default="")
    docker_host: str = Field(default="")
    ci_mode: bool = Field(default=False)

    def model_post_init(self, _context: object) -> None:
        """Resolve relative Path fields to absolute after model init."""
        root = self.project_root
        for attr in ("experts_dir", "skills_dir", "scripts_dir", "workspace_dir",
                     "config_dir", "templates_dir"):
            p = getattr(self, attr)
            if not p.is_absolute():
                object.__setattr__(self, attr, (root / p).resolve())

    def resolve(self, rel: Path) -> Path:
        return rel if rel.is_absolute() else (self.project_root / rel).resolve()

    def validate_startup(self) -> list[dict[str, str]]:
        """Check config health at startup. Returns list of {level, key, message}."""
        import os

        issues: list[dict[str, str]] = []

        # LLM key check
        llm_key = os.getenv("TAGENT_LLM_API_KEY", "")
        if not llm_key:
            alt_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DASHSCOPE_API_KEY", "DEEPSEEK_API_KEY"]
            if not any(os.getenv(k) for k in alt_keys):
                issues.append({
                    "level": "warning",
                    "key": "llm_api_key",
                    "message": "No LLM API key found — LLM calls will fail. Set TAGENT_LLM_API_KEY in .env or environment.",
                })

        # Critical dirs exist
        for attr, label in [("experts_dir", "experts"), ("skills_dir", "skills"), ("scripts_dir", "scripts")]:
            p = self.resolve(getattr(self, attr))
            if not p.is_dir():
                issues.append({
                    "level": "error",
                    "key": attr,
                    "message": f"{label} directory not found: {p}",
                })

        # DB URL: warn if postgres and no psycopg
        if self.db_url and "postgres" in self.db_url:
            try:
                import psycopg  # noqa: F401
            except ImportError:
                issues.append({
                    "level": "warning",
                    "key": "db_url",
                    "message": "PostgreSQL URL configured but psycopg not installed — database unavailable",
                })

        return issues


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
