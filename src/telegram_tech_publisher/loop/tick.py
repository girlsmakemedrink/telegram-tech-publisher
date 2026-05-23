"""One tick of the autonomous publishing loop.

Lifecycle:
  1. poll          source.poll() -> candidates                  (retry: github transient)
  2. filter unseen state.is_published(source, external_id)
  3. pick one      sort by published_at desc, take [0]
  4. draft         drafter.draft(candidate) -> Draft            (retry: anthropic transient)
  4a. length-gate  reject if len(draft.text) > 4096
  5. publish       publisher.send(draft.text) -> msg_id         (retry: telegram transient, honors Retry-After)
  6. record        state.mark_published(...)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Protocol

import anthropic
import httpx
import structlog
import telegram.error

from telegram_tech_publisher.llm.client import Draft
from telegram_tech_publisher.loop.retry import with_retry
from telegram_tech_publisher.loop.state import StateStore
from telegram_tech_publisher.sources.base import Candidate

log = structlog.get_logger(__name__)

TELEGRAM_MAX_TEXT = 4096
_TRANSIENT_HTTP_STATUS = frozenset({429, 500, 502, 503, 504})


def _github_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in _TRANSIENT_HTTP_STATUS
    return False


def _anthropic_retryable(exc: BaseException) -> bool:
    return isinstance(
        exc,
        (
            anthropic.APIConnectionError,
            anthropic.APITimeoutError,
            anthropic.RateLimitError,
            anthropic.InternalServerError,
        ),
    )


def _telegram_retryable(exc: BaseException) -> bool:
    return isinstance(
        exc,
        (
            telegram.error.RetryAfter,
            telegram.error.TimedOut,
            telegram.error.NetworkError,
        ),
    )


def _telegram_retry_after(exc: BaseException) -> float | None:
    if isinstance(exc, telegram.error.RetryAfter):
        return float(exc.retry_after)
    return None


class _SourceProto(Protocol):
    async def poll(self) -> list[Candidate]: ...


class _DrafterProto(Protocol):
    async def draft(self, candidate: Candidate) -> Draft: ...


class _PublisherProto(Protocol):
    async def send(self, text: str) -> int: ...


class TickOutcome(str, Enum):
    PUBLISHED = "published"
    NOOP = "noop"
    FAILED = "failed"


@dataclass(frozen=True)
class TickResult:
    outcome: TickOutcome
    candidate_external_id: str | None
    message_id: int | None
    drafted_text: str | None
    error: str | None


async def tick(
    *,
    source: _SourceProto,
    state: StateStore,
    drafter: _DrafterProto,
    publisher: _PublisherProto,
    channel_id: str,
    dry_run: bool = False,
) -> TickResult:
    started = datetime.now(UTC)
    log.info("tick.start", scheduled_at=started.isoformat(), dry_run=dry_run)

    try:
        candidates = await with_retry(
            source.poll, is_retryable=_github_retryable, op_name="poll"
        )
    except Exception as exc:
        err = f"poll failed: {exc!r}"
        log.error("tick.poll_failed", error=err)
        state.record_tick_run(
            started_at=started,
            finished_at=datetime.now(UTC),
            outcome="failed",
            error=err,
        )
        return TickResult(TickOutcome.FAILED, None, None, None, err)

    unseen = [c for c in candidates if not state.is_published(c.source, c.external_id)]
    log.info(
        "tick.poll_complete",
        candidates_total=len(candidates),
        candidates_unseen=len(unseen),
    )

    if not unseen:
        state.record_tick_run(
            started_at=started, finished_at=datetime.now(UTC), outcome="noop"
        )
        log.info("tick.noop")
        return TickResult(TickOutcome.NOOP, None, None, None, None)

    chosen = sorted(unseen, key=lambda c: c.published_at, reverse=True)[0]
    log.info(
        "tick.chosen",
        source=chosen.source,
        external_id=chosen.external_id,
        title=chosen.title,
    )

    try:
        draft = await with_retry(
            lambda: drafter.draft(chosen),
            is_retryable=_anthropic_retryable,
            op_name="draft",
        )
    except Exception as exc:
        err = f"draft failed: {exc!r}"
        log.error("tick.draft_failed", external_id=chosen.external_id, error=err)
        state.record_tick_run(
            started_at=started,
            finished_at=datetime.now(UTC),
            outcome="failed",
            candidate_external_id=chosen.external_id,
            error=err,
        )
        return TickResult(TickOutcome.FAILED, chosen.external_id, None, None, err)

    if len(draft.text) > TELEGRAM_MAX_TEXT:
        err = f"draft text too long: {len(draft.text)} > {TELEGRAM_MAX_TEXT}"
        log.error(
            "tick.skipped_too_long",
            external_id=chosen.external_id,
            length=len(draft.text),
        )
        state.record_tick_run(
            started_at=started,
            finished_at=datetime.now(UTC),
            outcome="failed",
            candidate_external_id=chosen.external_id,
            error=err,
        )
        return TickResult(
            TickOutcome.FAILED, chosen.external_id, None, draft.text, err
        )

    if dry_run:
        log.info(
            "tick.dry_run", external_id=chosen.external_id, length=len(draft.text)
        )
        state.record_tick_run(
            started_at=started,
            finished_at=datetime.now(UTC),
            outcome="noop",
            candidate_external_id=chosen.external_id,
        )
        return TickResult(
            TickOutcome.PUBLISHED, chosen.external_id, None, draft.text, None
        )

    try:
        message_id = await with_retry(
            lambda: publisher.send(draft.text),
            is_retryable=_telegram_retryable,
            retry_after=_telegram_retry_after,
            op_name="publish",
        )
    except Exception as exc:
        err = f"publish failed: {exc!r}"
        log.error("tick.publish_failed", external_id=chosen.external_id, error=err)
        state.record_tick_run(
            started_at=started,
            finished_at=datetime.now(UTC),
            outcome="failed",
            candidate_external_id=chosen.external_id,
            error=err,
        )
        return TickResult(
            TickOutcome.FAILED, chosen.external_id, None, draft.text, err
        )

    try:
        state.mark_published(
            source=chosen.source,
            external_id=chosen.external_id,
            candidate_title=chosen.title,
            candidate_url=str(chosen.url),
            channel_id=channel_id,
            message_id=message_id,
            model=draft.model,
            input_tokens=draft.input_tokens,
            output_tokens=draft.output_tokens,
            cache_read_tokens=draft.cache_read_tokens,
        )
    except Exception as exc:
        log.critical(
            "tick.state_write_failed",
            external_id=chosen.external_id,
            message_id=message_id,
            channel_id=channel_id,
            error=repr(exc),
        )

    state.record_tick_run(
        started_at=started,
        finished_at=datetime.now(UTC),
        outcome="published",
        candidate_external_id=chosen.external_id,
    )
    log.info(
        "tick.published",
        external_id=chosen.external_id,
        message_id=message_id,
        input_tokens=draft.input_tokens,
        output_tokens=draft.output_tokens,
        cache_read_tokens=draft.cache_read_tokens,
    )
    return TickResult(
        TickOutcome.PUBLISHED, chosen.external_id, message_id, draft.text, None
    )
