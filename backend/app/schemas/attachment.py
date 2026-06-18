from typing import Any
from uuid import UUID

from pydantic import AliasChoices, Field

from app.schemas.common import FebGridModel, Timestamped


class AttachmentBase(FebGridModel):
    company_id: UUID
    uploaded_by_employee_id: UUID | None = None
    linked_entity_type: str = Field(min_length=1, max_length=80)
    linked_entity_id: UUID
    file_name: str = Field(min_length=1, max_length=255)
    file_type: str | None = Field(default=None, max_length=120)
    file_size: int | None = Field(default=None, ge=0)
    storage_url: str = Field(min_length=1)
    ai_processing_status: str = Field(default="pending", max_length=40)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata", "metadata_json"),
        serialization_alias="metadata",
    )


class AttachmentCreate(AttachmentBase):
    pass


class WorkObjectAttachmentCreate(FebGridModel):
    company_id: UUID
    uploaded_by_employee_id: UUID | None = None
    file_name: str = Field(min_length=1, max_length=255)
    file_type: str | None = Field(default=None, max_length=120)
    file_size: int | None = Field(default=None, ge=0)
    storage_url: str = Field(min_length=1)
    ai_processing_status: str = Field(default="pending", max_length=40)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata", "metadata_json"),
        serialization_alias="metadata",
    )


class AttachmentUpdate(FebGridModel):
    file_name: str | None = Field(default=None, min_length=1, max_length=255)
    file_type: str | None = Field(default=None, max_length=120)
    file_size: int | None = Field(default=None, ge=0)
    storage_url: str | None = Field(default=None, min_length=1)
    ai_processing_status: str | None = Field(default=None, max_length=40)
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata", "metadata_json"),
        serialization_alias="metadata",
    )


class AttachmentRead(AttachmentBase, Timestamped):
    id: UUID
