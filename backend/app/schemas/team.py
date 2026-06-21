from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import FebGridModel, Timestamped


class TeamBase(FebGridModel):
    company_id: UUID
    department_id: UUID | None = None
    lead_employee_id: UUID | None = None
    name: str = Field(min_length=1, max_length=140)
    department: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class TeamCreate(TeamBase):
    pass


class TeamUpdate(FebGridModel):
    department_id: UUID | None = None
    lead_employee_id: UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=140)
    department: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class TeamRead(TeamBase, Timestamped):
    id: UUID


class TeamMemberCreate(FebGridModel):
    company_id: UUID
    employee_id: UUID


class TeamMemberRead(FebGridModel):
    id: UUID
    company_id: UUID
    team_id: UUID
    employee_id: UUID
    joined_at: datetime
