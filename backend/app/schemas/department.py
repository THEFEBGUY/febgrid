from uuid import UUID

from pydantic import Field

from app.schemas.common import FebGridModel, Timestamped


class DepartmentBase(FebGridModel):
    company_id: UUID
    name: str = Field(min_length=1, max_length=140)
    description: str | None = None
    is_active: bool = True


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(FebGridModel):
    name: str | None = Field(default=None, min_length=1, max_length=140)
    description: str | None = None
    is_active: bool | None = None


class DepartmentRead(DepartmentBase, Timestamped):
    id: UUID
