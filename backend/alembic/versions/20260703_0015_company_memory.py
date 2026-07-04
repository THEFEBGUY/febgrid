"""add company memory foundation

Revision ID: 20260703_0015
Revises: 20260630_0014
Create Date: 2026-07-03 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260703_0015"
down_revision: str | None = "20260630_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("memory_type", sa.String(length=60), server_default="general_note", nullable=False),
        sa.Column("scope_type", sa.String(length=60), server_default="company", nullable=False),
        sa.Column("scope_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_type", sa.String(length=80), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_ai_job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("importance", sa.String(length=20), server_default="normal", nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("visibility", sa.String(length=40), server_default="owner_admin", nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], name="fk_company_memories_approved_by_user_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["archived_by_user_id"], ["users.id"], name="fk_company_memories_archived_by_user_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], name="fk_company_memories_company_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_employee_id"], ["employees.id"], name="fk_company_memories_created_by_employee_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_company_memories_created_by_user_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rejected_by_user_id"], ["users.id"], name="fk_company_memories_rejected_by_user_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_ai_job_id"], ["ai_jobs.id"], name="fk_company_memories_source_ai_job_id", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_company_memories_approved_at", "company_memories", ["approved_at"], unique=False)
    op.create_index("idx_company_memories_company_status", "company_memories", ["company_id", "status"], unique=False)
    op.create_index("idx_company_memories_company_type", "company_memories", ["company_id", "memory_type"], unique=False)
    op.create_index("idx_company_memories_created_at", "company_memories", ["created_at"], unique=False)
    op.create_index("idx_company_memories_importance", "company_memories", ["company_id", "importance"], unique=False)
    op.create_index("idx_company_memories_scope", "company_memories", ["company_id", "scope_type", "scope_id"], unique=False)
    op.create_index("idx_company_memories_source", "company_memories", ["company_id", "source_type", "source_id"], unique=False)
    op.create_index("idx_company_memories_source_ai_job_id", "company_memories", ["source_ai_job_id"], unique=False)
    op.alter_column("company_memories", "memory_type", server_default=None)
    op.alter_column("company_memories", "scope_type", server_default=None)
    op.alter_column("company_memories", "tags", server_default=None)
    op.alter_column("company_memories", "importance", server_default=None)
    op.alter_column("company_memories", "status", server_default=None)
    op.alter_column("company_memories", "visibility", server_default=None)
    op.alter_column("company_memories", "metadata", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_company_memories_source_ai_job_id", table_name="company_memories")
    op.drop_index("idx_company_memories_source", table_name="company_memories")
    op.drop_index("idx_company_memories_scope", table_name="company_memories")
    op.drop_index("idx_company_memories_importance", table_name="company_memories")
    op.drop_index("idx_company_memories_created_at", table_name="company_memories")
    op.drop_index("idx_company_memories_company_type", table_name="company_memories")
    op.drop_index("idx_company_memories_company_status", table_name="company_memories")
    op.drop_index("idx_company_memories_approved_at", table_name="company_memories")
    op.drop_table("company_memories")
