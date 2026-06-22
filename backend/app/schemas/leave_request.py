from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, Field, field_validator, model_validator

from app.schemas.common import FebGridModel, Timestamped


class LeaveRequestBase(FebGridModel):
    company_id: UUID
    employee_id: UUID
    approver_employee_id: UUID | None = None
    leave_type: str = Field(min_length=1, max_length=80)
    start_date: date
    end_date: date
    reason: str | None = None
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

    @model_validator(mode="after")
    def validate_date_range(self) -> "LeaveRequestBase":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class LeaveRequestCreate(LeaveRequestBase):
    requested_by_user_id: UUID | None = None
    status: str = Field(default="pending", max_length=40)
    manager_note: str | None = Field(
        default=None,
        validation_alias=AliasChoices("manager_note", "decision_note"),
        serialization_alias="manager_note",
    )


class LeaveRequestUpdate(FebGridModel):
    employee_id: UUID | None = None
    approver_employee_id: UUID | None = None
    leave_type: str | None = Field(default=None, min_length=1, max_length=80)
    start_date: date | None = None
    end_date: date | None = None
    reason: str | None = None
    status: str | None = Field(default=None, max_length=40)
    manager_note: str | None = Field(
        default=None,
        validation_alias=AliasChoices("manager_note", "decision_note"),
        serialization_alias="manager_note",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )
    is_active: bool | None = None

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_optional_metadata_dict(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        return {}


class LeaveDecision(FebGridModel):
    company_id: UUID
    approver_employee_id: UUID | None = None
    manager_note: str | None = Field(
        default=None,
        validation_alias=AliasChoices("manager_note", "decision_note"),
        serialization_alias="manager_note",
    )


class LeaveCancel(FebGridModel):
    company_id: UUID
    actor_employee_id: UUID | None = None
    manager_note: str | None = Field(
        default=None,
        validation_alias=AliasChoices("manager_note", "decision_note"),
        serialization_alias="manager_note",
    )


class LeaveSummary(FebGridModel):
    company_id: UUID
    total: int
    pending: int
    approved: int
    rejected: int
    cancelled: int
    this_week: int
    this_month: int


class LeaveRequestRead(LeaveRequestBase, Timestamped):
    id: UUID
    requested_by_user_id: UUID | None = None
    status: str
    total_days: float
    manager_note: str | None = Field(
        default=None,
        validation_alias=AliasChoices("manager_note", "decision_note"),
        serialization_alias="manager_note",
    )
    submitted_at: datetime
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    cancelled_at: datetime | None = None
    is_active: bool
