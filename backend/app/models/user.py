from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, uuid_pk


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(40), default="employee", nullable=False)
    auth_provider: Mapped[str] = mapped_column(String(40), default="local", nullable=False)
    supabase_user_id: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    company = relationship("Company", back_populates="users")

    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("supabase_user_id", name="uq_users_supabase_user_id"),
        Index("idx_users_company_id", "company_id"),
        Index("idx_users_company_role", "company_id", "role"),
    )
