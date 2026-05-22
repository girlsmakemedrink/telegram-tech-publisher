"""Alembic env.py — async mode, target_metadata = Base.metadata."""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from telegram_tech_publisher.db.models import Base

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic's ConfigParser does not interpolate ${VAR} from the process
# env. Read DATABASE_URL here and override the ini value so the runtime
# engine and `alembic upgrade head` see the same DSN.
_database_url = os.environ.get("DATABASE_URL")
if _database_url:
    config.set_main_option("sqlalchemy.url", _database_url)

target_metadata = Base.metadata


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
