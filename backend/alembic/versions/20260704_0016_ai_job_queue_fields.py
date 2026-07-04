"""add ai job queue reliability fields

Revision ID: 20260704_0016
Revises: 20260703_0015
Create Date: 2026-07-04 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260704_0016"
down_revision: str | None = "20260703_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ai_jobs", sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_jobs", sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_jobs", sa.Column("locked_by", sa.String(length=120), nullable=True))
    op.add_column("ai_jobs", sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_jobs", sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_jobs", sa.Column("timeout_seconds", sa.Integer(), server_default="30", nullable=False))
    op.add_column("ai_jobs", sa.Column("error_code", sa.String(length=120), nullable=True))
    op.add_column("ai_jobs", sa.Column("retryable", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("ai_jobs", sa.Column("cancelled_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ai_jobs", sa.Column("cancellation_reason", sa.Text(), nullable=True))
    op.add_column("ai_jobs", sa.Column("run_mode", sa.String(length=40), server_default="manual", nullable=False))
    op.create_foreign_key(
        "fk_ai_jobs_cancelled_by_user_id",
        "ai_jobs",
        "users",
        ["cancelled_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("idx_ai_jobs_company_next_attempt", "ai_jobs", ["company_id", "status", "next_attempt_at"], unique=False)
    op.create_index("idx_ai_jobs_company_locked_at", "ai_jobs", ["company_id", "locked_at"], unique=False)
    op.create_index("idx_ai_jobs_run_mode", "ai_jobs", ["company_id", "run_mode"], unique=False)
    op.alter_column("ai_jobs", "timeout_seconds", server_default=None)
    op.alter_column("ai_jobs", "retryable", server_default=None)
    op.alter_column("ai_jobs", "run_mode", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_ai_jobs_run_mode", table_name="ai_jobs")
    op.drop_index("idx_ai_jobs_company_locked_at", table_name="ai_jobs")
    op.drop_index("idx_ai_jobs_company_next_attempt", table_name="ai_jobs")
    op.drop_constraint("fk_ai_jobs_cancelled_by_user_id", "ai_jobs", type_="foreignkey")
    op.drop_column("ai_jobs", "run_mode")
    op.drop_column("ai_jobs", "cancellation_reason")
    op.drop_column("ai_jobs", "cancelled_by_user_id")
    op.drop_column("ai_jobs", "retryable")
    op.drop_column("ai_jobs", "error_code")
    op.drop_column("ai_jobs", "timeout_seconds")
    op.drop_column("ai_jobs", "last_attempt_at")
    op.drop_column("ai_jobs", "next_attempt_at")
    op.drop_column("ai_jobs", "locked_by")
    op.drop_column("ai_jobs", "locked_at")
    op.drop_column("ai_jobs", "queued_at")
