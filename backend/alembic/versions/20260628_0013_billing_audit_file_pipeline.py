"""add billing prep and file pipeline metadata

Revision ID: 20260628_0013
Revises: 20260626_0012
Create Date: 2026-06-28 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260628_0013"
down_revision: str | None = "20260626_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_billing_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_key", sa.String(length=40), nullable=False),
        sa.Column("billing_status", sa.String(length=40), nullable=False),
        sa.Column("trial_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("seat_limit", sa.Integer(), nullable=False),
        sa.Column("storage_limit_mb", sa.Integer(), nullable=False),
        sa.Column("work_object_limit", sa.Integer(), nullable=False),
        sa.Column("project_limit", sa.Integer(), nullable=False),
        sa.Column("employee_limit", sa.Integer(), nullable=False),
        sa.Column("notification_limit", sa.Integer(), nullable=True),
        sa.Column("file_upload_limit_mb", sa.Integer(), nullable=False),
        sa.Column("is_trial", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id"),
    )
    op.create_index("idx_company_billing_active", "company_billing_plans", ["company_id", "is_active"], unique=False)
    op.create_index("idx_company_billing_company_id", "company_billing_plans", ["company_id"], unique=False)
    op.create_index("idx_company_billing_plan_key", "company_billing_plans", ["plan_key"], unique=False)
    op.create_index("idx_company_billing_status", "company_billing_plans", ["billing_status"], unique=False)

    op.add_column("attachments", sa.Column("extension", sa.String(length=20), nullable=True))
    op.add_column("attachments", sa.Column("checksum_sha256", sa.String(length=128), nullable=True))
    op.add_column("attachments", sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False))
    op.add_column("attachments", sa.Column("processing_status", sa.String(length=40), server_default="uploaded", nullable=False))
    op.add_column("attachments", sa.Column("scan_status", sa.String(length=40), server_default="not_scanned", nullable=False))
    op.add_column("attachments", sa.Column("is_deleted", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("attachments", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("attachments", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("idx_attachments_uploaded_by_employee_id", "attachments", ["uploaded_by_employee_id"], unique=False)
    op.create_index("idx_attachments_company_processing", "attachments", ["company_id", "processing_status"], unique=False)
    op.create_index("idx_attachments_company_deleted", "attachments", ["company_id", "is_deleted"], unique=False)
    op.alter_column("attachments", "tags", server_default=None)
    op.alter_column("attachments", "processing_status", server_default=None)
    op.alter_column("attachments", "scan_status", server_default=None)
    op.alter_column("attachments", "is_deleted", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_attachments_company_deleted", table_name="attachments")
    op.drop_index("idx_attachments_company_processing", table_name="attachments")
    op.drop_index("idx_attachments_uploaded_by_employee_id", table_name="attachments")
    op.drop_column("attachments", "deleted_at")
    op.drop_column("attachments", "archived_at")
    op.drop_column("attachments", "is_deleted")
    op.drop_column("attachments", "scan_status")
    op.drop_column("attachments", "processing_status")
    op.drop_column("attachments", "tags")
    op.drop_column("attachments", "checksum_sha256")
    op.drop_column("attachments", "extension")

    op.drop_index("idx_company_billing_status", table_name="company_billing_plans")
    op.drop_index("idx_company_billing_plan_key", table_name="company_billing_plans")
    op.drop_index("idx_company_billing_company_id", table_name="company_billing_plans")
    op.drop_index("idx_company_billing_active", table_name="company_billing_plans")
    op.drop_table("company_billing_plans")
