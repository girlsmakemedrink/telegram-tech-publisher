"""Tests for LoopConfig (TOML loader + validator)."""

from __future__ import annotations

from textwrap import dedent
from typing import TYPE_CHECKING

import pytest

from telegram_tech_publisher.loop.config import LoopConfig, LoopConfigError

if TYPE_CHECKING:
    from pathlib import Path


def _write_toml(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "loop.toml"
    p.write_text(dedent(body).lstrip())
    return p


def test_loads_valid_toml(tmp_path: Path, monkeypatch) -> None:
    voice_dir = tmp_path / "voice"
    voice_dir.mkdir()
    (voice_dir / "devops.md").write_text("---\ntone\n---\n---\nexamples\n---\n")

    monkeypatch.setattr("telegram_tech_publisher.loop.config.VOICE_DIR", voice_dir)

    p = _write_toml(
        tmp_path,
        """
        voice = "devops"
        timezone = "Europe/Moscow"
        schedule = ["09:30", "13:30", "18:00"]

        [[sources.github_repos]]
        repo = "a/x"

        [[sources.github_repos]]
        repo = "b/y"
        """,
    )

    cfg = LoopConfig.load(p)
    assert cfg.voice == "devops"
    assert cfg.timezone == "Europe/Moscow"
    assert cfg.schedule == ["09:30", "13:30", "18:00"]
    assert cfg.github_repos == ["a/x", "b/y"]


def test_rejects_bad_schedule_format(tmp_path: Path, monkeypatch) -> None:
    voice_dir = tmp_path / "voice"
    voice_dir.mkdir()
    (voice_dir / "devops.md").write_text("x")
    monkeypatch.setattr("telegram_tech_publisher.loop.config.VOICE_DIR", voice_dir)

    p = _write_toml(
        tmp_path,
        """
        voice = "devops"
        timezone = "Europe/Moscow"
        schedule = ["9:30am"]

        [[sources.github_repos]]
        repo = "a/x"
        """,
    )
    with pytest.raises(LoopConfigError, match="schedule"):
        LoopConfig.load(p)


def test_rejects_missing_voice_file(tmp_path: Path, monkeypatch) -> None:
    voice_dir = tmp_path / "voice"
    voice_dir.mkdir()
    monkeypatch.setattr("telegram_tech_publisher.loop.config.VOICE_DIR", voice_dir)

    p = _write_toml(
        tmp_path,
        """
        voice = "nope"
        timezone = "Europe/Moscow"
        schedule = ["09:30"]

        [[sources.github_repos]]
        repo = "a/x"
        """,
    )
    with pytest.raises(LoopConfigError, match="voice"):
        LoopConfig.load(p)


def test_rejects_empty_repo_list(tmp_path: Path, monkeypatch) -> None:
    voice_dir = tmp_path / "voice"
    voice_dir.mkdir()
    (voice_dir / "devops.md").write_text("x")
    monkeypatch.setattr("telegram_tech_publisher.loop.config.VOICE_DIR", voice_dir)

    p = _write_toml(
        tmp_path,
        """
        voice = "devops"
        timezone = "Europe/Moscow"
        schedule = ["09:30"]
        """,
    )
    with pytest.raises(LoopConfigError, match="repo"):
        LoopConfig.load(p)


def test_rejects_malformed_repo(tmp_path: Path, monkeypatch) -> None:
    voice_dir = tmp_path / "voice"
    voice_dir.mkdir()
    (voice_dir / "devops.md").write_text("x")
    monkeypatch.setattr("telegram_tech_publisher.loop.config.VOICE_DIR", voice_dir)

    p = _write_toml(
        tmp_path,
        """
        voice = "devops"
        timezone = "Europe/Moscow"
        schedule = ["09:30"]

        [[sources.github_repos]]
        repo = "not-a-slash-pair"
        """,
    )
    with pytest.raises(LoopConfigError, match="owner/repo"):
        LoopConfig.load(p)
