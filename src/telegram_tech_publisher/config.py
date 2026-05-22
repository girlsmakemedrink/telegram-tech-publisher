"""Env-backed settings loader."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str = Field(..., min_length=10)
    telegram_test_channel_id: str = Field(..., min_length=1)
    github_token: str = Field(..., min_length=10)
    database_url: str = "postgresql+asyncpg://localhost/telegram_tech_publisher"
    anthropic_api_key: str | None = None
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
