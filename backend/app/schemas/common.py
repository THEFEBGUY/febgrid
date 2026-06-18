from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class FebGridModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MetadataField(FebGridModel):
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata", "metadata_json"),
        serialization_alias="metadata",
    )


class Timestamped(FebGridModel):
    created_at: datetime
    updated_at: datetime


class IDModel(FebGridModel):
    id: UUID
