from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, Field, field_validator

from app.schemas.common import FebGridModel, Timestamped

COMMENT_TARGET_TYPES = {"work_object", "project"}
ANNOUNCEMENT_PRIORITIES = {"low", "normal", "high", "urgent"}


class MetadataMixin(FebGridModel):
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_metadata_dict(cls, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {}


class CommentMentionRead(FebGridModel):
    id: UUID
    company_id: UUID
    comment_id: UUID
    mentioned_user_id: UUID | None = None
    mentioned_employee_id: UUID | None = None
    created_at: datetime


class CommentBase(MetadataMixin):
    company_id: UUID
    target_entity_type: str = Field(min_length=1, max_length=80)
    target_entity_id: UUID
    parent_comment_id: UUID | None = None
    body: str = Field(min_length=1)
    mentioned_user_ids: list[UUID] = Field(default_factory=list)
    mentioned_employee_ids: list[UUID] = Field(default_factory=list)

    @field_validator("target_entity_type")
    @classmethod
    def ensure_target_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in COMMENT_TARGET_TYPES:
            raise ValueError("Invalid comment target")
        return normalized


class CommentCreate(CommentBase):
    author_employee_id: UUID | None = None


class CommentUpdate(MetadataMixin):
    body: str | None = Field(default=None, min_length=1)
    mentioned_user_ids: list[UUID] | None = None
    mentioned_employee_ids: list[UUID] | None = None


class CommentRead(MetadataMixin, Timestamped):
    id: UUID
    company_id: UUID
    author_user_id: UUID | None = None
    author_employee_id: UUID | None = None
    target_entity_type: str
    target_entity_id: UUID
    parent_comment_id: UUID | None = None
    body: str
    is_edited: bool
    edited_at: datetime | None = None
    is_archived: bool
    mentions: list[CommentMentionRead] = Field(default_factory=list)


class AnnouncementBase(MetadataMixin):
    company_id: UUID
    title: str = Field(min_length=1, max_length=180)
    body: str = Field(min_length=1)
    priority: str = Field(default="normal", max_length=20)
    is_published: bool = True

    @field_validator("priority")
    @classmethod
    def ensure_priority(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ANNOUNCEMENT_PRIORITIES:
            raise ValueError("Invalid announcement priority")
        return normalized


class AnnouncementCreate(AnnouncementBase):
    pass


class AnnouncementUpdate(MetadataMixin):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    body: str | None = Field(default=None, min_length=1)
    priority: str | None = Field(default=None, max_length=20)
    is_published: bool | None = None

    @field_validator("priority")
    @classmethod
    def ensure_optional_priority(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in ANNOUNCEMENT_PRIORITIES:
            raise ValueError("Invalid announcement priority")
        return normalized


class AnnouncementRead(MetadataMixin, Timestamped):
    id: UUID
    company_id: UUID
    author_user_id: UUID | None = None
    title: str
    body: str
    priority: str
    is_published: bool
    published_at: datetime | None = None
    is_archived: bool
