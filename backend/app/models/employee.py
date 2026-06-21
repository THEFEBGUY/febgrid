from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, json_dict, json_list, utc_now, uuid_pk


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID | None] = mapped_column(
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
    manager_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
    )
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(40))
    role: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str | None] = mapped_column(String(120))
    employment_type: Mapped[str] = mapped_column(String(80), default="full_time", nullable=False)
    status: Mapped[str] = mapped_column(String(60), default="available", nullable=False)
    location: Mapped[str | None] = mapped_column(String(160))
    profile_image_url: Mapped[str | None] = mapped_column(Text)
    skills = json_list()
    metadata_json = json_dict(name="metadata")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    company = relationship("Company", back_populates="employees")
    user = relationship("User")
    department_ref = relationship("Department", back_populates="employees")
    team_ref = relationship("Team", foreign_keys=[team_id])
    manager = relationship("Employee", remote_side=[id])
    led_teams = relationship("Team", back_populates="lead", foreign_keys="Team.lead_employee_id")

    @property
    def role_title(self) -> str:
        return self.role

    @role_title.setter
    def role_title(self, value: str) -> None:
        self.role = value

    @property
    def current_status(self) -> str:
        return self.status

    @current_status.setter
    def current_status(self, value: str) -> None:
        self.status = value

    __table_args__ = (
        UniqueConstraint("company_id", "email", name="uq_employees_company_email"),
        UniqueConstraint("user_id", name="uq_employees_user_id"),
        Index("idx_employees_company_id", "company_id"),
        Index("idx_employees_company_status", "company_id", "status"),
        Index("idx_employees_company_active", "company_id", "is_active"),
        Index("idx_employees_department_id", "department_id"),
        Index("idx_employees_team_id", "team_id"),
        Index("idx_employees_manager_id", "manager_id"),
    )
