"""structlog configuration: JSON to ${STATE_DIR}/loop.log + stderr fallback."""

from __future__ import annotations

import logging
import logging.handlers
import sys
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from pathlib import Path


def configure_logging(state_dir: Path | None, level: str = "INFO") -> None:
    handlers: list[logging.Handler] = []
    if state_dir is not None:
        state_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            state_dir / "loop.log", maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        handlers.append(file_handler)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    handlers.append(console_handler)

    logging.basicConfig(level=level.upper(), handlers=handlers, force=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, level.upper())),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
