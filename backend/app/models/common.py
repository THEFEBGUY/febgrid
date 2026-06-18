from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def uuid_pk() -> Mapped[UUID]:
    return mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)


def json_dict(default: dict[str, Any] | None = None, name: str | None = None) -> Mapped[dict[str, Any]]:
    if name is not None:
        return mapped_column(name, JSONB, default=lambda: dict(default or {}), nullable=False)
    return mapped_column(JSONB, default=lambda: dict(default or {}), nullable=False)


def json_list() -> Mapped[list[str]]:
    return mapped_column(JSONB, default=list, nullable=False)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
