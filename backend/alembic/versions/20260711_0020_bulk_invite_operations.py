"""add bulk invite operations

Revision ID: 20260711_0020
Revises: 20260709_0019
Create Date: 2026-07-11 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260711_0020"
down_revision: str | None = "20260709_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bulk_invite_operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("invited_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="processing"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "actor_user_id", "idempotency_key", name="uq_bulk_invite_operation_idempotency"),
    )
    op.create_index("idx_bulk_invite_operations_company_created", "bulk_invite_operations", ["company_id", "created_at"], unique=False)
    op.create_index("idx_bulk_invite_operations_actor_key", "bulk_invite_operations", ["actor_user_id", "idempotency_key"], unique=False)
    op.create_index("idx_bulk_invite_operations_status", "bulk_invite_operations", ["company_id", "status"], unique=False)
    op.alter_column("bulk_invite_operations", "total_rows", server_default=None)
    op.alter_column("bulk_invite_operations", "valid_rows", server_default=None)
    op.alter_column("bulk_invite_operations", "invited_rows", server_default=None)
    op.alter_column("bulk_invite_operations", "skipped_rows", server_default=None)
    op.alter_column("bulk_invite_operations", "failed_rows", server_default=None)
    op.alter_column("bulk_invite_operations", "status", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_bulk_invite_operations_status", table_name="bulk_invite_operations")
    op.drop_index("idx_bulk_invite_operations_actor_key", table_name="bulk_invite_operations")
    op.drop_index("idx_bulk_invite_operations_company_created", table_name="bulk_invite_operations")
    op.drop_table("bulk_invite_operations")
