"""Tests for ClaudeCodeLLMDrafterClient."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from telegram_tech_publisher.llm.claude_code import (
    ClaudeCodeError,
    ClaudeCodeLLMDrafterClient,
)
from telegram_tech_publisher.llm.client import Example
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


def _examples() -> list[Example]:
    return [
        Example(input_title="t1", input_body="b1", output_text="o1"),
        Example(input_title="t2", input_body="b2", output_text="o2"),
    ]


@pytest.mark.asyncio
async def test_draft_returns_stdout_stripped() -> None:
    captured: dict[str, object] = {}

    async def runner(argv, stdin_text, timeout):
        captured["argv"] = argv
        captured["stdin"] = stdin_text
        captured["timeout"] = timeout
        return 0, "  drafted output\n", ""

    client = ClaudeCodeLLMDrafterClient(runner=runner)
    draft = await client.draft("Voice: terse.", _examples(), _candidate())

    assert draft.text == "drafted output"
    assert draft.model == "claude-code-cli"
    assert draft.input_tokens == 0
    assert draft.output_tokens == 0
    assert draft.cache_read_tokens == 0
    assert captured["argv"] == ["claude", "-p"]
    assert "Voice: terse." in captured["stdin"]
    assert "httpx 0.28" in captured["stdin"]
    assert "Past post 1" in captured["stdin"]
    assert "Past post 2" in captured["stdin"]


@pytest.mark.asyncio
async def test_nonzero_exit_raises() -> None:
    async def runner(argv, stdin_text, timeout):
        return 1, "", "boom"

    client = ClaudeCodeLLMDrafterClient(runner=runner)
    with pytest.raises(ClaudeCodeError) as excinfo:
        await client.draft("v", _examples(), _candidate())
    assert "boom" in str(excinfo.value)


@pytest.mark.asyncio
async def test_empty_stdout_raises() -> None:
    async def runner(argv, stdin_text, timeout):
        return 0, "   \n", ""

    client = ClaudeCodeLLMDrafterClient(runner=runner)
    with pytest.raises(ClaudeCodeError):
        await client.draft("v", _examples(), _candidate())


@pytest.mark.asyncio
async def test_extra_args_and_binary_are_forwarded() -> None:
    captured: dict[str, object] = {}

    async def runner(argv, stdin_text, timeout):
        captured["argv"] = argv
        return 0, "ok", ""

    client = ClaudeCodeLLMDrafterClient(
        binary="/usr/local/bin/claude",
        extra_args=["--model", "sonnet"],
        runner=runner,
    )
    await client.draft("v", _examples(), _candidate())
    assert captured["argv"] == ["/usr/local/bin/claude", "-p", "--model", "sonnet"]
