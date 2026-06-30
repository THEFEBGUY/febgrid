from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AliasChoices, Field, field_validator, model_validator

from app.schemas.common import FebGridModel, Timestamped

MOCK_AI_JOB_TYPES = {
    "work_object_summary_mock",
    "project_summary_mock",
    "employee_workload_mock",
    "file_summary_mock",
    "company_brief_mock",
}
REAL_AI_JOB_TYPES = {
    "work_object_summary_safe",
    "project_summary_safe",
    "company_brief_safe",
}
AI_JOB_TYPES = MOCK_AI_JOB_TYPES | REAL_AI_JOB_TYPES
AI_JOB_STATUSES = {"queued", "running", "succeeded", "failed", "cancelled", "skipped"}
AI_JOB_PRIORITIES = {"low", "normal", "high", "urgent"}

ProviderMode = Literal["disabled", "mock", "groq", "openai_future", "custom_openai_compatible_future"]


def ensure_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


class AIJobCreate(FebGridModel):
    company_id: UUID
    job_type: str = Field(min_length=1, max_length=100)
    priority: str = Field(default="normal", max_length=40)
    input_entity_type: str | None = Field(default=None, max_length=80)
    input_entity_id: UUID | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    max_attempts: int = Field(default=1, ge=1, le=3)
    scheduled_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("job_type")
    @classmethod
    def validate_job_type(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in AI_JOB_TYPES:
            raise ValueError("Invalid AI job type")
        return normalized

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in AI_JOB_PRIORITIES:
            raise ValueError("Invalid AI job priority")
        return normalized

    @field_validator("input_payload", "metadata", mode="before")
    @classmethod
    def ensure_payload_dict(cls, value: Any) -> dict[str, Any]:
        return ensure_dict(value)

    @model_validator(mode="after")
    def validate_entity_pair(self) -> "AIJobCreate":
        if (self.input_entity_type is None) != (self.input_entity_id is None):
            raise ValueError("input_entity_type and input_entity_id must be provided together")
        return self


class AIJobRead(Timestamped):
    id: UUID
    company_id: UUID
    requested_by_user_id: UUID | None = None
    requested_by_employee_id: UUID | None = None
    job_type: str
    status: str
    priority: str
    input_entity_type: str | None = None
    input_entity_id: UUID | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_payload: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    provider_key: str
    provider_mode: ProviderMode | str
    attempts: int
    max_attempts: int
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    cancelled_at: datetime | None = None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )

    @field_validator("input_payload", "output_payload", "metadata", mode="before")
    @classmethod
    def ensure_json_dict(cls, value: Any) -> dict[str, Any]:
        return ensure_dict(value)


class AICapability(FebGridModel):
    job_type: str
    label: str
    description: str
    mock_only: bool = True


class AICapabilitiesRead(FebGridModel):
    company_id: UUID
    provider_key: str = "mock"
    provider_mode: ProviderMode | str = "mock"
    real_ai_connected: bool = False
    external_calls_enabled: bool = False
    capabilities: list[AICapability]
    message: str


class AIProviderStatusRead(FebGridModel):
    company_id: UUID
    provider_key: str
    provider_mode: ProviderMode | str
    configured: bool
    model_name: str | None = None
    external_processing_enabled: bool
    external_processing_allowed: bool
    ai_enabled: bool
    real_ai_connected: bool
    supported_real_job_types: list[str] = Field(default_factory=list)
    supported_mock_job_types: list[str] = Field(default_factory=list)
    message: str


class AISafetySettingsRead(FebGridModel):
    company_id: UUID
    ai_enabled: bool
    external_ai_processing_allowed: bool
    default_provider_mode: ProviderMode | str
    allowed_ai_job_types: list[str] = Field(default_factory=list)
    max_monthly_ai_jobs: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_settings_metadata_dict(cls, value: Any) -> dict[str, Any]:
        return ensure_dict(value)


class AISafetySettingsUpdate(FebGridModel):
    ai_enabled: bool | None = None
    external_ai_processing_allowed: bool | None = None
    default_provider_mode: ProviderMode | str | None = None
    allowed_ai_job_types: list[str] | None = None
    max_monthly_ai_jobs: int | None = Field(default=None, ge=1, le=100_000)
    metadata: dict[str, Any] | None = None

    @field_validator("default_provider_mode")
    @classmethod
    def validate_provider_mode(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        valid_modes = {"disabled", "mock", "groq", "openai_future", "custom_openai_compatible_future"}
        if normalized not in valid_modes:
            raise ValueError("Invalid AI provider mode")
        return normalized

    @field_validator("allowed_ai_job_types")
    @classmethod
    def validate_allowed_job_types(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = sorted({item.strip() for item in value if item.strip()})
        invalid = [item for item in normalized if item not in AI_JOB_TYPES]
        if invalid:
            raise ValueError("Invalid AI job type in allowlist")
        return normalized

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_update_metadata_dict(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        return ensure_dict(value)
