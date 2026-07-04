from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, json_dict, utc_now, uuid_pk


class AIJob(TimestampMixin, Base):
    __tablename__ = "ai_jobs"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    requested_by_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
    )
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="queued", nullable=False)
    priority: Mapped[str] = mapped_column(String(40), default="normal", nullable=False)
    input_entity_type: Mapped[str | None] = mapped_column(String(80))
    input_entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    input_payload = json_dict()
    output_payload = json_dict()
    error_message: Mapped[str | None] = mapped_column(Text)
    provider_key: Mapped[str] = mapped_column(String(80), default="mock", nullable=False)
    provider_mode: Mapped[str] = mapped_column(String(40), default="mock", nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=utc_now)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(120))
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(120))
    retryable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    cancelled_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    run_mode: Mapped[str] = mapped_column(String(40), default="manual", nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json = json_dict(name="metadata")

    # Legacy columns kept mapped for old rows/backward-compatible reads.
    related_entity_type: Mapped[str | None] = mapped_column(String(80))
    related_entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))

    requester = relationship("Employee", foreign_keys=[requested_by_employee_id])
    requested_by_user = relationship("User", foreign_keys=[requested_by_user_id])
    cancelled_by_user = relationship("User", foreign_keys=[cancelled_by_user_id])

    __table_args__ = (
        Index("idx_ai_jobs_company_status", "company_id", "status"),
        Index("idx_ai_jobs_company_job_type", "company_id", "job_type"),
        Index("idx_ai_jobs_company_next_attempt", "company_id", "status", "next_attempt_at"),
        Index("idx_ai_jobs_company_locked_at", "company_id", "locked_at"),
        Index("idx_ai_jobs_run_mode", "company_id", "run_mode"),
        Index("idx_ai_jobs_requested_by_user_id", "requested_by_user_id"),
        Index("idx_ai_jobs_created_at", "created_at"),
        Index("idx_ai_jobs_input_entity", "input_entity_type", "input_entity_id"),
        Index("idx_ai_jobs_related_entity", "related_entity_type", "related_entity_id"),
    )
