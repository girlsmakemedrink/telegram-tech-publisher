"""Smoke tests for the new Click sub-commands via CliRunner."""

from __future__ import annotations

from typing import TYPE_CHECKING

from click.testing import CliRunner

from telegram_tech_publisher.cli import cli
from telegram_tech_publisher.loop.state import StateStore

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


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


def test_daemon_command_registers_triggers_and_exits_on_signal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_env(monkeypatch, tmp_path)
    voice_dir = tmp_path / "voice"
    voice_dir.mkdir()
    (voice_dir / "devops.md").write_text(
        "---\ntone\n---\n---\ninput_title: t\ninput_body: b\noutput_text: o\n"
    )
    monkeypatch.setattr("telegram_tech_publisher.loop.config.VOICE_DIR", voice_dir)
    monkeypatch.setattr("telegram_tech_publisher.cli.VOICE_DIR", voice_dir)

    (tmp_path / "loop.toml").write_text(
        "\n".join(
            [
                'voice = "devops"',
                'timezone = "UTC"',
                'schedule = ["09:30"]',
                "[[sources.github_repos]]",
                'repo = "a/x"',
            ]
        )
    )

    triggers_registered: list[str] = []

    class _FakeScheduler:
        def __init__(self, *_, **__):
            pass

        def add_job(self, fn, trigger, **kw):
            triggers_registered.append(f"{trigger}:{kw}")

        def start(self) -> None:
            pass

        def shutdown(self, **__) -> None:
            pass

    monkeypatch.setattr("telegram_tech_publisher.loop.daemon.AsyncIOScheduler", _FakeScheduler)

    async def _no_wait() -> None:
        return None

    monkeypatch.setattr(
        "telegram_tech_publisher.loop.daemon._wait_for_shutdown",
        _no_wait,
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["daemon"])
    assert result.exit_code == 0, result.output
    assert triggers_registered, "daemon did not register any cron triggers"
    assert any("tick-09:30" in t for t in triggers_registered)


def test_status_shows_recent_post(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
