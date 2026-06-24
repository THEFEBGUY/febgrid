"""add notification preferences foundation

Revision ID: 20260624_0010
Revises: 20260623_0009
Create Date: 2026-06-24 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260624_0010"
down_revision: str | None = "20260623_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("in_app_enabled", sa.Boolean(), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), nullable=False),
        sa.Column("mentions_enabled", sa.Boolean(), nullable=False),
        sa.Column("assignments_enabled", sa.Boolean(), nullable=False),
        sa.Column("leave_decisions_enabled", sa.Boolean(), nullable=False),
        sa.Column("project_updates_enabled", sa.Boolean(), nullable=False),
        sa.Column("announcements_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "employee_id", name="uq_notification_preferences_company_employee"),
        sa.UniqueConstraint("company_id", "user_id", name="uq_notification_preferences_company_user"),
    )
    op.create_index("idx_notification_preferences_company_id", "notification_preferences", ["company_id"], unique=False)
    op.create_index("idx_notification_preferences_employee_id", "notification_preferences", ["employee_id"], unique=False)
    op.create_index("idx_notification_preferences_user_id", "notification_preferences", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_notification_preferences_user_id", table_name="notification_preferences")
    op.drop_index("idx_notification_preferences_employee_id", table_name="notification_preferences")
    op.drop_index("idx_notification_preferences_company_id", table_name="notification_preferences")
    op.drop_table("notification_preferences")
