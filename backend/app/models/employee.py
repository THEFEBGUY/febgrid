from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, json_dict, json_list, uuid_pk


class Employee(TimestampMixin, Base):
    __tablename__ = "employees"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    manager_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
    )
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40))
    role: Mapped[str] = mapped_column(String(120), nullable=False)
    department: Mapped[str | None] = mapped_column(String(120))
    employment_type: Mapped[str] = mapped_column(String(80), default="full_time", nullable=False)
    status: Mapped[str] = mapped_column(String(60), default="available", nullable=False)
    location: Mapped[str | None] = mapped_column(String(160))
    profile_image_url: Mapped[str | None] = mapped_column(Text)
    skills = json_list()
    metadata_json = json_dict(name="metadata")

    company = relationship("Company", back_populates="employees")
    manager = relationship("Employee", remote_side=[id])
    led_teams = relationship("Team", back_populates="lead", foreign_keys="Team.lead_employee_id")

    __table_args__ = (
        UniqueConstraint("company_id", "email", name="uq_employees_company_email"),
        Index("idx_employees_company_id", "company_id"),
        Index("idx_employees_company_status", "company_id", "status"),
        Index("idx_employees_manager_id", "manager_id"),
    )
