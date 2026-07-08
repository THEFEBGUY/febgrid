from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, json_dict, json_list, uuid_pk


class CompanyPulseSnapshot(TimestampMixin, Base):
    __tablename__ = "company_pulse_snapshots"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    pulse_status: Mapped[str] = mapped_column(String(40), nullable=False)
    trend: Mapped[str] = mapped_column(String(40), default="unknown", nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    section_scores = json_dict()
    key_signals = json_list()
    risks = json_list()
    recommended_actions = json_list()
    source_counts = json_dict()
    generated_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    generated_by_ai_job_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ai_jobs.id", ondelete="SET NULL"),
    )
    is_rule_based: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json = json_dict(name="metadata")

    company = relationship("Company")
    generated_by_user = relationship("User")
    generated_by_ai_job = relationship("AIJob")

    __table_args__ = (
        Index("idx_company_pulse_company_created", "company_id", "created_at"),
        Index("idx_company_pulse_company_status", "company_id", "pulse_status"),
        Index("idx_company_pulse_company_score", "company_id", "overall_score"),
    )
