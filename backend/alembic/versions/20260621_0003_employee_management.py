"""add employee management foundation

Revision ID: 20260621_0003
Revises: 20260620_0002
Create Date: 2026-06-21 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260621_0003"
down_revision: str | None = "20260620_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "name", name="uq_departments_company_name"),
    )
    op.create_index("idx_departments_company_active", "departments", ["company_id", "is_active"], unique=False)
    op.create_index("idx_departments_company_id", "departments", ["company_id"], unique=False)

    op.add_column("teams", sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("teams", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_foreign_key("fk_teams_department_id_departments", "teams", "departments", ["department_id"], ["id"], ondelete="SET NULL")
    op.create_index("idx_teams_department_id", "teams", ["department_id"], unique=False)
    op.alter_column("teams", "is_active", server_default=None)

    op.add_column("employees", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("employees", sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("employees", sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("employees", sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.add_column("employees", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.alter_column("employees", "email", existing_type=sa.String(length=255), nullable=True)
    op.create_foreign_key("fk_employees_user_id_users", "employees", "users", ["user_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key(
        "fk_employees_department_id_departments",
        "employees",
        "departments",
        ["department_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key("fk_employees_team_id_teams", "employees", "teams", ["team_id"], ["id"], ondelete="SET NULL")
    op.create_unique_constraint("uq_employees_user_id", "employees", ["user_id"])
    op.create_index("idx_employees_company_active", "employees", ["company_id", "is_active"], unique=False)
    op.create_index("idx_employees_department_id", "employees", ["department_id"], unique=False)
    op.create_index("idx_employees_team_id", "employees", ["team_id"], unique=False)
    op.alter_column("employees", "joined_at", server_default=None)
    op.alter_column("employees", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_employees_team_id", table_name="employees")
    op.drop_index("idx_employees_department_id", table_name="employees")
    op.drop_index("idx_employees_company_active", table_name="employees")
    op.drop_constraint("uq_employees_user_id", "employees", type_="unique")
    op.drop_constraint("fk_employees_team_id_teams", "employees", type_="foreignkey")
    op.drop_constraint("fk_employees_department_id_departments", "employees", type_="foreignkey")
    op.drop_constraint("fk_employees_user_id_users", "employees", type_="foreignkey")
    op.alter_column("employees", "email", existing_type=sa.String(length=255), nullable=False)
    op.drop_column("employees", "is_active")
    op.drop_column("employees", "joined_at")
    op.drop_column("employees", "team_id")
    op.drop_column("employees", "department_id")
    op.drop_column("employees", "user_id")

    op.drop_index("idx_teams_department_id", table_name="teams")
    op.drop_constraint("fk_teams_department_id_departments", "teams", type_="foreignkey")
    op.drop_column("teams", "is_active")
    op.drop_column("teams", "department_id")

    op.drop_index("idx_departments_company_id", table_name="departments")
    op.drop_index("idx_departments_company_active", table_name="departments")
    op.drop_table("departments")
