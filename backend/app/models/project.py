from datetime import date
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String, Text
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
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(60), default="not_started", nullable=False)
    priority: Mapped[str] = mapped_column(String(40), default="medium", nullable=False)
    start_date: Mapped[date | None]
    due_date: Mapped[date | None]
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tags = json_list()

    company = relationship("Company", back_populates="projects")
    owner = relationship("Employee")
    work_objects = relationship("WorkObject", back_populates="project")

    __table_args__ = (
        Index("idx_projects_company_id", "company_id"),
        Index("idx_projects_company_status", "company_id", "status"),
    )
