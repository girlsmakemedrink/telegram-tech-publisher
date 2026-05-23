"""Verify _build_drafter_client picks the right backend per DRAFTER_BACKEND."""

from __future__ import annotations

from typing import TYPE_CHECKING

import click
import pytest

from telegram_tech_publisher.cli import _build_drafter_client
from telegram_tech_publisher.config import Settings
from telegram_tech_publisher.llm.anthropic_client import AnthropicLLMDrafterClient
from telegram_tech_publisher.llm.claude_code import ClaudeCodeLLMDrafterClient
from telegram_tech_publisher.llm.mock import MockLLMDrafterClient

if TYPE_CHECKING:
    from pathlib import Path


def _base_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "0123456789abcdef")
    monkeypatch.setenv("TELEGRAM_CHANNEL_ID", "@c")
    monkeypatch.setenv("TELEGRAM_TEST_CHANNEL_ID", "@t")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_0123456789abcdef")
    monkeypatch.setenv("STATE_DIR", str(tmp_path))
    monkeypatch.setenv("LOOP_CONFIG_PATH", str(tmp_path / "loop.toml"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)


def test_default_backend_is_claude_code(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _base_env(monkeypatch, tmp_path)
    settings = Settings()  # type: ignore[call-arg]
    client = _build_drafter_client(settings)
    assert isinstance(client, ClaudeCodeLLMDrafterClient)


def test_anthropic_backend_requires_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("DRAFTER_BACKEND", "anthropic")
    settings = Settings()  # type: ignore[call-arg]
    with pytest.raises(click.UsageError):
        _build_drafter_client(settings)


def test_anthropic_backend_with_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("DRAFTER_BACKEND", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    settings = Settings()  # type: ignore[call-arg]
    client = _build_drafter_client(settings)
    assert isinstance(client, AnthropicLLMDrafterClient)


def test_mock_backend(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _base_env(monkeypatch, tmp_path)
    monkeypatch.setenv("DRAFTER_BACKEND", "mock")
    settings = Settings()  # type: ignore[call-arg]
    client = _build_drafter_client(settings)
    assert isinstance(client, MockLLMDrafterClient)
