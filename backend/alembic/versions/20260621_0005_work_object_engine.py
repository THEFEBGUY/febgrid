"""add work object engine foundation

Revision ID: 20260621_0005
Revises: 20260621_0004
Create Date: 2026-06-21 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260621_0005"
down_revision: str | None = "20260621_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("work_objects", sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("work_objects", sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("work_objects", sa.Column("creator_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("work_objects", sa.Column("start_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("work_objects", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "work_objects",
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column("work_objects", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_foreign_key("fk_work_objects_department_id_departments", "work_objects", "departments", ["department_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_work_objects_team_id_teams", "work_objects", "teams", ["team_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_work_objects_creator_user_id_users", "work_objects", "users", ["creator_user_id"], ["id"], ondelete="SET NULL")
    op.create_index("idx_work_objects_department_id", "work_objects", ["department_id"], unique=False)
    op.create_index("idx_work_objects_team_id", "work_objects", ["team_id"], unique=False)
    op.create_index("idx_work_objects_creator_user_id", "work_objects", ["creator_user_id"], unique=False)
    op.create_index("idx_work_objects_company_active", "work_objects", ["company_id", "is_active"], unique=False)
    op.alter_column("work_objects", "metadata", server_default=None)
    op.alter_column("work_objects", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_work_objects_company_active", table_name="work_objects")
    op.drop_index("idx_work_objects_creator_user_id", table_name="work_objects")
    op.drop_index("idx_work_objects_team_id", table_name="work_objects")
    op.drop_index("idx_work_objects_department_id", table_name="work_objects")
    op.drop_constraint("fk_work_objects_creator_user_id_users", "work_objects", type_="foreignkey")
    op.drop_constraint("fk_work_objects_team_id_teams", "work_objects", type_="foreignkey")
    op.drop_constraint("fk_work_objects_department_id_departments", "work_objects", type_="foreignkey")
    op.drop_column("work_objects", "is_active")
    op.drop_column("work_objects", "metadata")
    op.drop_column("work_objects", "completed_at")
    op.drop_column("work_objects", "start_date")
    op.drop_column("work_objects", "creator_user_id")
    op.drop_column("work_objects", "team_id")
    op.drop_column("work_objects", "department_id")
