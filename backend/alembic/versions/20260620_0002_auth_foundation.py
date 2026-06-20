"""add auth user foundation

Revision ID: 20260620_0002
Revises: 20260618_0001
Create Date: 2026-06-20 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260620_0002"
down_revision: str | None = "20260618_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("auth_provider", sa.String(length=40), nullable=False),
        sa.Column("supabase_user_id", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("supabase_user_id", name="uq_users_supabase_user_id"),
    )
    op.create_index("idx_users_company_id", "users", ["company_id"], unique=False)
    op.create_index("idx_users_company_role", "users", ["company_id", "role"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_users_company_role", table_name="users")
    op.drop_index("idx_users_company_id", table_name="users")
    op.drop_table("users")
