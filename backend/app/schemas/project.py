from datetime import date
from uuid import UUID

from pydantic import Field

from app.schemas.common import FebGridModel, Timestamped


class ProjectBase(FebGridModel):
    company_id: UUID
    owner_employee_id: UUID | None = None
    name: str = Field(min_length=1, max_length=180)
    description: str | None = None
    status: str = Field(default="not_started", max_length=60)
    priority: str = Field(default="medium", max_length=40)
    start_date: date | None = None
    due_date: date | None = None
    progress_percent: int = Field(default=0, ge=0, le=100)
    tags: list[str] = Field(default_factory=list)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(FebGridModel):
    owner_employee_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = None
    status: str | None = Field(default=None, max_length=60)
    priority: str | None = Field(default=None, max_length=40)
    start_date: date | None = None
    due_date: date | None = None
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    tags: list[str] | None = None


class ProjectRead(ProjectBase, Timestamped):
    id: UUID
