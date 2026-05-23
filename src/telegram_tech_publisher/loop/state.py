"""SQLite-backed state store for the autonomous publishing loop."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

_SCHEMA = """
CREATE TABLE IF NOT EXISTS published (
  id            INTEGER PRIMARY KEY,
  source        TEXT NOT NULL,
  external_id   TEXT NOT NULL,
  candidate_title TEXT NOT NULL,
  candidate_url   TEXT NOT NULL,
  channel_id    TEXT NOT NULL,
  message_id    INTEGER NOT NULL,
  model         TEXT NOT NULL,
  input_tokens  INTEGER NOT NULL DEFAULT 0,
  output_tokens INTEGER NOT NULL DEFAULT 0,
  cache_read_tokens INTEGER NOT NULL DEFAULT 0,
  published_at  TEXT NOT NULL,
  UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS tick_runs (
  id            INTEGER PRIMARY KEY,
  started_at    TEXT NOT NULL,
  finished_at   TEXT,
  outcome       TEXT NOT NULL CHECK (outcome IN ('published','noop','failed')),
  candidate_external_id TEXT,
  error         TEXT
);
"""


@dataclass(frozen=True)
class PublishedRow:
    source: str
    external_id: str
    candidate_title: str
    candidate_url: str
    channel_id: str
    message_id: int
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    published_at: datetime


@dataclass(frozen=True)
class TickRunRow:
    started_at: datetime
    finished_at: datetime | None
    outcome: str
    candidate_external_id: str | None
    error: str | None


class StateStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self._db_path, isolation_level=None)
        try:
            yield conn
        finally:
            conn.close()

    def is_published(self, source: str, external_id: str) -> bool:
        with self._conn() as conn:
            cur = conn.execute(
                "SELECT 1 FROM published WHERE source = ? AND external_id = ?",
                (source, external_id),
            )
            return cur.fetchone() is not None

    def mark_published(
        self,
        *,
        source: str,
        external_id: str,
        candidate_title: str,
        candidate_url: str,
        channel_id: str,
        message_id: int,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO published
                   (source, external_id, candidate_title, candidate_url, channel_id,
                    message_id, model, input_tokens, output_tokens, cache_read_tokens,
                    published_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    source,
                    external_id,
                    candidate_title,
                    candidate_url,
                    channel_id,
                    message_id,
                    model,
                    input_tokens,
                    output_tokens,
                    cache_read_tokens,
                    datetime.now(UTC).isoformat(),
                ),
            )

    def record_tick_run(
        self,
        *,
        started_at: datetime,
        finished_at: datetime | None,
        outcome: str,
        candidate_external_id: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO tick_runs
                   (started_at, finished_at, outcome, candidate_external_id, error)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    started_at.isoformat(),
                    finished_at.isoformat() if finished_at else None,
                    outcome,
                    candidate_external_id,
                    error,
                ),
            )

    def recent_posts(self, limit: int = 10) -> list[PublishedRow]:
        with self._conn() as conn:
            cur = conn.execute(
                """SELECT source, external_id, candidate_title, candidate_url, channel_id,
                          message_id, model, input_tokens, output_tokens, cache_read_tokens,
                          published_at
                   FROM published
                   ORDER BY id DESC
                   LIMIT ?""",
                (limit,),
            )
            return [
                PublishedRow(
                    source=row[0],
                    external_id=row[1],
                    candidate_title=row[2],
                    candidate_url=row[3],
                    channel_id=row[4],
                    message_id=row[5],
                    model=row[6],
                    input_tokens=row[7],
                    output_tokens=row[8],
                    cache_read_tokens=row[9],
                    published_at=datetime.fromisoformat(row[10]),
                )
                for row in cur.fetchall()
            ]

    def failed_ticks(self, since: datetime) -> list[TickRunRow]:
        with self._conn() as conn:
            cur = conn.execute(
                """SELECT started_at, finished_at, outcome, candidate_external_id, error
                   FROM tick_runs
                   WHERE outcome = 'failed' AND started_at >= ?
                   ORDER BY started_at DESC""",
                (since.isoformat(),),
            )
            return [
                TickRunRow(
                    started_at=datetime.fromisoformat(row[0]),
                    finished_at=datetime.fromisoformat(row[1]) if row[1] else None,
                    outcome=row[2],
                    candidate_external_id=row[3],
                    error=row[4],
                )
                for row in cur.fetchall()
            ]
