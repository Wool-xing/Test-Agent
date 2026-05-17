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
    experts_dir: Path = Field(default=Path("02-专家定义"))
    skills_dir: Path = Field(default=Path("03-技能定义"))
    scripts_dir: Path = Field(default=Path("05-代码示例"))
    workspace_dir: Path = Field(default=Path("workspace"))

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
