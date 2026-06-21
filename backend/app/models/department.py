from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, uuid_pk


class Department(TimestampMixin, Base):
    __tablename__ = "departments"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    company = relationship("Company", back_populates="departments")
    employees = relationship("Employee", back_populates="department_ref")
    teams = relationship("Team", back_populates="department_ref")

    __table_args__ = (
        UniqueConstraint("company_id", "name", name="uq_departments_company_name"),
        Index("idx_departments_company_id", "company_id"),
        Index("idx_departments_company_active", "company_id", "is_active"),
    )
