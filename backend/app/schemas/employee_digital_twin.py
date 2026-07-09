from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, Field, field_validator

from app.schemas.common import FebGridModel, Timestamped

EMPLOYEE_TWIN_PERIODS = {7, 30, 90}
EMPLOYEE_TWIN_WORKLOAD_LEVELS = {"light", "balanced", "elevated", "overloaded", "unknown"}


def safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


class EmployeeDigitalTwinSnapshotRead(Timestamped):
    id: UUID
    company_id: UUID
    employee_id: UUID
    generated_by_user_id: UUID | None = None
    period_days: int
    period_start: datetime
    period_end: datetime
    workload_level: str
    summary: str
    profile: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("profile_json", "profile"),
        serialization_alias="profile",
    )
    work_metrics: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("work_metrics_json", "work_metrics"),
        serialization_alias="work_metrics",
    )
    project_metrics: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("project_metrics_json", "project_metrics"),
        serialization_alias="project_metrics",
    )
    availability: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("availability_json", "availability"),
        serialization_alias="availability",
    )
    skills: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("skills_json", "skills"),
        serialization_alias="skills",
    )
    strengths: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("strengths_json", "strengths"),
        serialization_alias="strengths",
    )
    attention_areas: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("attention_areas_json", "attention_areas"),
        serialization_alias="attention_areas",
    )
    risks: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("risks_json", "risks"),
        serialization_alias="risks",
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("recommended_actions_json", "recommended_actions"),
        serialization_alias="recommended_actions",
    )
    source_counts: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("source_counts_json", "source_counts"),
        serialization_alias="source_counts",
    )
    data_coverage: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("data_coverage_json", "data_coverage"),
        serialization_alias="data_coverage",
    )
    limitations: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("limitations_json", "limitations"),
        serialization_alias="limitations",
    )
    is_rule_based: bool = True
    ai_narrative_used: bool = False
    ai_job_id: UUID | None = None
    provider_mode: str | None = None
    provider_key: str | None = None
    model_name: str | None = None
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )

    @field_validator(
        "profile",
        "work_metrics",
        "project_metrics",
        "availability",
        "source_counts",
        "data_coverage",
        "metadata",
        mode="before",
    )
    @classmethod
    def ensure_dicts(cls, value: Any) -> dict[str, Any]:
        return safe_dict(value)

    @field_validator("skills", "strengths", "attention_areas", "risks", "recommended_actions", "limitations", mode="before")
    @classmethod
    def ensure_lists(cls, value: Any) -> list[str]:
        return safe_list(value)


class EmployeeDigitalTwinSignalsRead(FebGridModel):
    company_id: UUID
    employee_id: UUID
    period_days: int
    period_start: datetime
    period_end: datetime
    workload_level: str
    summary: str
    profile: dict[str, Any] = Field(default_factory=dict)
    work_metrics: dict[str, Any] = Field(default_factory=dict)
    project_metrics: dict[str, Any] = Field(default_factory=dict)
    availability: dict[str, Any] = Field(default_factory=dict)
    skills: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    attention_areas: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    source_counts: dict[str, Any] = Field(default_factory=dict)
    data_coverage: dict[str, Any] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    is_rule_based: bool = True
    ai_narrative_used: bool = False
    generated_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
