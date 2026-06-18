from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import FebGridModel, Timestamped


class WorkObjectBase(FebGridModel):
    company_id: UUID
    project_id: UUID | None = None
    created_by_employee_id: UUID | None = None
    assigned_to_employee_id: UUID | None = None
    title: str = Field(min_length=1, max_length=220)
    description: str | None = None
    object_type: str = Field(default="task", max_length=80)
    status: str = Field(default="draft", max_length=60)
    priority: str = Field(default="medium", max_length=40)
    due_date: datetime | None = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    ai_summary: str | None = None


class WorkObjectCreate(WorkObjectBase):
    pass


class WorkObjectUpdate(FebGridModel):
    project_id: UUID | None = None
    assigned_to_employee_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=220)
    description: str | None = None
    object_type: str | None = Field(default=None, max_length=80)
    status: str | None = Field(default=None, max_length=60)
    priority: str | None = Field(default=None, max_length=40)
    due_date: datetime | None = None
    tags: list[str] | None = None
    custom_fields: dict[str, Any] | None = None
    ai_summary: str | None = None


class WorkObjectStatusUpdate(FebGridModel):
    company_id: UUID
    status: str = Field(min_length=1, max_length=60)
    actor_employee_id: UUID | None = None


class WorkObjectRead(WorkObjectBase, Timestamped):
    id: UUID
