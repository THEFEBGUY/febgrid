from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, Field

from app.schemas.common import FebGridModel


class EventBase(FebGridModel):
    company_id: UUID
    actor_employee_id: UUID | None = None
    target_entity_type: str | None = Field(default=None, max_length=80)
    target_entity_id: UUID | None = None
    event_type: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=220)
    description: str | None = None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata", "metadata_json"),
        serialization_alias="metadata",
    )


class EventCreate(EventBase):
    pass


class EventRead(EventBase):
    id: UUID
    created_at: datetime
