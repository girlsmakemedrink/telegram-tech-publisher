"""Settings loader: env-backed; rejects missing/short tokens."""

import pytest
from pydantic import ValidationError

from telegram_tech_publisher.config import Settings


def test_settings_loads_from_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abcdefghijklmnop")
    monkeypatch.setenv("TELEGRAM_TEST_CHANNEL_ID", "@my_test_channel")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_abcdefghijklmnop")

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.telegram_bot_token == "123:abcdefghijklmnop"
    assert settings.telegram_test_channel_id == "@my_test_channel"
    assert settings.github_token == "ghp_abcdefghijklmnop"
    assert settings.log_level == "INFO"
    assert "postgresql+asyncpg" in settings.database_url


def test_settings_rejects_short_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "short")  # < min_length=10
    monkeypatch.setenv("TELEGRAM_TEST_CHANNEL_ID", "@x")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_abcdefghijklmnop")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]
