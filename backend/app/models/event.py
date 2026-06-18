from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import json_dict, utc_now, uuid_pk


class Event(Base):
    __tablename__ = "events"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
    )
    target_entity_type: Mapped[str | None] = mapped_column(String(80))
    target_entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    metadata_json = json_dict(name="metadata")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    company = relationship("Company", back_populates="events")
    actor = relationship("Employee")

    __table_args__ = (
        Index("idx_events_company_id_created_at", "company_id", "created_at"),
        Index("idx_events_target", "target_entity_type", "target_entity_id"),
        Index("idx_events_actor_employee_id", "actor_employee_id"),
    )
