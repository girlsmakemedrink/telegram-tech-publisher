"""Tests for the loop's Drafter adapter."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from telegram_tech_publisher.llm.client import Draft, Example
from telegram_tech_publisher.llm.mock import MockLLMDrafterClient
from telegram_tech_publisher.llm.voice import Voice
from telegram_tech_publisher.loop.drafter import Drafter
from telegram_tech_publisher.sources.base import Candidate


def _candidate() -> Candidate:
    return Candidate(
        source="github_releases",
        external_id="42",
        title="httpx 0.28",
        body="HTTP/3 support",
        url="https://github.com/encode/httpx/releases/tag/0.28.0",
        published_at=datetime(2026, 5, 23, tzinfo=UTC),
    )


def _voice() -> Voice:
    return Voice(
        voice_block="Voice: terse, code-literate.",
        examples=[
            Example(input_title="t1", input_body="b1", output_text="o1"),
            Example(input_title="t2", input_body="b2", output_text="o2"),
        ],
    )


@pytest.mark.asyncio
async def test_drafter_passes_voice_block_and_examples_to_client() -> None:
    received: dict[str, object] = {}

    class CapturingClient:
        async def draft(self, voice_block, examples, candidate):
            received["voice_block"] = voice_block
            received["examples"] = examples
            received["candidate"] = candidate
            return Draft(
                text="ok", model="m", input_tokens=1, output_tokens=2, cache_read_tokens=3
            )

    drafter = Drafter(client=CapturingClient(), voice=_voice())
    draft = await drafter.draft(_candidate())

    assert draft.text == "ok"
    assert received["voice_block"] == "Voice: terse, code-literate."
    assert len(received["examples"]) == 2
    assert received["candidate"].external_id == "42"


@pytest.mark.asyncio
async def test_drafter_with_mock_client_returns_shape() -> None:
    drafter = Drafter(client=MockLLMDrafterClient(), voice=_voice())
    draft = await drafter.draft(_candidate())
    assert "httpx 0.28" in draft.text
    assert draft.model == "mock"
