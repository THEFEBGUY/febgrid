from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, Field, field_validator

from app.schemas.common import FebGridModel, Timestamped


class PlanDefinitionRead(FebGridModel):
    key: str
    name: str
    description: str
    seat_limit: int
    storage_limit_mb: int
    work_object_limit: int
    project_limit: int
    employee_limit: int
    notification_limit: int | None = None
    file_upload_limit_mb: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class BillingUsageRead(FebGridModel):
    company_id: UUID
    active_employees: int
    active_projects: int
    active_work_objects: int
    uploaded_file_count: int
    storage_used_mb: float
    active_departments: int
    active_teams: int
    notifications_count: int
    monthly_events_count: int


class UsageWarningRead(FebGridModel):
    code: str
    message: str
    current: float
    limit: float
    severity: str = "warning"


class CompanyBillingPlanRead(Timestamped):
    id: UUID
    company_id: UUID
    plan_key: str
    billing_status: str
    trial_start_at: datetime | None = None
    trial_ends_at: datetime | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    seat_limit: int
    storage_limit_mb: int
    work_object_limit: int
    project_limit: int
    employee_limit: int
    notification_limit: int | None = None
    file_upload_limit_mb: int
    is_trial: bool
    is_active: bool
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


class BillingSummaryRead(FebGridModel):
    company_id: UUID
    company_name: str
    generated_at: datetime
    plan: CompanyBillingPlanRead
    usage: BillingUsageRead
    warnings: list[UsageWarningRead]
    payment_provider_enabled: bool = False
    payment_provider_note: str = "Payment integration coming later."


class CompanyPlanUpdate(FebGridModel):
    plan_key: str | None = Field(default=None, max_length=40)
    billing_status: str | None = Field(default=None, max_length=40)
    trial_start_at: datetime | None = None
    trial_ends_at: datetime | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    seat_limit: int | None = Field(default=None, ge=0)
    storage_limit_mb: int | None = Field(default=None, ge=0)
    work_object_limit: int | None = Field(default=None, ge=0)
    project_limit: int | None = Field(default=None, ge=0)
    employee_limit: int | None = Field(default=None, ge=0)
    notification_limit: int | None = Field(default=None, ge=0)
    file_upload_limit_mb: int | None = Field(default=None, ge=1)
    is_trial: bool | None = None
    is_active: bool | None = None
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata_json", "metadata"),
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
