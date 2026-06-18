from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, json_dict, json_list, uuid_pk


class WorkObject(TimestampMixin, Base):
    __tablename__ = "work_objects"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
    )
    created_by_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
    )
    assigned_to_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
    )
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    object_type: Mapped[str] = mapped_column(String(80), default="task", nullable=False)
    status: Mapped[str] = mapped_column(String(60), default="draft", nullable=False)
    priority: Mapped[str] = mapped_column(String(40), default="medium", nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tags = json_list()
    custom_fields = json_dict()
    ai_summary: Mapped[str | None] = mapped_column(Text)

    company = relationship("Company", back_populates="work_objects")
    project = relationship("Project", back_populates="work_objects")
    created_by = relationship("Employee", foreign_keys=[created_by_employee_id])
    assigned_to = relationship("Employee", foreign_keys=[assigned_to_employee_id])

    __table_args__ = (
        Index("idx_work_objects_company_id", "company_id"),
        Index("idx_work_objects_assigned_to", "assigned_to_employee_id"),
        Index("idx_work_objects_project_id", "project_id"),
        Index("idx_work_objects_status", "status"),
        Index("idx_work_objects_company_status", "company_id", "status"),
    )
