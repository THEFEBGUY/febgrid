from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, json_dict, uuid_pk


class Notification(TimestampMixin, Base):
    __tablename__ = "notifications"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    recipient_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    recipient_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    actor_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
    )
    event_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="SET NULL"),
    )
    target_entity_type: Mapped[str | None] = mapped_column("related_entity_type", String(80))
    target_entity_id: Mapped[UUID | None] = mapped_column("related_entity_id", PG_UUID(as_uuid=True))
    notification_type: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)
    action_url: Mapped[str | None] = mapped_column(String(255))
    metadata_json = json_dict(name="metadata")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    recipient_user = relationship("User", foreign_keys=[recipient_user_id])
    recipient = relationship("Employee", foreign_keys=[recipient_employee_id])
    actor_user = relationship("User", foreign_keys=[actor_user_id])
    actor = relationship("Employee", foreign_keys=[actor_employee_id])
    event = relationship("Event")

    @property
    def related_entity_type(self) -> str | None:
        return self.target_entity_type

    @related_entity_type.setter
    def related_entity_type(self, value: str | None) -> None:
        self.target_entity_type = value

    @property
    def related_entity_id(self) -> UUID | None:
        return self.target_entity_id

    @related_entity_id.setter
    def related_entity_id(self, value: UUID | None) -> None:
        self.target_entity_id = value

    __table_args__ = (
        Index("idx_notifications_recipient", "recipient_employee_id", "is_read"),
        Index("idx_notifications_recipient_user", "recipient_user_id", "is_read"),
        Index("idx_notifications_company_id", "company_id"),
        Index("idx_notifications_company_dismissed", "company_id", "is_dismissed", "created_at"),
        Index("idx_notifications_target", "related_entity_type", "related_entity_id"),
        Index("idx_notifications_event_id", "event_id"),
    )
