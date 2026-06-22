from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, Field, field_validator

from app.schemas.common import FebGridModel


class EventBase(FebGridModel):
    company_id: UUID
    actor_user_id: UUID | None = None
    actor_employee_id: UUID | None = None
    target_entity_type: str | None = Field(default=None, max_length=80)
    target_entity_id: UUID | None = None
    related_entity_type: str | None = Field(default=None, max_length=80)
    related_entity_id: UUID | None = None
    event_type: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=220)
    description: str | None = None
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


class EventCreate(EventBase):
    pass


class EventRead(EventBase):
    id: UUID
    created_at: datetime
