"""add employee invitation and activation foundation

Revision ID: 20260626_0012
Revises: 20260626_0011
Create Date: 2026-06-26 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260626_0012"
down_revision: str | None = "20260626_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("account_status", sa.String(length=60), server_default="active", nullable=False))
    op.add_column("employees", sa.Column("activation_status", sa.String(length=60), server_default="activated", nullable=False))
    op.add_column("employees", sa.Column("profile_completion_status", sa.String(length=60), server_default="complete", nullable=False))
    op.create_index("idx_employees_company_account_status", "employees", ["company_id", "account_status"], unique=False)
    op.create_index("idx_employees_company_activation_status", "employees", ["company_id", "activation_status"], unique=False)
    op.alter_column("employees", "account_status", server_default=None)
    op.alter_column("employees", "activation_status", server_default=None)
    op.alter_column("employees", "profile_completion_status", server_default=None)

    op.create_table(
        "employee_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("invited_email", sa.String(length=255), nullable=False),
        sa.Column("normalized_email", sa.String(length=255), nullable=False),
        sa.Column("invited_role", sa.String(length=40), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("manager_employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("job_title", sa.String(length=120), nullable=True),
        sa.Column("employment_type", sa.String(length=80), nullable=True),
        sa.Column("joining_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invite_source", sa.String(length=40), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=60), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("invited_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["manager_employee_id"], ["employees.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rejected_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_employee_invitations_token_hash"),
    )
    op.create_index("idx_employee_invitations_company_id", "employee_invitations", ["company_id"], unique=False)
    op.create_index("idx_employee_invitations_company_email", "employee_invitations", ["company_id", "normalized_email"], unique=False)
    op.create_index("idx_employee_invitations_company_status", "employee_invitations", ["company_id", "status"], unique=False)
    op.create_index("idx_employee_invitations_employee_id", "employee_invitations", ["employee_id"], unique=False)
    op.create_index("idx_employee_invitations_expires_at", "employee_invitations", ["expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_employee_invitations_expires_at", table_name="employee_invitations")
    op.drop_index("idx_employee_invitations_employee_id", table_name="employee_invitations")
    op.drop_index("idx_employee_invitations_company_status", table_name="employee_invitations")
    op.drop_index("idx_employee_invitations_company_email", table_name="employee_invitations")
    op.drop_index("idx_employee_invitations_company_id", table_name="employee_invitations")
    op.drop_table("employee_invitations")
    op.drop_index("idx_employees_company_activation_status", table_name="employees")
    op.drop_index("idx_employees_company_account_status", table_name="employees")
    op.drop_column("employees", "profile_completion_status")
    op.drop_column("employees", "activation_status")
    op.drop_column("employees", "account_status")
