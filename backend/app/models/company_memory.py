from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, json_dict, json_list, uuid_pk


class CompanyMemory(TimestampMixin, Base):
    __tablename__ = "company_memories"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(60), default="general_note", nullable=False)
    scope_type: Mapped[str] = mapped_column(String(60), default="company", nullable=False)
    scope_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    source_type: Mapped[str | None] = mapped_column(String(80))
    source_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    source_ai_job_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ai_jobs.id", ondelete="SET NULL"),
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    tags = json_list()
    importance: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    visibility: Mapped[str] = mapped_column(String(40), default="owner_admin", nullable=False)
    created_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    created_by_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
    )
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archived_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json = json_dict(name="metadata")

    company = relationship("Company")
    source_ai_job = relationship("AIJob")
    created_by_user = relationship("User", foreign_keys=[created_by_user_id])
    created_by_employee = relationship("Employee", foreign_keys=[created_by_employee_id])

    __table_args__ = (
        Index("idx_company_memories_company_status", "company_id", "status"),
        Index("idx_company_memories_company_type", "company_id", "memory_type"),
        Index("idx_company_memories_scope", "company_id", "scope_type", "scope_id"),
        Index("idx_company_memories_source", "company_id", "source_type", "source_id"),
        Index("idx_company_memories_source_ai_job_id", "source_ai_job_id"),
        Index("idx_company_memories_importance", "company_id", "importance"),
        Index("idx_company_memories_created_at", "created_at"),
        Index("idx_company_memories_approved_at", "approved_at"),
    )
