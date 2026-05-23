"""Smoke tests for the new Click sub-commands via CliRunner."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from telegram_tech_publisher.cli import cli
from telegram_tech_publisher.loop.state import StateStore


def _set_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "0123456789abcdef")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@target")
    monkeypatch.setenv("TELEGRAM_TEST_CHANNEL_ID", "@test")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_0123456789abcdef")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("STATE_DIR", str(tmp_path))
    monkeypatch.setenv("LOOP_CONFIG_PATH", str(tmp_path / "loop.toml"))


def test_status_empty_store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _set_env(monkeypatch, tmp_path)
    StateStore(tmp_path / "state.db")  # init schema
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0, result.output
    assert "no posts" in result.output.lower() or "0" in result.output


def test_status_shows_recent_post(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_env(monkeypatch, tmp_path)
    store = StateStore(tmp_path / "state.db")
    store.mark_published(
        source="github_releases",
        external_id="42",
        candidate_title="httpx 0.28",
        candidate_url="https://x/r/42",
        channel_id="@target",
        message_id=7,
        model="claude-sonnet-4-6",
        input_tokens=10,
        output_tokens=20,
        cache_read_tokens=5,
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["status"])
    assert result.exit_code == 0, result.output
    assert "httpx 0.28" in result.output
    assert "7" in result.output
