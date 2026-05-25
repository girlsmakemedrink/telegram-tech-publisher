"""Env-backed settings loader."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DrafterBackend = Literal["anthropic", "claude_code", "mock"]


class Settings(BaseSettings):
    telegram_bot_token: str = Field(..., min_length=10)
    telegram_channel_id: str = Field(..., min_length=1)
    telegram_test_channel_id: str = Field(..., min_length=1)
    github_token: str = Field(..., min_length=10)
    anthropic_api_key: str | None = None
    drafter_backend: DrafterBackend = "claude_code"
    claude_code_binary: str = "claude"
    claude_code_timeout_seconds: float = 120.0
    database_url: str = "postgresql+asyncpg://localhost/telegram_tech_publisher"
    loop_config_path: Path = Path("config/loop.toml")
    state_dir: Path = Path("~/.local/share/telegram-tech-publisher").expanduser()
    log_level: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
