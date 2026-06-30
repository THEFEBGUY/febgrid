from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import AliasChoices, Field, field_validator, model_validator

from app.schemas.common import FebGridModel, Timestamped

AI_JOB_TYPES = {
    "work_object_summary_mock",
    "project_summary_mock",
    "employee_workload_mock",
    "file_summary_mock",
    "company_brief_mock",
}
AI_JOB_STATUSES = {"queued", "running", "succeeded", "failed", "cancelled", "skipped"}
AI_JOB_PRIORITIES = {"low", "normal", "high", "urgent"}

ProviderMode = Literal["mock", "disabled", "future_external"]


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
    provider_mode: ProviderMode = "mock"
    real_ai_connected: bool = False
    external_calls_enabled: bool = False
    capabilities: list[AICapability]
    message: str
