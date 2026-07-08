"""add company pulse snapshots

Revision ID: 20260708_0017
Revises: 20260704_0016
Create Date: 2026-07-08 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260708_0017"
down_revision: str | None = "20260704_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_pulse_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("pulse_status", sa.String(length=40), nullable=False),
        sa.Column("trend", sa.String(length=40), server_default="unknown", nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("section_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("key_signals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommended_actions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_counts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("generated_by_ai_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_rule_based", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generated_by_ai_job_id"], ["ai_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_company_pulse_company_created", "company_pulse_snapshots", ["company_id", "created_at"], unique=False)
    op.create_index("idx_company_pulse_company_score", "company_pulse_snapshots", ["company_id", "overall_score"], unique=False)
    op.create_index("idx_company_pulse_company_status", "company_pulse_snapshots", ["company_id", "pulse_status"], unique=False)
    op.alter_column("company_pulse_snapshots", "trend", server_default=None)
    op.alter_column("company_pulse_snapshots", "is_rule_based", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_company_pulse_company_status", table_name="company_pulse_snapshots")
    op.drop_index("idx_company_pulse_company_score", table_name="company_pulse_snapshots")
    op.drop_index("idx_company_pulse_company_created", table_name="company_pulse_snapshots")
    op.drop_table("company_pulse_snapshots")
