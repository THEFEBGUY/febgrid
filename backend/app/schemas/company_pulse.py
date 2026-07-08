from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, Field, field_validator

from app.schemas.common import FebGridModel, Timestamped

PULSE_STATUSES = {"excellent", "healthy", "watch", "at_risk", "critical"}
PULSE_TRENDS = {"improving", "stable", "declining", "unknown"}
PULSE_SECTION_KEYS = {
    "work_health",
    "project_health",
    "people_health",
    "leave_health",
    "communication_health",
    "ai_system_health",
    "memory_health",
}


def safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


class CompanyPulseSnapshotRead(Timestamped):
    id: UUID
    company_id: UUID
    overall_score: int = Field(ge=0, le=100)
    pulse_status: str
    trend: str
    summary: str
    section_scores: dict[str, int] = Field(default_factory=dict)
    key_signals: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    source_counts: dict[str, Any] = Field(default_factory=dict)
    generated_by_user_id: UUID | None = None
    generated_by_ai_job_id: UUID | None = None
    is_rule_based: bool = True
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )

    @field_validator("section_scores", "source_counts", "metadata", mode="before")
    @classmethod
    def ensure_dicts(cls, value: Any) -> dict[str, Any]:
        return safe_dict(value)

    @field_validator("key_signals", "risks", "recommended_actions", mode="before")
    @classmethod
    def ensure_lists(cls, value: Any) -> list[str]:
        return safe_list(value)


class CompanyPulseSignalsRead(FebGridModel):
    company_id: UUID
    overall_score: int = Field(ge=0, le=100)
    pulse_status: str
    trend: str = "unknown"
    summary: str
    section_scores: dict[str, int] = Field(default_factory=dict)
    key_signals: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    source_counts: dict[str, Any] = Field(default_factory=dict)
    generated_at: datetime
    is_rule_based: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
