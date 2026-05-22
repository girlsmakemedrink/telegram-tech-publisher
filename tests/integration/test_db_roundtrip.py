"""DB roundtrip: insert a User, commit, requery, assert.

Marked `integration` — needs a Postgres running at `TEST_DATABASE_URL`
(default: `postgresql+asyncpg://localhost/telegram_tech_publisher`) with
the alembic migration applied.

Each test cleans up its own row at the end so the table can be reused
across runs. No testcontainers in 29a (deferred).
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (  # noqa: TC002  pytest_asyncio reads runtime types
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)

from telegram_tech_publisher.db import User, make_engine, make_session_factory

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

pytestmark = pytest.mark.integration

_DEFAULT_DSN = "postgresql+asyncpg://localhost/telegram_tech_publisher"


def _dsn() -> str:
    return os.environ.get("TEST_DATABASE_URL", _DEFAULT_DSN)


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    eng = make_engine(_dsn())
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return make_session_factory(engine)


@pytest.mark.asyncio
async def test_user_roundtrip(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    # > 2^31 to exercise BigInteger.
    telegram_id = 9_999_999_999_999
    async with session_factory() as session:
        user = User(telegram_user_id=telegram_id)
        session.add(user)
        await session.commit()
        user_id = user.id

        result = await session.execute(select(User).where(User.telegram_user_id == telegram_id))
        loaded = result.scalar_one()
        try:
            assert loaded.id == user_id
            assert loaded.telegram_user_id == telegram_id
            assert loaded.voice_store == {}
            assert loaded.labeled_count == 0
            assert loaded.created_at is not None
            assert loaded.updated_at is not None
        finally:
            await session.delete(loaded)
            await session.commit()
