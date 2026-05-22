"""Tests for AnthropicLLMDrafterClient — constructor + _build_request shape only.

The actual SDK round-trip is not exercised here. First paid call lands in
29b's `real_llm` smoke.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import HttpUrl

from telegram_tech_publisher.llm import AnthropicLLMDrafterClient, Example
from telegram_tech_publisher.sources.base import Candidate


def _candidate() -> Candidate:
    return Candidate(
        source="github",
        external_id="abc-123",
        title="Hello",
        body="World",
        url=HttpUrl("https://example.com/post"),
        published_at=datetime(2026, 5, 22, tzinfo=UTC),
    )


def test_init_raises_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        AnthropicLLMDrafterClient()


def test_init_uses_env_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-env")
    client = AnthropicLLMDrafterClient()
    assert client.model == "claude-sonnet-4-6"
    assert client.max_tokens == 2048
    assert client.temperature == pytest.approx(0.7)


def test_init_explicit_kwarg_beats_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-env")
    client = AnthropicLLMDrafterClient(
        api_key="sk-explicit", model="claude-opus-4-6", max_tokens=1024, temperature=0.2
    )
    assert client.model == "claude-opus-4-6"
    assert client.max_tokens == 1024
    assert client.temperature == pytest.approx(0.2)


def test_build_request_shape_pins_ephemeral_cache_on_system_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    client = AnthropicLLMDrafterClient()
    request = client._build_request(
        voice_block="terse, technical",
        examples=[Example(input_title="t1", input_body="b1", output_text="o1")],
        candidate=_candidate(),
    )

    assert request["model"] == "claude-sonnet-4-6"
    assert request["max_tokens"] == 2048
    assert request["temperature"] == pytest.approx(0.7)

    assert isinstance(request["system"], list)
    assert len(request["system"]) == 1
    sys_block = request["system"][0]
    assert sys_block["type"] == "text"
    assert sys_block["text"] == "terse, technical"
    assert sys_block["cache_control"] == {"type": "ephemeral"}

    assert isinstance(request["messages"], list)
    assert len(request["messages"]) == 1
    assert request["messages"][0]["role"] == "user"
    user_content = request["messages"][0]["content"]
    assert "Past post 1:" in user_content
    assert "source title: t1" in user_content
    assert "published post: o1" in user_content
    assert "Draft a Telegram post for:" in user_content
    assert "title: Hello" in user_content


def test_build_request_with_no_examples(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    client = AnthropicLLMDrafterClient()
    request = client._build_request(
        voice_block="v",
        examples=[],
        candidate=_candidate(),
    )
    user_content = request["messages"][0]["content"]
    assert "Past post" not in user_content
    assert "Draft a Telegram post for:" in user_content
