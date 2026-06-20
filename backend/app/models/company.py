from uuid import UUID

from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, json_dict, uuid_pk


class Company(TimestampMixin, Base):
    __tablename__ = "companies"

    id: Mapped[UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    industry: Mapped[str | None] = mapped_column(String(120))
    size: Mapped[str | None] = mapped_column(String(80))
    timezone: Mapped[str] = mapped_column(String(80), default="UTC", nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    settings_json = json_dict()
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    employees = relationship("Employee", back_populates="company", cascade="all, delete-orphan")
    teams = relationship("Team", back_populates="company", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="company", cascade="all, delete-orphan")
    work_objects = relationship("WorkObject", back_populates="company", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="company", cascade="all, delete-orphan")
    users = relationship("User", back_populates="company", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_companies_active", "is_active"),)
