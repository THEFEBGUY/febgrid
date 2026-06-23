"""add phase 1 communication layer

Revision ID: 20260623_0009
Revises: 20260622_0008
Create Date: 2026-06-23 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260623_0009"
down_revision: str | None = "20260622_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("author_employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_entity_type", sa.String(length=80), nullable=False),
        sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_comment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_edited", sa.Boolean(), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_employee_id"], ["employees.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_comment_id"], ["comments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_comments_company_target", "comments", ["company_id", "target_entity_type", "target_entity_id"], unique=False)
    op.create_index("idx_comments_company_archived_created", "comments", ["company_id", "is_archived", "created_at"], unique=False)
    op.create_index("idx_comments_parent_comment_id", "comments", ["parent_comment_id"], unique=False)
    op.create_index("idx_comments_author_user_id", "comments", ["author_user_id"], unique=False)
    op.create_index("idx_comments_author_employee_id", "comments", ["author_employee_id"], unique=False)

    op.create_table(
        "comment_mentions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("mentioned_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("mentioned_employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["mentioned_employee_id"], ["employees.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["mentioned_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_comment_mentions_company_id", "comment_mentions", ["company_id"], unique=False)
    op.create_index("idx_comment_mentions_comment_id", "comment_mentions", ["comment_id"], unique=False)
    op.create_index("idx_comment_mentions_employee_id", "comment_mentions", ["mentioned_employee_id"], unique=False)
    op.create_index("idx_comment_mentions_user_id", "comment_mentions", ["mentioned_user_id"], unique=False)

    op.create_table(
        "announcements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_announcements_company_published", "announcements", ["company_id", "is_published", "published_at"], unique=False)
    op.create_index("idx_announcements_company_archived", "announcements", ["company_id", "is_archived", "created_at"], unique=False)
    op.create_index("idx_announcements_author_user_id", "announcements", ["author_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_announcements_author_user_id", table_name="announcements")
    op.drop_index("idx_announcements_company_archived", table_name="announcements")
    op.drop_index("idx_announcements_company_published", table_name="announcements")
    op.drop_table("announcements")

    op.drop_index("idx_comment_mentions_user_id", table_name="comment_mentions")
    op.drop_index("idx_comment_mentions_employee_id", table_name="comment_mentions")
    op.drop_index("idx_comment_mentions_comment_id", table_name="comment_mentions")
    op.drop_index("idx_comment_mentions_company_id", table_name="comment_mentions")
    op.drop_table("comment_mentions")

    op.drop_index("idx_comments_author_employee_id", table_name="comments")
    op.drop_index("idx_comments_author_user_id", table_name="comments")
    op.drop_index("idx_comments_parent_comment_id", table_name="comments")
    op.drop_index("idx_comments_company_archived_created", table_name="comments")
    op.drop_index("idx_comments_company_target", table_name="comments")
    op.drop_table("comments")
