from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, uuid_pk


class NotificationPreference(TimestampMixin, Base):
    __tablename__ = "notification_preferences"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
    )
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mentions_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    assignments_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    leave_decisions_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    project_updates_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    announcements_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    company = relationship("Company")
    user = relationship("User")
    employee = relationship("Employee")

    __table_args__ = (
        UniqueConstraint("company_id", "user_id", name="uq_notification_preferences_company_user"),
        UniqueConstraint("company_id", "employee_id", name="uq_notification_preferences_company_employee"),
        Index("idx_notification_preferences_company_id", "company_id"),
        Index("idx_notification_preferences_user_id", "user_id"),
        Index("idx_notification_preferences_employee_id", "employee_id"),
    )
