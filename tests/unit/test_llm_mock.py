"""Tests for the deterministic MockLLMDrafterClient."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import HttpUrl

from telegram_tech_publisher.llm import (
    Draft,
    Example,
    LLMDrafterClient,
    MockLLMDrafterClient,
)
from telegram_tech_publisher.sources.base import Candidate


def _candidate(title: str = "PEP 999 lands") -> Candidate:
    return Candidate(
        source="github",
        external_id="abc-123",
        title=title,
        body="Body text.",
        url=HttpUrl("https://example.com/post"),
        published_at=datetime(2026, 5, 22, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_mock_returns_deterministic_draft_with_default_zero_counts() -> None:
    client = MockLLMDrafterClient()
    draft = await client.draft(
        voice_block="terse engineering voice",
        examples=[],
        candidate=_candidate(),
    )
    assert isinstance(draft, Draft)
    assert "PEP 999 lands" in draft.text
    assert "voice_len=23" in draft.text
    assert "n_examples=0" in draft.text
    assert draft.model == "mock"
    assert draft.input_tokens == 0
    assert draft.output_tokens == 0
    assert draft.cache_read_tokens == 0


@pytest.mark.asyncio
async def test_mock_surfaces_injected_token_counts() -> None:
    client = MockLLMDrafterClient(
        model="mock-pro", input_tokens=12, output_tokens=34, cache_read_tokens=8
    )
    draft = await client.draft(
        voice_block="",
        examples=[
            Example(input_title="t", input_body="b", output_text="o"),
            Example(input_title="t2", input_body="b2", output_text="o2"),
        ],
        candidate=_candidate("Title"),
    )
    assert draft.model == "mock-pro"
    assert draft.input_tokens == 12
    assert draft.output_tokens == 34
    assert draft.cache_read_tokens == 8
    assert "n_examples=2" in draft.text


def test_mock_conforms_to_protocol_statically() -> None:
    client: LLMDrafterClient = MockLLMDrafterClient()
    assert callable(client.draft)
