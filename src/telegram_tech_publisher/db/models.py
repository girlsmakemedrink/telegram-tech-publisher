"""SQLAlchemy 2.0 typed models for the product runtime."""

from __future__ import annotations

import uuid
from datetime import datetime  # noqa: TC003  # SQLAlchemy needs runtime symbol for Mapped[datetime]
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    voice_store: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    labeled_count: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
