from typing import Any
from datetime import datetime
from uuid import UUID

from pydantic import AliasChoices, Field, field_validator

from app.schemas.common import FebGridModel, Timestamped


class AttachmentBase(FebGridModel):
    company_id: UUID
    work_object_id: UUID | None = None
    project_id: UUID | None = None
    uploaded_by_user_id: UUID | None = None
    uploaded_by_employee_id: UUID | None = None
    linked_entity_type: str = Field(default="work_object", min_length=1, max_length=80)
    linked_entity_id: UUID
    file_name: str = Field(min_length=1, max_length=255)
    original_file_name: str = Field(min_length=1, max_length=255)
    content_type: str | None = Field(
        default=None,
        max_length=120,
        validation_alias=AliasChoices("content_type", "file_type"),
        serialization_alias="content_type",
    )
    file_size: int | None = Field(default=None, ge=0)
    extension: str | None = Field(default=None, max_length=20)
    checksum_sha256: str | None = Field(default=None, max_length=128)
    storage_provider: str = Field(default="local", max_length=40)
    storage_path: str = Field(min_length=1)
    public_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("public_url", "storage_url"),
        serialization_alias="public_url",
    )
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    processing_status: str = Field(default="uploaded", max_length=40)
    scan_status: str = Field(default="not_scanned", max_length=40)
    ai_processing_status: str = Field(default="pending", max_length=40)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )
    is_active: bool = True
    is_deleted: bool = False

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_metadata_dict(cls, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {}


class AttachmentCreate(AttachmentBase):
    pass


class WorkObjectAttachmentCreate(FebGridModel):
    company_id: UUID
    uploaded_by_employee_id: UUID | None = None
    file_name: str = Field(min_length=1, max_length=255)
    original_file_name: str | None = Field(default=None, min_length=1, max_length=255)
    content_type: str | None = Field(
        default=None,
        max_length=120,
        validation_alias=AliasChoices("content_type", "file_type"),
        serialization_alias="content_type",
    )
    file_size: int | None = Field(default=None, ge=0)
    extension: str | None = Field(default=None, max_length=20)
    checksum_sha256: str | None = Field(default=None, max_length=128)
    storage_provider: str = Field(default="local", max_length=40)
    storage_path: str = Field(min_length=1)
    public_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("public_url", "storage_url"),
        serialization_alias="public_url",
    )
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    processing_status: str = Field(default="uploaded", max_length=40)
    scan_status: str = Field(default="not_scanned", max_length=40)
    ai_processing_status: str = Field(default="pending", max_length=40)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )


class AttachmentUpdate(FebGridModel):
    description: str | None = None
    tags: list[str] | None = None
    processing_status: str | None = Field(default=None, max_length=40)
    scan_status: str | None = Field(default=None, max_length=40)
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata", "metadata_json"),
        serialization_alias="metadata",
    )

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_optional_metadata_dict(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        return {}


class AttachmentRead(AttachmentBase, Timestamped):
    id: UUID
    archived_at: datetime | None = None
    deleted_at: datetime | None = None
