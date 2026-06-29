from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, json_dict, uuid_pk


class CompanyBillingPlan(TimestampMixin, Base):
    __tablename__ = "company_billing_plans"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    plan_key: Mapped[str] = mapped_column(String(40), default="free", nullable=False)
    billing_status: Mapped[str] = mapped_column(String(40), default="free", nullable=False)
    trial_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seat_limit: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    storage_limit_mb: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    work_object_limit: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    project_limit: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    employee_limit: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    notification_limit: Mapped[int | None] = mapped_column(Integer)
    file_upload_limit_mb: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json = json_dict(name="metadata")

    company = relationship("Company")

    __table_args__ = (
        Index("idx_company_billing_company_id", "company_id"),
        Index("idx_company_billing_plan_key", "plan_key"),
        Index("idx_company_billing_status", "billing_status"),
        Index("idx_company_billing_active", "company_id", "is_active"),
    )
