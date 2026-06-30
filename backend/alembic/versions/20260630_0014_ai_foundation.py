"""add ai foundation job lifecycle fields

Revision ID: 20260630_0014
Revises: 20260628_0013
Create Date: 2026-06-30 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260630_0014"
down_revision: str | None = "20260628_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("ai_jobs", sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ai_jobs", sa.Column("priority", sa.String(length=40), server_default="normal", nullable=False))
    op.add_column("ai_jobs", sa.Column("input_entity_type", sa.String(length=80), nullable=True))
    op.add_column("ai_jobs", sa.Column("input_entity_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("ai_jobs", sa.Column("provider_key", sa.String(length=80), server_default="mock", nullable=False))
    op.add_column("ai_jobs", sa.Column("provider_mode", sa.String(length=40), server_default="mock", nullable=False))
    op.add_column("ai_jobs", sa.Column("attempts", sa.Integer(), server_default="0", nullable=False))
    op.add_column("ai_jobs", sa.Column("max_attempts", sa.Integer(), server_default="1", nullable=False))
    op.add_column("ai_jobs", sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_jobs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_jobs", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_jobs", sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_jobs", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_jobs", sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False))
    op.create_foreign_key(
        "fk_ai_jobs_requested_by_user_id_users",
        "ai_jobs",
        "users",
        ["requested_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute("UPDATE ai_jobs SET status = 'succeeded' WHERE status = 'completed'")
    op.execute(
        "UPDATE ai_jobs SET input_entity_type = related_entity_type "
        "WHERE input_entity_type IS NULL AND related_entity_type IS NOT NULL"
    )
    op.execute(
        "UPDATE ai_jobs SET input_entity_id = related_entity_id "
        "WHERE input_entity_id IS NULL AND related_entity_id IS NOT NULL"
    )
    op.create_index("idx_ai_jobs_company_job_type", "ai_jobs", ["company_id", "job_type"], unique=False)
    op.create_index("idx_ai_jobs_requested_by_user_id", "ai_jobs", ["requested_by_user_id"], unique=False)
    op.create_index("idx_ai_jobs_created_at", "ai_jobs", ["created_at"], unique=False)
    op.create_index("idx_ai_jobs_input_entity", "ai_jobs", ["input_entity_type", "input_entity_id"], unique=False)
    op.alter_column("ai_jobs", "priority", server_default=None)
    op.alter_column("ai_jobs", "provider_key", server_default=None)
    op.alter_column("ai_jobs", "provider_mode", server_default=None)
    op.alter_column("ai_jobs", "attempts", server_default=None)
    op.alter_column("ai_jobs", "max_attempts", server_default=None)
    op.alter_column("ai_jobs", "metadata", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_ai_jobs_input_entity", table_name="ai_jobs")
    op.drop_index("idx_ai_jobs_created_at", table_name="ai_jobs")
    op.drop_index("idx_ai_jobs_requested_by_user_id", table_name="ai_jobs")
    op.drop_index("idx_ai_jobs_company_job_type", table_name="ai_jobs")
    op.drop_constraint("fk_ai_jobs_requested_by_user_id_users", "ai_jobs", type_="foreignkey")
    op.drop_column("ai_jobs", "metadata")
    op.drop_column("ai_jobs", "cancelled_at")
    op.drop_column("ai_jobs", "failed_at")
    op.drop_column("ai_jobs", "completed_at")
    op.drop_column("ai_jobs", "started_at")
    op.drop_column("ai_jobs", "scheduled_at")
    op.drop_column("ai_jobs", "max_attempts")
    op.drop_column("ai_jobs", "attempts")
    op.drop_column("ai_jobs", "provider_mode")
    op.drop_column("ai_jobs", "provider_key")
    op.drop_column("ai_jobs", "input_entity_id")
    op.drop_column("ai_jobs", "input_entity_type")
    op.drop_column("ai_jobs", "priority")
    op.drop_column("ai_jobs", "requested_by_user_id")
