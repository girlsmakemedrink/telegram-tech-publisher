"""Tests for the tick() orchestrator."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

from telegram_tech_publisher.llm.client import Draft
from telegram_tech_publisher.loop.state import StateStore
from telegram_tech_publisher.loop.tick import TickOutcome, tick
from telegram_tech_publisher.sources.base import Candidate

if TYPE_CHECKING:
    from pathlib import Path


class _FakeSource:
    def __init__(self, candidates: list[Candidate]) -> None:
        self._candidates = candidates

    async def poll(self) -> list[Candidate]:
        return list(self._candidates)


class _FakeDrafter:
    def __init__(self, text: str = "drafted text") -> None:
        self._text = text
        self.calls = 0

    async def draft(self, candidate: Candidate) -> Draft:
        self.calls += 1
        return Draft(
            text=self._text,
            model="claude-sonnet-4-6",
            input_tokens=10,
            output_tokens=20,
            cache_read_tokens=5,
        )


class _FakePublisher:
    def __init__(self, fail_with: Exception | None = None, msg_id: int = 99) -> None:
        self._fail_with = fail_with
        self._msg_id = msg_id
        self.calls = 0

    async def send(self, text: str) -> int:
        self.calls += 1
        if self._fail_with:
            raise self._fail_with
        return self._msg_id


def _candidate(ext_id: str, title: str = "t") -> Candidate:
    return Candidate(
        source="github_releases",
        external_id=ext_id,
        title=title,
        body="b",
        url=f"https://example.test/{ext_id}",
        published_at=datetime(2026, 5, 23, tzinfo=UTC),
    )


@pytest.fixture
def store(tmp_path: Path) -> StateStore:
    return StateStore(tmp_path / "state.db")


@pytest.mark.asyncio
async def test_publishes_first_unseen_candidate(store: StateStore) -> None:
    src = _FakeSource([_candidate("a"), _candidate("b")])
    drafter = _FakeDrafter()
    pub = _FakePublisher()

    result = await tick(source=src, state=store, drafter=drafter, publisher=pub, channel_id="@c")

    assert result.outcome is TickOutcome.PUBLISHED
    assert result.message_id == 99
    assert drafter.calls == 1
    assert pub.calls == 1
    assert store.is_published("github_releases", "a") or store.is_published("github_releases", "b")


@pytest.mark.asyncio
async def test_skips_already_published(store: StateStore) -> None:
    store.mark_published(
        source="github_releases",
        external_id="a",
        candidate_title="t",
        candidate_url="https://example.test/a",
        channel_id="@c",
        message_id=1,
        model="m",
        input_tokens=0,
        output_tokens=0,
        cache_read_tokens=0,
    )
    src = _FakeSource([_candidate("a")])
    drafter = _FakeDrafter()
    pub = _FakePublisher()

    result = await tick(source=src, state=store, drafter=drafter, publisher=pub, channel_id="@c")

    assert result.outcome is TickOutcome.NOOP
    assert drafter.calls == 0
    assert pub.calls == 0


@pytest.mark.asyncio
async def test_empty_poll_returns_noop(store: StateStore) -> None:
    src = _FakeSource([])
    drafter = _FakeDrafter()
    pub = _FakePublisher()

    result = await tick(source=src, state=store, drafter=drafter, publisher=pub, channel_id="@c")
    assert result.outcome is TickOutcome.NOOP


@pytest.mark.asyncio
async def test_text_too_long_marks_failed(store: StateStore) -> None:
    src = _FakeSource([_candidate("a")])
    drafter = _FakeDrafter(text="x" * 5000)
    pub = _FakePublisher()

    result = await tick(source=src, state=store, drafter=drafter, publisher=pub, channel_id="@c")
    assert result.outcome is TickOutcome.FAILED
    assert "too long" in (result.error or "").lower()
    assert pub.calls == 0
    assert store.is_published("github_releases", "a") is False


@pytest.mark.asyncio
async def test_publish_failure_does_not_mark_published(store: StateStore) -> None:
    src = _FakeSource([_candidate("a")])
    drafter = _FakeDrafter()
    pub = _FakePublisher(fail_with=RuntimeError("telegram boom"))

    result = await tick(source=src, state=store, drafter=drafter, publisher=pub, channel_id="@c")
    assert result.outcome is TickOutcome.FAILED
    assert store.is_published("github_releases", "a") is False


@pytest.mark.asyncio
async def test_dry_run_skips_publish_but_does_not_record(store: StateStore) -> None:
    src = _FakeSource([_candidate("a")])
    drafter = _FakeDrafter()
    pub = _FakePublisher()

    result = await tick(
        source=src,
        state=store,
        drafter=drafter,
        publisher=pub,
        channel_id="@c",
        dry_run=True,
    )
    assert result.outcome is TickOutcome.PUBLISHED  # means "would publish"
    assert result.message_id is None
    assert pub.calls == 0
    assert store.is_published("github_releases", "a") is False
