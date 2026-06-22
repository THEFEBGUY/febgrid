from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, Field, field_validator

from app.schemas.common import FebGridModel, Timestamped

NOTIFICATION_PRIORITIES = {"low", "normal", "high", "urgent"}


class NotificationBase(FebGridModel):
    company_id: UUID
    recipient_user_id: UUID | None = None
    recipient_employee_id: UUID | None = None
    actor_user_id: UUID | None = None
    actor_employee_id: UUID | None = None
    event_id: UUID | None = None
    target_entity_type: str | None = Field(
        default=None,
        max_length=80,
        validation_alias=AliasChoices("target_entity_type", "related_entity_type"),
        serialization_alias="target_entity_type",
    )
    target_entity_id: UUID | None = Field(
        default=None,
        validation_alias=AliasChoices("target_entity_id", "related_entity_id"),
        serialization_alias="target_entity_id",
    )
    notification_type: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=180)
    message: str = Field(min_length=1)
    priority: str = Field(default="normal", max_length=20)
    action_url: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )

    @field_validator("priority")
    @classmethod
    def ensure_priority(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in NOTIFICATION_PRIORITIES:
            raise ValueError("Invalid notification priority")
        return normalized

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_metadata_dict(cls, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {}


class NotificationCreate(NotificationBase):
    company_wide: bool = False


class NotificationRead(NotificationBase, Timestamped):
    id: UUID
    is_read: bool
    read_at: datetime | None
    is_dismissed: bool
    dismissed_at: datetime | None


class NotificationReadUpdate(FebGridModel):
    company_id: UUID
    recipient_user_id: UUID | None = None
    recipient_employee_id: UUID | None = None


class NotificationUnreadCount(FebGridModel):
    company_id: UUID
    unread_count: int
