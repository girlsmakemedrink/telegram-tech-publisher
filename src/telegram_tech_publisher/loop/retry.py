"""Async exponential-backoff retry engine. Policy is caller-supplied via predicates."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

log = logging.getLogger(__name__)

T = TypeVar("T")


class RetryError(Exception):
    def __init__(self, attempts: int, last_error: BaseException) -> None:
        super().__init__(f"all {attempts} retry attempts failed: {last_error!r}")
        self.attempts = attempts
        self.last_error = last_error


def _no_override(_: BaseException) -> float | None:
    return None


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    is_retryable: Callable[[BaseException], bool],
    retry_after: Callable[[BaseException], float | None] = _no_override,
    max_attempts: int = 3,
    base_delay: float = 2.0,
    op_name: str = "call",
) -> T:
    last_exc: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except BaseException as exc:
            if not is_retryable(exc):
                raise
            last_exc = exc
            override = retry_after(exc)
            delay = override if override is not None else base_delay * (2 ** (attempt - 1))
            log.warning(
                "retry",
                extra={
                    "op": op_name,
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "delay": delay,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            if attempt >= max_attempts:
                break
            await asyncio.sleep(delay)
    assert last_exc is not None
    raise RetryError(attempts=max_attempts, last_error=last_exc)
