"""add employee digital twin snapshots

Revision ID: 20260709_0018
Revises: 20260708_0017
Create Date: 2026-07-09 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260709_0018"
down_revision: str | None = "20260708_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "employee_digital_twin_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("period_days", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("workload_level", sa.String(length=40), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("profile_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("work_metrics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("project_metrics_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("availability_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("skills_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("strengths_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("attention_areas_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risks_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommended_actions_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
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
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_employee_twin_company_employee_created",
        "employee_digital_twin_snapshots",
        ["company_id", "employee_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_employee_twin_company_created",
        "employee_digital_twin_snapshots",
        ["company_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_employee_twin_employee_created",
        "employee_digital_twin_snapshots",
        ["employee_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_employee_twin_generated_by_user",
        "employee_digital_twin_snapshots",
        ["generated_by_user_id"],
        unique=False,
    )
    op.alter_column("employee_digital_twin_snapshots", "is_rule_based", server_default=None)
    op.alter_column("employee_digital_twin_snapshots", "ai_narrative_used", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_employee_twin_generated_by_user", table_name="employee_digital_twin_snapshots")
    op.drop_index("idx_employee_twin_employee_created", table_name="employee_digital_twin_snapshots")
    op.drop_index("idx_employee_twin_company_created", table_name="employee_digital_twin_snapshots")
    op.drop_index("idx_employee_twin_company_employee_created", table_name="employee_digital_twin_snapshots")
    op.drop_table("employee_digital_twin_snapshots")
