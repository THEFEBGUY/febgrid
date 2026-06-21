from datetime import date
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, json_list, uuid_pk


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
    )
    owner_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    department_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
    )
    team_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="SET NULL"),
    )
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    code: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(60), default="not_started", nullable=False)
    priority: Mapped[str] = mapped_column(String(40), default="medium", nullable=False)
    start_date: Mapped[date | None]
    due_date: Mapped[date | None]
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_level: Mapped[str | None] = mapped_column(String(40))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    tags = json_list()

    company = relationship("Company", back_populates="projects")
    owner = relationship("Employee", foreign_keys=[owner_employee_id])
    owner_user = relationship("User")
    department = relationship("Department")
    team = relationship("Team")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    work_objects = relationship("WorkObject", back_populates="project")

    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_projects_company_code"),
        Index("idx_projects_company_id", "company_id"),
        Index("idx_projects_company_status", "company_id", "status"),
        Index("idx_projects_company_active", "company_id", "is_active"),
        Index("idx_projects_department_id", "department_id"),
        Index("idx_projects_team_id", "team_id"),
        Index("idx_projects_owner_employee_id", "owner_employee_id"),
    )


class ProjectMember(TimestampMixin, Base):
    __tablename__ = "project_members"

    id: Mapped[UUID] = uuid_pk()
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
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
    role_on_project: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    project = relationship("Project", back_populates="members")
    employee = relationship("Employee")

    __table_args__ = (
        UniqueConstraint("project_id", "employee_id", name="uq_project_members_project_employee"),
        Index("idx_project_members_company_id", "company_id"),
        Index("idx_project_members_employee_id", "employee_id"),
        Index("idx_project_members_project_active", "project_id", "is_active"),
    )
