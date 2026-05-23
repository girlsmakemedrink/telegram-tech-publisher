"""Tests for the generic async retry engine."""

from __future__ import annotations

import pytest

from telegram_tech_publisher.loop.retry import RetryError, with_retry


@pytest.mark.asyncio
async def test_returns_on_first_success() -> None:
    calls = {"n": 0}

    async def ok() -> str:
        calls["n"] += 1
        return "ok"

    result = await with_retry(ok, is_retryable=lambda _: True, op_name="ok")
    assert result == "ok"
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_retries_until_success(monkeypatch) -> None:
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("asyncio.sleep", fake_sleep)

    calls = {"n": 0}

    async def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("transient")
        return "ok"

    result = await with_retry(
        flaky,
        is_retryable=lambda e: isinstance(e, ValueError),
        max_attempts=3,
        base_delay=2.0,
        op_name="flaky",
    )
    assert result == "ok"
    assert calls["n"] == 3
    assert sleep_calls == [2.0, 4.0]


@pytest.mark.asyncio
async def test_no_retry_when_predicate_false() -> None:
    calls = {"n": 0}

    async def bad() -> None:
        calls["n"] += 1
        raise KeyError("nope")

    with pytest.raises(KeyError):
        await with_retry(bad, is_retryable=lambda _: False, op_name="bad")
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_raises_retry_error_after_exhausting(monkeypatch) -> None:
    async def fake_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("asyncio.sleep", fake_sleep)

    async def always_bad() -> None:
        raise ValueError("boom")

    with pytest.raises(RetryError) as excinfo:
        await with_retry(
            always_bad,
            is_retryable=lambda _: True,
            max_attempts=3,
            op_name="always_bad",
        )
    assert excinfo.value.attempts == 3
    assert isinstance(excinfo.value.last_error, ValueError)


@pytest.mark.asyncio
async def test_retry_after_override(monkeypatch) -> None:
    sleep_calls: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr("asyncio.sleep", fake_sleep)

    calls = {"n": 0}

    class RateLimit(Exception):
        retry_after = 7.5

    async def rl() -> str:
        calls["n"] += 1
        if calls["n"] < 2:
            raise RateLimit()
        return "ok"

    def retry_after(exc: BaseException) -> float | None:
        return exc.retry_after if isinstance(exc, RateLimit) else None

    result = await with_retry(
        rl,
        is_retryable=lambda e: isinstance(e, RateLimit),
        retry_after=retry_after,
        base_delay=2.0,
        op_name="rl",
    )
    assert result == "ok"
    assert sleep_calls == [7.5]
