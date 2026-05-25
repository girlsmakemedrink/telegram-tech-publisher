"""Tests for the SQLite-backed StateStore."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from telegram_tech_publisher.loop.state import StateStore

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def store(tmp_path: Path) -> StateStore:
    return StateStore(tmp_path / "state.db")


def test_is_published_false_for_unknown(store: StateStore) -> None:
    assert store.is_published("github_releases", "no-such-id") is False


def test_mark_then_is_published_true(store: StateStore) -> None:
    store.mark_published(
        source="github_releases",
        external_id="ext-1",
        candidate_title="t",
        candidate_url="https://x",
        channel_id="@c",
        message_id=42,
        model="m",
        input_tokens=1,
        output_tokens=2,
        cache_read_tokens=3,
    )
    assert store.is_published("github_releases", "ext-1") is True


def test_mark_twice_same_external_id_raises(store: StateStore) -> None:
    common = {
        "source": "github_releases",
        "external_id": "ext-dup",
        "candidate_title": "t",
        "candidate_url": "https://x",
        "channel_id": "@c",
        "message_id": 42,
        "model": "m",
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
    }
    store.mark_published(**common)
    with pytest.raises(Exception) as excinfo:
        store.mark_published(**common)
    assert "UNIQUE" in str(excinfo.value).upper()


def test_recent_posts_orders_newest_first(store: StateStore) -> None:
    for i in range(5):
        store.mark_published(
            source="github_releases",
            external_id=f"ext-{i}",
            candidate_title=f"title-{i}",
            candidate_url=f"https://x/{i}",
            channel_id="@c",
            message_id=i,
            model="m",
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=0,
        )
    rows = store.recent_posts(limit=3)
    assert [r.external_id for r in rows] == ["ext-4", "ext-3", "ext-2"]


def test_failed_ticks_filters_by_since(store: StateStore) -> None:
    now = datetime.now(UTC)
    old = now - timedelta(days=2)
    recent = now - timedelta(minutes=5)

    store.record_tick_run(started_at=old, finished_at=old, outcome="failed", error="old")
    store.record_tick_run(started_at=recent, finished_at=recent, outcome="failed", error="recent")
    store.record_tick_run(started_at=recent, finished_at=recent, outcome="published")

    rows = store.failed_ticks(since=now - timedelta(hours=1))
    assert len(rows) == 1
    assert rows[0].error == "recent"
