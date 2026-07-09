from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, json_dict, json_list, uuid_pk


class EmployeeDigitalTwinSnapshot(TimestampMixin, Base):
    __tablename__ = "employee_digital_twin_snapshots"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    employee_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    generated_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    period_days: Mapped[int] = mapped_column(Integer, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    workload_level: Mapped[str] = mapped_column(String(40), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    profile_json = json_dict()
    work_metrics_json = json_dict()
    project_metrics_json = json_dict()
    availability_json = json_dict()
    skills_json = json_list()
    strengths_json = json_list()
    attention_areas_json = json_list()
    risks_json = json_list()
    recommended_actions_json = json_list()
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
    employee = relationship("Employee", foreign_keys=[employee_id])
    generated_by_user = relationship("User")
    ai_job = relationship("AIJob")

    __table_args__ = (
        Index("idx_employee_twin_company_employee_created", "company_id", "employee_id", "created_at"),
        Index("idx_employee_twin_company_created", "company_id", "created_at"),
        Index("idx_employee_twin_employee_created", "employee_id", "created_at"),
        Index("idx_employee_twin_generated_by_user", "generated_by_user_id"),
    )
