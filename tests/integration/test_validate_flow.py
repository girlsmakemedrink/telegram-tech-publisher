"""Integration: full validate command flow with HTTP mocked at the edge."""

from __future__ import annotations

import traceback
from pathlib import Path

import pytest
import respx
from click.testing import CliRunner

from telegram_tech_publisher.cli import cli
from telegram_tech_publisher.loop.state import StateStore


@respx.mock
def test_validate_publishes_one_post_end_to_end(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    voice_dir = tmp_path / "voice"
    voice_dir.mkdir()
    (voice_dir / "devops.md").write_text(
        "---\nVoice: terse.\n---\n---\ninput_title: t\ninput_body: b\noutput_text: o\n"
    )
    monkeypatch.setattr("telegram_tech_publisher.loop.config.VOICE_DIR", voice_dir)
    monkeypatch.setattr("telegram_tech_publisher.cli.VOICE_DIR", voice_dir)

    loop_toml = tmp_path / "loop.toml"
    loop_toml.write_text(
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

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "0123456789abcdef")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "-1001234567890")
    monkeypatch.setenv("TELEGRAM_TEST_CHANNEL_ID", "-1001234567890")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_0123456789abcdef")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("STATE_DIR", str(tmp_path))
    monkeypatch.setenv("LOOP_CONFIG_PATH", str(loop_toml))

    respx.get("https://api.github.com/repos/a/x/releases").respond(
        200,
        json=[
            {
                "id": 777,
                "name": "release seven-seven-seven",
                "tag_name": "v7.7.7",
                "body": "great release",
                "html_url": "https://github.com/a/x/releases/tag/v7.7.7",
                "published_at": "2026-05-23T10:00:00Z",
            }
        ],
    )

    respx.post("https://api.anthropic.com/v1/messages").respond(
        200,
        json={
            "id": "msg_test",
            "type": "message",
            "role": "assistant",
            "model": "claude-sonnet-4-6",
            "content": [{"type": "text", "text": "drafted post about release"}],
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 30,
                "cache_read_input_tokens": 50,
            },
        },
    )

    respx.post(
        "https://api.telegram.org/bot0123456789abcdef/sendMessage"
    ).respond(
        200,
        json={
            "ok": True,
            "result": {
                "message_id": 42,
                "chat": {"id": -1001234567890, "type": "channel"},
                "date": 1700000000,
                "text": "drafted post about release",
            },
        },
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["validate"])

    if result.exit_code != 0:
        print(result.output)
        if result.exception:
            traceback.print_exception(
                type(result.exception), result.exception, result.exception.__traceback__
            )
    assert result.exit_code == 0
    assert "42" in result.output

    state = StateStore(tmp_path / "state.db")
    posts = state.recent_posts(limit=10)
    assert len(posts) == 1
    assert posts[0].message_id == 42
    assert posts[0].external_id == "777"
