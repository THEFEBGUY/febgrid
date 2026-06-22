"""add file upload attachment metadata

Revision ID: 20260622_0007
Revises: 20260622_0006
Create Date: 2026-06-22 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260622_0007"
down_revision: str | None = "20260622_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("attachments", sa.Column("work_object_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("attachments", sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("attachments", sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("attachments", sa.Column("original_file_name", sa.String(length=255), nullable=False, server_default="uploaded-file"))
    op.add_column("attachments", sa.Column("storage_provider", sa.String(length=40), nullable=False, server_default="local"))
    op.add_column("attachments", sa.Column("storage_path", sa.Text(), nullable=False, server_default="uploads/legacy"))
    op.add_column("attachments", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("attachments", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.execute("UPDATE attachments SET original_file_name = file_name WHERE original_file_name = 'uploaded-file'")
    op.execute("UPDATE attachments SET storage_path = storage_url WHERE storage_path = 'uploads/legacy'")
    op.execute("UPDATE attachments SET work_object_id = linked_entity_id WHERE linked_entity_type = 'work_object'")
    op.create_foreign_key("fk_attachments_work_object_id_work_objects", "attachments", "work_objects", ["work_object_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_attachments_project_id_projects", "attachments", "projects", ["project_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_attachments_uploaded_by_user_id_users", "attachments", "users", ["uploaded_by_user_id"], ["id"], ondelete="SET NULL")
    op.create_index("idx_attachments_company_active", "attachments", ["company_id", "is_active"], unique=False)
    op.create_index("idx_attachments_work_object_id", "attachments", ["work_object_id"], unique=False)
    op.create_index("idx_attachments_project_id", "attachments", ["project_id"], unique=False)
    op.create_index("idx_attachments_uploaded_by_user_id", "attachments", ["uploaded_by_user_id"], unique=False)
    op.alter_column("attachments", "original_file_name", server_default=None)
    op.alter_column("attachments", "storage_provider", server_default=None)
    op.alter_column("attachments", "storage_path", server_default=None)
    op.alter_column("attachments", "storage_url", existing_type=sa.Text(), nullable=True)
    op.alter_column("attachments", "is_active", server_default=None)


def downgrade() -> None:
    op.execute("UPDATE attachments SET storage_url = storage_path WHERE storage_url IS NULL")
    op.alter_column("attachments", "storage_url", existing_type=sa.Text(), nullable=False)
    op.drop_index("idx_attachments_uploaded_by_user_id", table_name="attachments")
    op.drop_index("idx_attachments_project_id", table_name="attachments")
    op.drop_index("idx_attachments_work_object_id", table_name="attachments")
    op.drop_index("idx_attachments_company_active", table_name="attachments")
    op.drop_constraint("fk_attachments_uploaded_by_user_id_users", "attachments", type_="foreignkey")
    op.drop_constraint("fk_attachments_project_id_projects", "attachments", type_="foreignkey")
    op.drop_constraint("fk_attachments_work_object_id_work_objects", "attachments", type_="foreignkey")
    op.drop_column("attachments", "is_active")
    op.drop_column("attachments", "description")
    op.drop_column("attachments", "storage_path")
    op.drop_column("attachments", "storage_provider")
    op.drop_column("attachments", "original_file_name")
    op.drop_column("attachments", "uploaded_by_user_id")
    op.drop_column("attachments", "project_id")
    op.drop_column("attachments", "work_object_id")
