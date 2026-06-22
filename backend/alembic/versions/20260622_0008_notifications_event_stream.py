"""add notification v1 and event stream fields

Revision ID: 20260622_0008
Revises: 20260622_0007
Create Date: 2026-06-22 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260622_0008"
down_revision: str | None = "20260622_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("events", sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("events", sa.Column("related_entity_type", sa.String(length=80), nullable=True))
    op.add_column("events", sa.Column("related_entity_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_events_actor_user_id_users", "events", "users", ["actor_user_id"], ["id"], ondelete="SET NULL")
    op.create_index("idx_events_actor_user_id", "events", ["actor_user_id"], unique=False)
    op.create_index("idx_events_related", "events", ["related_entity_type", "related_entity_id"], unique=False)
    op.create_index("idx_events_company_type_created_at", "events", ["company_id", "event_type", "created_at"], unique=False)

    op.add_column("notifications", sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("notifications", sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("notifications", sa.Column("actor_employee_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("notifications", sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("notifications", sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"))
    op.add_column("notifications", sa.Column("action_url", sa.String(length=255), nullable=True))
    op.add_column(
        "notifications",
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column("notifications", sa.Column("is_dismissed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("notifications", sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("notifications", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
    op.alter_column("notifications", "notification_type", existing_type=sa.String(length=80), type_=sa.String(length=120))
    op.alter_column("notifications", "recipient_employee_id", existing_type=postgresql.UUID(as_uuid=True), nullable=True)
    op.execute(
        """
        UPDATE notifications
        SET recipient_user_id = employees.user_id
        FROM employees
        WHERE notifications.recipient_employee_id = employees.id
        """
    )
    op.create_foreign_key("fk_notifications_recipient_user_id_users", "notifications", "users", ["recipient_user_id"], ["id"], ondelete="CASCADE")
    op.create_foreign_key("fk_notifications_actor_user_id_users", "notifications", "users", ["actor_user_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_notifications_actor_employee_id_employees", "notifications", "employees", ["actor_employee_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_notifications_event_id_events", "notifications", "events", ["event_id"], ["id"], ondelete="SET NULL")
    op.create_index("idx_notifications_recipient_user", "notifications", ["recipient_user_id", "is_read"], unique=False)
    op.create_index("idx_notifications_company_dismissed", "notifications", ["company_id", "is_dismissed", "created_at"], unique=False)
    op.create_index("idx_notifications_target", "notifications", ["related_entity_type", "related_entity_id"], unique=False)
    op.create_index("idx_notifications_event_id", "notifications", ["event_id"], unique=False)
    op.alter_column("notifications", "priority", server_default=None)
    op.alter_column("notifications", "metadata", server_default=None)
    op.alter_column("notifications", "is_dismissed", server_default=None)
    op.alter_column("notifications", "updated_at", server_default=None)


def downgrade() -> None:
    op.drop_index("idx_notifications_event_id", table_name="notifications")
    op.drop_index("idx_notifications_target", table_name="notifications")
    op.drop_index("idx_notifications_company_dismissed", table_name="notifications")
    op.drop_index("idx_notifications_recipient_user", table_name="notifications")
    op.drop_constraint("fk_notifications_event_id_events", "notifications", type_="foreignkey")
    op.drop_constraint("fk_notifications_actor_employee_id_employees", "notifications", type_="foreignkey")
    op.drop_constraint("fk_notifications_actor_user_id_users", "notifications", type_="foreignkey")
    op.drop_constraint("fk_notifications_recipient_user_id_users", "notifications", type_="foreignkey")
    op.execute("DELETE FROM notifications WHERE recipient_employee_id IS NULL")
    op.alter_column("notifications", "recipient_employee_id", existing_type=postgresql.UUID(as_uuid=True), nullable=False)
    op.alter_column("notifications", "notification_type", existing_type=sa.String(length=120), type_=sa.String(length=80))
    op.drop_column("notifications", "updated_at")
    op.drop_column("notifications", "dismissed_at")
    op.drop_column("notifications", "is_dismissed")
    op.drop_column("notifications", "metadata")
    op.drop_column("notifications", "action_url")
    op.drop_column("notifications", "priority")
    op.drop_column("notifications", "event_id")
    op.drop_column("notifications", "actor_employee_id")
    op.drop_column("notifications", "actor_user_id")
    op.drop_column("notifications", "recipient_user_id")

    op.drop_index("idx_events_company_type_created_at", table_name="events")
    op.drop_index("idx_events_related", table_name="events")
    op.drop_index("idx_events_actor_user_id", table_name="events")
    op.drop_constraint("fk_events_actor_user_id_users", "events", type_="foreignkey")
    op.drop_column("events", "related_entity_id")
    op.drop_column("events", "related_entity_type")
    op.drop_column("events", "actor_user_id")
