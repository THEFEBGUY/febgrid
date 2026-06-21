from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
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
    department_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
    )
    team_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
    )
    creator_employee_id: Mapped[UUID | None] = mapped_column(
        "created_by_employee_id",
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
    )
    creator_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    assignee_employee_id: Mapped[UUID | None] = mapped_column(
        "assigned_to_employee_id",
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
    )
    title: Mapped[str] = mapped_column(String(220), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    object_type: Mapped[str] = mapped_column(String(80), default="task", nullable=False)
    status: Mapped[str] = mapped_column(String(60), default="assigned", nullable=False)
    priority: Mapped[str] = mapped_column(String(40), default="medium", nullable=False)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tags = json_list()
    metadata_json = json_dict(name="metadata")
    custom_fields = json_dict()
    ai_summary: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    company = relationship("Company", back_populates="work_objects")
    project = relationship("Project", back_populates="work_objects")
    department = relationship("Department")
    team = relationship("Team")
    creator_employee = relationship("Employee", foreign_keys=[creator_employee_id])
    creator_user = relationship("User")
    assignee = relationship("Employee", foreign_keys=[assignee_employee_id])

    @property
    def created_by_employee_id(self) -> UUID | None:
        return self.creator_employee_id

    @created_by_employee_id.setter
    def created_by_employee_id(self, value: UUID | None) -> None:
        self.creator_employee_id = value

    @property
    def assigned_to_employee_id(self) -> UUID | None:
        return self.assignee_employee_id

    @assigned_to_employee_id.setter
    def assigned_to_employee_id(self, value: UUID | None) -> None:
        self.assignee_employee_id = value

    __table_args__ = (
        Index("idx_work_objects_company_id", "company_id"),
        Index("idx_work_objects_assigned_to", "assigned_to_employee_id"),
        Index("idx_work_objects_project_id", "project_id"),
        Index("idx_work_objects_department_id", "department_id"),
        Index("idx_work_objects_team_id", "team_id"),
        Index("idx_work_objects_creator_user_id", "creator_user_id"),
        Index("idx_work_objects_status", "status"),
        Index("idx_work_objects_company_status", "company_id", "status"),
        Index("idx_work_objects_company_active", "company_id", "is_active"),
    )
