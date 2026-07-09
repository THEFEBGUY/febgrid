"""add work dna snapshots

Revision ID: 20260709_0019
Revises: 20260709_0018
Create Date: 2026-07-09 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260709_0019"
down_revision: str | None = "20260709_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_dna_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scope_type", sa.String(length=40), nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("generated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("period_days", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("overall_summary", sa.Text(), nullable=False),
        sa.Column("work_volume_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("work_type_distribution_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status_distribution_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("priority_distribution_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("completion_patterns_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("overdue_patterns_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("blocked_patterns_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("workflow_patterns_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("project_patterns_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("department_patterns_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("team_patterns_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tag_patterns_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recurring_patterns_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("deadline_patterns_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("bottlenecks_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("operational_strengths_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("attention_areas_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risks_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommended_improvements_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("template_candidates_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("automation_candidates_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("source_counts_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("data_coverage_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("limitations_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_rule_based", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("ai_narrative_used", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("ai_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_mode", sa.String(length=80), nullable=True),
        sa.Column("provider_key", sa.String(length=80), nullable=True),
        sa.Column("model_name", sa.String(length=160), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ai_job_id"], ["ai_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_work_dna_company_created", "work_dna_snapshots", ["company_id", "created_at"], unique=False)
    op.create_index("idx_work_dna_scope_created", "work_dna_snapshots", ["company_id", "scope_type", "scope_id", "created_at"], unique=False)
    op.create_index("idx_work_dna_scope", "work_dna_snapshots", ["scope_type", "scope_id"], unique=False)
    op.create_index("idx_work_dna_generated_by_user", "work_dna_snapshots", ["generated_by_user_id"], unique=False)
    op.alter_column("work_dna_snapshots", "is_rule_based", server_default=None)
    op.alter_column("work_dna_snapshots", "ai_narrative_used", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_work_dna_generated_by_user", table_name="work_dna_snapshots")
    op.drop_index("idx_work_dna_scope", table_name="work_dna_snapshots")
    op.drop_index("idx_work_dna_scope_created", table_name="work_dna_snapshots")
    op.drop_index("idx_work_dna_company_created", table_name="work_dna_snapshots")
    op.drop_table("work_dna_snapshots")
