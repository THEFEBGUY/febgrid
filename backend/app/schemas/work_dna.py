from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, Field, field_validator

from app.schemas.common import FebGridModel, Timestamped

WORK_DNA_PERIODS = {7, 30, 90}
WORK_DNA_SCOPE_TYPES = {"company", "project", "department", "team"}


def safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


class WorkDNASnapshotRead(Timestamped):
    id: UUID
    company_id: UUID
    scope_type: str
    scope_id: UUID | None = None
    generated_by_user_id: UUID | None = None
    period_days: int
    period_start: datetime
    period_end: datetime
    overall_summary: str
    work_volume: dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("work_volume_json", "work_volume"), serialization_alias="work_volume")
    work_type_distribution: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("work_type_distribution_json", "work_type_distribution"), serialization_alias="work_type_distribution")
    status_distribution: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("status_distribution_json", "status_distribution"), serialization_alias="status_distribution")
    priority_distribution: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("priority_distribution_json", "priority_distribution"), serialization_alias="priority_distribution")
    completion_patterns: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("completion_patterns_json", "completion_patterns"), serialization_alias="completion_patterns")
    overdue_patterns: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("overdue_patterns_json", "overdue_patterns"), serialization_alias="overdue_patterns")
    blocked_patterns: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("blocked_patterns_json", "blocked_patterns"), serialization_alias="blocked_patterns")
    workflow_patterns: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("workflow_patterns_json", "workflow_patterns"), serialization_alias="workflow_patterns")
    project_patterns: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("project_patterns_json", "project_patterns"), serialization_alias="project_patterns")
    department_patterns: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("department_patterns_json", "department_patterns"), serialization_alias="department_patterns")
    team_patterns: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("team_patterns_json", "team_patterns"), serialization_alias="team_patterns")
    tag_patterns: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("tag_patterns_json", "tag_patterns"), serialization_alias="tag_patterns")
    recurring_patterns: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("recurring_patterns_json", "recurring_patterns"), serialization_alias="recurring_patterns")
    deadline_patterns: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("deadline_patterns_json", "deadline_patterns"), serialization_alias="deadline_patterns")
    bottlenecks: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("bottlenecks_json", "bottlenecks"), serialization_alias="bottlenecks")
    operational_strengths: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("operational_strengths_json", "operational_strengths"), serialization_alias="operational_strengths")
    attention_areas: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("attention_areas_json", "attention_areas"), serialization_alias="attention_areas")
    risks: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("risks_json", "risks"), serialization_alias="risks")
    recommended_improvements: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("recommended_improvements_json", "recommended_improvements"), serialization_alias="recommended_improvements")
    template_candidates: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("template_candidates_json", "template_candidates"), serialization_alias="template_candidates")
    automation_candidates: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("automation_candidates_json", "automation_candidates"), serialization_alias="automation_candidates")
    source_counts: dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("source_counts_json", "source_counts"), serialization_alias="source_counts")
    data_coverage: dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("data_coverage_json", "data_coverage"), serialization_alias="data_coverage")
    limitations: list[Any] = Field(default_factory=list, validation_alias=AliasChoices("limitations_json", "limitations"), serialization_alias="limitations")
    is_rule_based: bool = True
    ai_narrative_used: bool = False
    ai_job_id: UUID | None = None
    provider_mode: str | None = None
    provider_key: str | None = None
    model_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("metadata_json", "metadata"), serialization_alias="metadata")

    @field_validator("work_volume", "source_counts", "data_coverage", "metadata", mode="before")
    @classmethod
    def ensure_dicts(cls, value: Any) -> dict[str, Any]:
        return safe_dict(value)

    @field_validator(
        "work_type_distribution",
        "status_distribution",
        "priority_distribution",
        "completion_patterns",
        "overdue_patterns",
        "blocked_patterns",
        "workflow_patterns",
        "project_patterns",
        "department_patterns",
        "team_patterns",
        "tag_patterns",
        "recurring_patterns",
        "deadline_patterns",
        "bottlenecks",
        "operational_strengths",
        "attention_areas",
        "risks",
        "recommended_improvements",
        "template_candidates",
        "automation_candidates",
        "limitations",
        mode="before",
    )
    @classmethod
    def ensure_lists(cls, value: Any) -> list[Any]:
        return safe_list(value)


class WorkDNASignalsRead(FebGridModel):
    company_id: UUID
    scope_type: str
    scope_id: UUID | None = None
    period_days: int
    period_start: datetime
    period_end: datetime
    overall_summary: str
    work_volume: dict[str, Any] = Field(default_factory=dict)
    work_type_distribution: list[Any] = Field(default_factory=list)
    status_distribution: list[Any] = Field(default_factory=list)
    priority_distribution: list[Any] = Field(default_factory=list)
    completion_patterns: list[Any] = Field(default_factory=list)
    overdue_patterns: list[Any] = Field(default_factory=list)
    blocked_patterns: list[Any] = Field(default_factory=list)
    workflow_patterns: list[Any] = Field(default_factory=list)
    project_patterns: list[Any] = Field(default_factory=list)
    department_patterns: list[Any] = Field(default_factory=list)
    team_patterns: list[Any] = Field(default_factory=list)
    tag_patterns: list[Any] = Field(default_factory=list)
    recurring_patterns: list[Any] = Field(default_factory=list)
    deadline_patterns: list[Any] = Field(default_factory=list)
    bottlenecks: list[Any] = Field(default_factory=list)
    operational_strengths: list[Any] = Field(default_factory=list)
    attention_areas: list[Any] = Field(default_factory=list)
    risks: list[Any] = Field(default_factory=list)
    recommended_improvements: list[Any] = Field(default_factory=list)
    template_candidates: list[Any] = Field(default_factory=list)
    automation_candidates: list[Any] = Field(default_factory=list)
    source_counts: dict[str, Any] = Field(default_factory=dict)
    data_coverage: dict[str, Any] = Field(default_factory=dict)
    limitations: list[Any] = Field(default_factory=list)
    generated_at: datetime
    is_rule_based: bool = True
    ai_narrative_used: bool = False
    provider_mode: str | None = None
    model_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
