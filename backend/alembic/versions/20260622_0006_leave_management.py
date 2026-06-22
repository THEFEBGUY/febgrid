"""add leave management workflow fields

Revision ID: 20260622_0006
Revises: 20260621_0005
Create Date: 2026-06-22 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260622_0006"
down_revision: str | None = "20260621_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("leave_requests", sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("leave_requests", sa.Column("total_days", sa.Float(), nullable=False, server_default=sa.text("1")))
    op.add_column(
        "leave_requests",
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.add_column("leave_requests", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("leave_requests", sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("leave_requests", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "leave_requests",
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column("leave_requests", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_foreign_key(
        "fk_leave_requests_requested_by_user_id_users",
        "leave_requests",
        "users",
        ["requested_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_leave_requests_company_active", "leave_requests", ["company_id", "is_active"], unique=False)
    op.create_index("idx_leave_requests_approver_employee_id", "leave_requests", ["approver_employee_id"], unique=False)
    op.create_index("idx_leave_requests_requested_by_user_id", "leave_requests", ["requested_by_user_id"], unique=False)
    op.create_index("idx_leave_requests_submitted_at", "leave_requests", ["submitted_at"], unique=False)
    op.alter_column("leave_requests", "total_days", server_default=None)
    op.alter_column("leave_requests", "submitted_at", server_default=None)
    op.alter_column("leave_requests", "metadata", server_default=None)
    op.alter_column("leave_requests", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_leave_requests_submitted_at", table_name="leave_requests")
    op.drop_index("idx_leave_requests_requested_by_user_id", table_name="leave_requests")
    op.drop_index("idx_leave_requests_approver_employee_id", table_name="leave_requests")
    op.drop_index("idx_leave_requests_company_active", table_name="leave_requests")
    op.drop_constraint("fk_leave_requests_requested_by_user_id_users", "leave_requests", type_="foreignkey")
    op.drop_column("leave_requests", "is_active")
    op.drop_column("leave_requests", "metadata")
    op.drop_column("leave_requests", "cancelled_at")
    op.drop_column("leave_requests", "rejected_at")
    op.drop_column("leave_requests", "approved_at")
    op.drop_column("leave_requests", "submitted_at")
    op.drop_column("leave_requests", "total_days")
    op.drop_column("leave_requests", "requested_by_user_id")
