"""Settings loader: env-backed; rejects missing/short tokens."""

import pytest
from pydantic import ValidationError

from telegram_tech_publisher.config import Settings


def test_settings_loads_from_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abcdefghijklmnop")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@my_channel")
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
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@x")
    monkeypatch.setenv("TELEGRAM_TEST_CHANNEL_ID", "@x")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_abcdefghijklmnop")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_settings_loads_new_loop_fields(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "0123456789abcdef")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@my_channel")
    monkeypatch.setenv("TELEGRAM_TEST_CHANNEL_ID", "@test_channel")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_0123456789abcdef")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-abc")
    monkeypatch.setenv("STATE_DIR", str(tmp_path))
    monkeypatch.setenv("LOOP_CONFIG_PATH", "config/loop.toml")

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.telegram_channel_id == "@my_channel"
    assert s.anthropic_api_key == "sk-ant-abc"
    assert s.state_dir == tmp_path
    assert str(s.loop_config_path) == "config/loop.toml"


def test_settings_anthropic_key_optional_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "0123456789abcdef")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@x")
    monkeypatch.setenv("TELEGRAM_TEST_CHANNEL_ID", "@x")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_0123456789abcdef")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.anthropic_api_key is None
