from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, json_dict, json_list, uuid_pk


class WorkObjectType(TimestampMixin, Base):
    __tablename__ = "work_object_types"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(80))
    color: Mapped[str | None] = mapped_column(String(40))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    metadata_json = json_dict(name="metadata")

    company = relationship("Company")
    custom_fields = relationship("CustomFieldDefinition", back_populates="work_object_type", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("company_id", "key", name="uq_work_object_types_company_key"),
        Index("idx_work_object_types_company_id", "company_id"),
        Index("idx_work_object_types_company_active", "company_id", "is_active", "sort_order"),
        Index("idx_work_object_types_key", "key"),
    )


class CustomFieldDefinition(TimestampMixin, Base):
    __tablename__ = "custom_field_definitions"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    work_object_type_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("work_object_types.id", ondelete="SET NULL"),
    )
    type_key: Mapped[str] = mapped_column(String(80), nullable=False)
    field_key: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(140), nullable=False)
    field_type: Mapped[str] = mapped_column(String(40), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    options = json_list()
    default_value: Mapped[Any | None] = mapped_column(JSONB)
    help_text: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json = json_dict(name="metadata")

    company = relationship("Company")
    work_object_type = relationship("WorkObjectType", back_populates="custom_fields")

    __table_args__ = (
        UniqueConstraint("company_id", "type_key", "field_key", name="uq_custom_fields_company_type_key"),
        Index("idx_custom_fields_company_id", "company_id"),
        Index("idx_custom_fields_company_type_active", "company_id", "type_key", "is_active", "sort_order"),
        Index("idx_custom_fields_field_key", "field_key"),
        Index("idx_custom_fields_work_object_type_id", "work_object_type_id"),
    )
