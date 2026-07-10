from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, Field, field_validator

from app.schemas.common import FebGridModel, Timestamped

MEMORY_TYPES = {
    "decision",
    "policy",
    "process",
    "project_context",
    "work_context",
    "file_insight",
    "company_brief",
    "risk",
    "customer_note",
    "operational_fact",
    "general_note",
}

SCOPE_TYPES = {"company", "project", "work_object", "team", "department", "file", "employee_self", "unknown"}
SOURCE_TYPES = {
    "ai_job",
    "work_object",
    "project",
    "attachment",
    "file",
    "company_brief",
    "work_object_summary",
    "project_summary",
    "file_summary",
    "document_analysis",
    "image_analysis",
    "audio_transcription",
    "work_dna",
    "employee_digital_twin",
    "event",
    "manual",
}
MEMORY_STATUSES = {"draft", "suggested", "approved", "rejected", "archived"}
MEMORY_VISIBILITIES = {"owner_admin", "manager_hr", "team", "project_members", "employee_self", "company"}
MEMORY_IMPORTANCE = {"low", "normal", "high", "critical"}


def safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def normalize_choice(value: str, allowed: set[str], label: str) -> str:
    normalized = value.strip().lower()
    if normalized not in allowed:
        raise ValueError(f"Invalid {label}")
    return normalized


class CompanyMemoryBase(FebGridModel):
    company_id: UUID
    title: str = Field(min_length=1, max_length=180)
    memory_type: str = "general_note"
    scope_type: str = "company"
    scope_id: UUID | None = None
    source_type: str | None = None
    source_id: UUID | None = None
    source_ai_job_id: UUID | None = None
    content: str = Field(min_length=1)
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    importance: str = "normal"
    confidence: float | None = Field(default=None, ge=0, le=1)
    status: str = "draft"
    visibility: str = "owner_admin"
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )

    @field_validator("memory_type")
    @classmethod
    def validate_memory_type(cls, value: str) -> str:
        return normalize_choice(value, MEMORY_TYPES, "memory type")

    @field_validator("scope_type")
    @classmethod
    def validate_scope_type(cls, value: str) -> str:
        return normalize_choice(value, SCOPE_TYPES, "scope type")

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_choice(value, SOURCE_TYPES, "source type")

    @field_validator("importance")
    @classmethod
    def validate_importance(cls, value: str) -> str:
        return normalize_choice(value, MEMORY_IMPORTANCE, "importance")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        return normalize_choice(value, MEMORY_STATUSES, "status")

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, value: str) -> str:
        return normalize_choice(value, MEMORY_VISIBILITIES, "visibility")

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_metadata_dict(cls, value: Any) -> dict[str, Any]:
        return safe_dict(value)

    @field_validator("tags", mode="before")
    @classmethod
    def ensure_tags(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()][:12]


class CompanyMemoryCreate(CompanyMemoryBase):
    pass


class CompanyMemoryUpdate(FebGridModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    memory_type: str | None = None
    scope_type: str | None = None
    scope_id: UUID | None = None
    content: str | None = Field(default=None, min_length=1)
    summary: str | None = None
    tags: list[str] | None = None
    importance: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    visibility: str | None = None
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )

    @field_validator("memory_type")
    @classmethod
    def validate_optional_memory_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_choice(value, MEMORY_TYPES, "memory type")

    @field_validator("scope_type")
    @classmethod
    def validate_optional_scope_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_choice(value, SCOPE_TYPES, "scope type")

    @field_validator("importance")
    @classmethod
    def validate_optional_importance(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_choice(value, MEMORY_IMPORTANCE, "importance")

    @field_validator("visibility")
    @classmethod
    def validate_optional_visibility(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_choice(value, MEMORY_VISIBILITIES, "visibility")

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_optional_metadata_dict(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        return safe_dict(value)

    @field_validator("tags", mode="before")
    @classmethod
    def ensure_optional_tags(cls, value: Any) -> list[str] | None:
        if value is None:
            return None
        if not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()][:12]


class CompanyMemoryFromAIJobPayload(FebGridModel):
    company_id: UUID
    title: str | None = Field(default=None, max_length=180)
    memory_type: str | None = None
    importance: str = "normal"
    visibility: str = "owner_admin"
    approve_now: bool = False
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("memory_type")
    @classmethod
    def validate_optional_memory_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_choice(value, MEMORY_TYPES, "memory type")

    @field_validator("importance")
    @classmethod
    def validate_importance(cls, value: str) -> str:
        return normalize_choice(value, MEMORY_IMPORTANCE, "importance")

    @field_validator("visibility")
    @classmethod
    def validate_visibility(cls, value: str) -> str:
        return normalize_choice(value, MEMORY_VISIBILITIES, "visibility")

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_metadata_dict(cls, value: Any) -> dict[str, Any]:
        return safe_dict(value)

    @field_validator("tags", mode="before")
    @classmethod
    def ensure_tags(cls, value: Any) -> list[str]:
        if value is None or not isinstance(value, list):
            return []
        return [str(item).strip() for item in value if str(item).strip()][:12]


class CompanyMemoryActionPayload(FebGridModel):
    company_id: UUID
    note: str | None = None


class CompanyMemoryRead(CompanyMemoryBase, Timestamped):
    id: UUID
    created_by_user_id: UUID | None = None
    created_by_employee_id: UUID | None = None
    approved_by_user_id: UUID | None = None
    approved_at: datetime | None = None
    rejected_by_user_id: UUID | None = None
    rejected_at: datetime | None = None
    archived_by_user_id: UUID | None = None
    archived_at: datetime | None = None
    last_used_at: datetime | None = None
