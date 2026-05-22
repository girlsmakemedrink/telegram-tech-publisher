"""CLI smoke commands: verify Click plumbing wires Settings → Source/Publisher."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from telegram_tech_publisher.cli import cli
from telegram_tech_publisher.sources.base import Candidate


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abcdefghijklmnop")
    monkeypatch.setenv("TELEGRAM_TEST_CHANNEL_ID", "@my_test_channel")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_abcdefghijklmnop")


def test_smoke_github_lists_candidates(env: None) -> None:
    fake_candidate = Candidate(
        source="github_releases",
        external_id="42",
        title="v0.1.0",
        body="",
        url="https://github.com/foo/bar/releases/tag/v0.1.0",
        published_at=datetime(2026, 5, 22, tzinfo=UTC),
    )

    with (
        patch("telegram_tech_publisher.cli.GitHubReleasesSource") as source_cls,
        patch("telegram_tech_publisher.cli.Settings", autospec=False),
    ):
        source_cls.return_value.poll = AsyncMock(return_value=[fake_candidate])
        result = CliRunner().invoke(cli, ["smoke-github", "--repo", "foo/bar"])

    assert result.exit_code == 0, result.output
    assert "1 candidates from foo/bar" in result.output
    assert "v0.1.0" in result.output


def test_smoke_telegram_sends_hardcoded_message(env: None) -> None:
    fake_publisher = MagicMock()
    fake_publisher.send = AsyncMock(return_value=4242)

    with (
        patch("telegram_tech_publisher.cli.TelegramPublisher", return_value=fake_publisher),
        patch("telegram_tech_publisher.cli.Bot"),
        patch("telegram_tech_publisher.cli.Settings", autospec=False),
    ):
        result = CliRunner().invoke(cli, ["smoke-telegram"])

    assert result.exit_code == 0, result.output
    assert "4242" in result.output
    fake_publisher.send.assert_awaited_once_with("iter-27 smoke from telegram-tech-publisher")
