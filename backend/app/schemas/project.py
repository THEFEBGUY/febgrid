from datetime import date
from uuid import UUID

from pydantic import Field

from app.schemas.common import FebGridModel, Timestamped


class ProjectBase(FebGridModel):
    company_id: UUID
    owner_employee_id: UUID | None = None
    owner_user_id: UUID | None = None
    department_id: UUID | None = None
    team_id: UUID | None = None
    name: str = Field(min_length=1, max_length=180)
    code: str | None = Field(default=None, max_length=80)
    description: str | None = None
    status: str = Field(default="not_started", min_length=1, max_length=60)
    priority: str = Field(default="medium", min_length=1, max_length=40)
    start_date: date | None = None
    due_date: date | None = None
    progress_percent: int = Field(default=0, ge=0, le=100)
    risk_level: str | None = Field(default=None, max_length=40)
    is_active: bool = True
    tags: list[str] = Field(default_factory=list)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(FebGridModel):
    owner_employee_id: UUID | None = None
    owner_user_id: UUID | None = None
    department_id: UUID | None = None
    team_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=180)
    code: str | None = Field(default=None, max_length=80)
    description: str | None = None
    status: str | None = Field(default=None, min_length=1, max_length=60)
    priority: str | None = Field(default=None, min_length=1, max_length=40)
    start_date: date | None = None
    due_date: date | None = None
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    risk_level: str | None = Field(default=None, max_length=40)
    is_active: bool | None = None
    tags: list[str] | None = None


class ProjectRead(ProjectBase, Timestamped):
    id: UUID


class ProjectStatusUpdate(FebGridModel):
    company_id: UUID
    status: str = Field(min_length=1, max_length=60)


class ProjectPriorityUpdate(FebGridModel):
    company_id: UUID
    priority: str = Field(min_length=1, max_length=40)


class ProjectOwnerUpdate(FebGridModel):
    company_id: UUID
    owner_employee_id: UUID | None = None
    owner_user_id: UUID | None = None


class ProjectMemberCreate(FebGridModel):
    company_id: UUID
    employee_id: UUID
    role_on_project: str | None = Field(default=None, max_length=120)


class ProjectMemberRead(Timestamped):
    id: UUID
    project_id: UUID
    company_id: UUID
    employee_id: UUID
    role_on_project: str | None = None
    is_active: bool
