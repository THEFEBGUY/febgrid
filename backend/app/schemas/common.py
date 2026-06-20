from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator


class FebGridModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MetadataField(FebGridModel):
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


class Timestamped(FebGridModel):
    created_at: datetime
    updated_at: datetime


class IDModel(FebGridModel):
    id: UUID
