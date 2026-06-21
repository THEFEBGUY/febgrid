from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, Field, field_validator

from app.schemas.common import FebGridModel, Timestamped


class WorkObjectBase(FebGridModel):
    company_id: UUID
    project_id: UUID | None = None
    department_id: UUID | None = None
    team_id: UUID | None = None
    creator_employee_id: UUID | None = Field(
        default=None,
        validation_alias=AliasChoices("creator_employee_id", "created_by_employee_id"),
        serialization_alias="creator_employee_id",
    )
    creator_user_id: UUID | None = None
    assignee_employee_id: UUID | None = Field(
        default=None,
        validation_alias=AliasChoices("assignee_employee_id", "assigned_to_employee_id"),
        serialization_alias="assignee_employee_id",
    )
    title: str = Field(min_length=1, max_length=220)
    description: str | None = None
    object_type: str = Field(default="task", min_length=1, max_length=80)
    status: str = Field(default="assigned", min_length=1, max_length=60)
    priority: str = Field(default="medium", min_length=1, max_length=40)
    due_date: datetime | None = None
    start_date: datetime | None = None
    completed_at: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    ai_summary: str | None = None
    is_active: bool = True

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_metadata_dict(cls, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        return {}


class WorkObjectCreate(WorkObjectBase):
    pass


class WorkObjectUpdate(FebGridModel):
    project_id: UUID | None = None
    department_id: UUID | None = None
    team_id: UUID | None = None
    creator_employee_id: UUID | None = Field(
        default=None,
        validation_alias=AliasChoices("creator_employee_id", "created_by_employee_id"),
        serialization_alias="creator_employee_id",
    )
    creator_user_id: UUID | None = None
    assignee_employee_id: UUID | None = Field(
        default=None,
        validation_alias=AliasChoices("assignee_employee_id", "assigned_to_employee_id"),
        serialization_alias="assignee_employee_id",
    )
    title: str | None = Field(default=None, min_length=1, max_length=220)
    description: str | None = None
    object_type: str | None = Field(default=None, min_length=1, max_length=80)
    status: str | None = Field(default=None, min_length=1, max_length=60)
    priority: str | None = Field(default=None, min_length=1, max_length=40)
    due_date: datetime | None = None
    start_date: datetime | None = None
    completed_at: datetime | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )
    custom_fields: dict[str, Any] | None = None
    ai_summary: str | None = None
    is_active: bool | None = None


class WorkObjectStatusUpdate(FebGridModel):
    company_id: UUID
    status: str = Field(min_length=1, max_length=60)
    actor_employee_id: UUID | None = None


class WorkObjectPriorityUpdate(FebGridModel):
    company_id: UUID
    priority: str = Field(min_length=1, max_length=40)


class WorkObjectAssigneeUpdate(FebGridModel):
    company_id: UUID
    assignee_employee_id: UUID | None = Field(
        default=None,
        validation_alias=AliasChoices("assignee_employee_id", "assigned_to_employee_id"),
        serialization_alias="assignee_employee_id",
    )


class WorkObjectProjectUpdate(FebGridModel):
    company_id: UUID
    project_id: UUID | None = None


class WorkObjectOrgUpdate(FebGridModel):
    company_id: UUID
    department_id: UUID | None = None
    team_id: UUID | None = None


class WorkObjectComplete(FebGridModel):
    company_id: UUID


class WorkObjectSummary(FebGridModel):
    company_id: UUID
    total: int
    open: int
    blocked: int
    completed: int
    due_soon: int
    overdue: int


class WorkObjectRead(WorkObjectBase, Timestamped):
    id: UUID
