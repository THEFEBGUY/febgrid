"""add company settings templates and configurable work fields

Revision ID: 20260626_0011
Revises: 20260624_0010
Create Date: 2026-06-26 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260626_0011"
down_revision: str | None = "20260624_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_object_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=80), nullable=True),
        sa.Column("color", sa.String(length=40), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "key", name="uq_work_object_types_company_key"),
    )
    op.create_index("idx_work_object_types_company_active", "work_object_types", ["company_id", "is_active", "sort_order"], unique=False)
    op.create_index("idx_work_object_types_company_id", "work_object_types", ["company_id"], unique=False)
    op.create_index("idx_work_object_types_key", "work_object_types", ["key"], unique=False)

    op.create_table(
        "custom_field_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("work_object_type_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("type_key", sa.String(length=80), nullable=False),
        sa.Column("field_key", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=140), nullable=False),
        sa.Column("field_type", sa.String(length=40), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("default_value", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("help_text", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_object_type_id"], ["work_object_types.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "type_key", "field_key", name="uq_custom_fields_company_type_key"),
    )
    op.create_index("idx_custom_fields_company_id", "custom_field_definitions", ["company_id"], unique=False)
    op.create_index(
        "idx_custom_fields_company_type_active",
        "custom_field_definitions",
        ["company_id", "type_key", "is_active", "sort_order"],
        unique=False,
    )
    op.create_index("idx_custom_fields_field_key", "custom_field_definitions", ["field_key"], unique=False)
    op.create_index("idx_custom_fields_work_object_type_id", "custom_field_definitions", ["work_object_type_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_custom_fields_work_object_type_id", table_name="custom_field_definitions")
    op.drop_index("idx_custom_fields_field_key", table_name="custom_field_definitions")
    op.drop_index("idx_custom_fields_company_type_active", table_name="custom_field_definitions")
    op.drop_index("idx_custom_fields_company_id", table_name="custom_field_definitions")
    op.drop_table("custom_field_definitions")
    op.drop_index("idx_work_object_types_key", table_name="work_object_types")
    op.drop_index("idx_work_object_types_company_id", table_name="work_object_types")
    op.drop_index("idx_work_object_types_company_active", table_name="work_object_types")
    op.drop_table("work_object_types")
