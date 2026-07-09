from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, json_dict, json_list, uuid_pk


class WorkDNASnapshot(TimestampMixin, Base):
    __tablename__ = "work_dna_snapshots"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    scope_type: Mapped[str] = mapped_column(String(40), nullable=False)
    scope_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    generated_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    overall_summary: Mapped[str] = mapped_column(Text, nullable=False)
    work_volume_json = json_dict()
    work_type_distribution_json = json_list()
    status_distribution_json = json_list()
    priority_distribution_json = json_list()
    completion_patterns_json = json_list()
    overdue_patterns_json = json_list()
    blocked_patterns_json = json_list()
    workflow_patterns_json = json_list()
    project_patterns_json = json_list()
    department_patterns_json = json_list()
    team_patterns_json = json_list()
    tag_patterns_json = json_list()
    recurring_patterns_json = json_list()
    deadline_patterns_json = json_list()
    bottlenecks_json = json_list()
    operational_strengths_json = json_list()
    attention_areas_json = json_list()
    risks_json = json_list()
    recommended_improvements_json = json_list()
    template_candidates_json = json_list()
    automation_candidates_json = json_list()
    source_counts_json = json_dict()
    data_coverage_json = json_dict()
    limitations_json = json_list()
    is_rule_based: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    ai_narrative_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ai_job_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ai_jobs.id", ondelete="SET NULL"),
    )
    provider_mode: Mapped[str | None] = mapped_column(String(80))
    provider_key: Mapped[str | None] = mapped_column(String(80))
    model_name: Mapped[str | None] = mapped_column(String(160))
    metadata_json = json_dict(name="metadata")

    company = relationship("Company")
    generated_by_user = relationship("User")
    ai_job = relationship("AIJob")

    __table_args__ = (
        Index("idx_work_dna_company_created", "company_id", "created_at"),
        Index("idx_work_dna_scope_created", "company_id", "scope_type", "scope_id", "created_at"),
        Index("idx_work_dna_scope", "scope_type", "scope_id"),
        Index("idx_work_dna_generated_by_user", "generated_by_user_id"),
    )
