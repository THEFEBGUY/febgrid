"""add project management foundation

Revision ID: 20260621_0004
Revises: 20260621_0003
Create Date: 2026-06-21 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260621_0004"
down_revision: str | None = "20260621_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("projects", sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("projects", sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("projects", sa.Column("code", sa.String(length=80), nullable=True))
    op.add_column("projects", sa.Column("risk_level", sa.String(length=40), nullable=True))
    op.add_column("projects", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_foreign_key("fk_projects_owner_user_id_users", "projects", "users", ["owner_user_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_projects_department_id_departments", "projects", "departments", ["department_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_projects_team_id_teams", "projects", "teams", ["team_id"], ["id"], ondelete="SET NULL")
    op.create_unique_constraint("uq_projects_company_code", "projects", ["company_id", "code"])
    op.create_index("idx_projects_company_active", "projects", ["company_id", "is_active"], unique=False)
    op.create_index("idx_projects_department_id", "projects", ["department_id"], unique=False)
    op.create_index("idx_projects_team_id", "projects", ["team_id"], unique=False)
    op.create_index("idx_projects_owner_employee_id", "projects", ["owner_employee_id"], unique=False)
    op.alter_column("projects", "is_active", server_default=None)

    op.create_table(
        "project_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_on_project", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "employee_id", name="uq_project_members_project_employee"),
    )
    op.create_index("idx_project_members_company_id", "project_members", ["company_id"], unique=False)
    op.create_index("idx_project_members_employee_id", "project_members", ["employee_id"], unique=False)
    op.create_index("idx_project_members_project_active", "project_members", ["project_id", "is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_project_members_project_active", table_name="project_members")
    op.drop_index("idx_project_members_employee_id", table_name="project_members")
    op.drop_index("idx_project_members_company_id", table_name="project_members")
    op.drop_table("project_members")

    op.drop_index("idx_projects_owner_employee_id", table_name="projects")
    op.drop_index("idx_projects_team_id", table_name="projects")
    op.drop_index("idx_projects_department_id", table_name="projects")
    op.drop_index("idx_projects_company_active", table_name="projects")
    op.drop_constraint("uq_projects_company_code", "projects", type_="unique")
    op.drop_constraint("fk_projects_team_id_teams", "projects", type_="foreignkey")
    op.drop_constraint("fk_projects_department_id_departments", "projects", type_="foreignkey")
    op.drop_constraint("fk_projects_owner_user_id_users", "projects", type_="foreignkey")
    op.drop_column("projects", "is_active")
    op.drop_column("projects", "risk_level")
    op.drop_column("projects", "code")
    op.drop_column("projects", "team_id")
    op.drop_column("projects", "department_id")
    op.drop_column("projects", "owner_user_id")
