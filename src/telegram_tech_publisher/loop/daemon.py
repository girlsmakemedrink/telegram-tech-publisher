"""APScheduler-driven daemon for the autonomous publishing loop."""

from __future__ import annotations

import asyncio
import signal
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from telegram_tech_publisher.loop.config import LoopConfig

log = structlog.get_logger(__name__)


async def _wait_for_shutdown() -> None:
    """Block until SIGTERM/SIGINT. Replaced in tests."""

    stop_event = asyncio.Event()

    def _handler(*_: object) -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handler)

    await stop_event.wait()


async def run_daemon(
    *,
    loop_cfg: LoopConfig,
    channel_id: str,
    tick_callable: Callable[[], Awaitable[object]],
) -> None:
    """Boot APScheduler with cron triggers from loop_cfg.schedule. Block until signal."""

    tz = ZoneInfo(loop_cfg.timezone)
    scheduler = AsyncIOScheduler(timezone=tz)

    for entry in loop_cfg.schedule:
        hour, minute = entry.split(":")
        scheduler.add_job(
            tick_callable,
            CronTrigger(hour=int(hour), minute=int(minute), timezone=tz),
            id=f"tick-{entry}",
            misfire_grace_time=300,
            coalesce=True,
            max_instances=1,
            replace_existing=True,
        )
        log.info("daemon.trigger_registered", time=entry, tz=loop_cfg.timezone)

    scheduler.start()
    log.info("daemon.started", channel_id=channel_id, tick_count=len(loop_cfg.schedule))
    try:
        await _wait_for_shutdown()
    finally:
        log.info("daemon.shutting_down")
        scheduler.shutdown(wait=True)
        log.info("daemon.shutdown_complete")
