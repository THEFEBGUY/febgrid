from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, json_dict, utc_now, uuid_pk


class Comment(TimestampMixin, Base):
    __tablename__ = "comments"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    author_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
    )
    target_entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    parent_comment_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="SET NULL"),
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json = json_dict(name="metadata")
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    company = relationship("Company")
    author_user = relationship("User", foreign_keys=[author_user_id])
    author = relationship("Employee", foreign_keys=[author_employee_id])
    parent_comment = relationship("Comment", remote_side=[id])
    mentions = relationship("CommentMention", back_populates="comment", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_comments_company_target", "company_id", "target_entity_type", "target_entity_id"),
        Index("idx_comments_company_archived_created", "company_id", "is_archived", "created_at"),
        Index("idx_comments_parent_comment_id", "parent_comment_id"),
        Index("idx_comments_author_user_id", "author_user_id"),
        Index("idx_comments_author_employee_id", "author_employee_id"),
    )


class CommentMention(Base):
    __tablename__ = "comment_mentions"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    comment_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
    )
    mentioned_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    mentioned_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    company = relationship("Company")
    comment = relationship("Comment", back_populates="mentions")
    mentioned_user = relationship("User", foreign_keys=[mentioned_user_id])
    mentioned_employee = relationship("Employee", foreign_keys=[mentioned_employee_id])

    __table_args__ = (
        Index("idx_comment_mentions_company_id", "company_id"),
        Index("idx_comment_mentions_comment_id", "comment_id"),
        Index("idx_comment_mentions_employee_id", "mentioned_employee_id"),
        Index("idx_comment_mentions_user_id", "mentioned_user_id"),
    )


class Announcement(TimestampMixin, Base):
    __tablename__ = "announcements"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)
    metadata_json = json_dict(name="metadata")
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    company = relationship("Company")
    author_user = relationship("User", foreign_keys=[author_user_id])

    __table_args__ = (
        Index("idx_announcements_company_published", "company_id", "is_published", "published_at"),
        Index("idx_announcements_company_archived", "company_id", "is_archived", "created_at"),
        Index("idx_announcements_author_user_id", "author_user_id"),
    )
