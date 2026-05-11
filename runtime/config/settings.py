"""Runtime settings (env-driven, pydantic-settings)."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    project_root: Path = Field(default=Path(__file__).resolve().parents[2])
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

    db_url: str = Field(default="postgresql+psycopg://tagent:tagent@localhost:5432/tagent")
    minio_endpoint: str = Field(default="localhost:9000")
    minio_access_key: str = Field(default="tagent")
    minio_secret_key: str = Field(default="tagent-secret")
    minio_bucket: str = Field(default="tagent-evidence")
    minio_secure: bool = Field(default=False)

    prefect_api_url: str = Field(default="http://localhost:4200/api")
    otel_endpoint: str = Field(default="http://localhost:4317")
    otel_enabled: bool = Field(default=False)

    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8800)

    def resolve(self, rel: Path) -> Path:
        return rel if rel.is_absolute() else (self.project_root / rel).resolve()


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
