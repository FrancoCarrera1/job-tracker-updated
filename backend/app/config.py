from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local", "dev", "prod"] = "local"
    app_secret_key: str = "dev-secret-change-me"
    app_base_url: str = "http://localhost:8000"
    dashboard_base_url: str = "http://localhost:5173"

    database_url: str = "postgresql+psycopg://jobtracker:changeme@postgres:5432/jobtracker"
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/gmail/callback"

    llm_provider: Literal["anthropic", "openai", "ollama"] = "anthropic"
    llm_model: str = "claude-sonnet-4-6"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""
    ollama_base_url: str = "http://host.docker.internal:11434"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    dry_run: bool = True
    per_job_approval: bool = True
    kill_switch: bool = False
    max_apps_per_day: int = 20
    max_apps_per_platform_per_day: int = 10
    max_apps_per_company_per_day: int = 1

    enable_linkedin: bool = False
    enable_indeed: bool = False
    enable_greenhouse: bool = True
    enable_lever: bool = True
    enable_clearancejobs: bool = True

    default_location: str = "San Antonio, TX"
    default_salary_min: int = 95000
    default_salary_max: int = 140000

    llm_confidence_threshold: float = Field(
        0.75,
        description="Below this, an autonomous answer to a free-text question pauses for human review.",
    )

    score_threshold_apply: float = Field(
        0.7,
        description="Postings scored at or above this auto-queue for application.",
    )
    score_threshold_review: float = Field(
        0.5,
        description="Postings between review and apply thresholds surface in the manual review queue.",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
