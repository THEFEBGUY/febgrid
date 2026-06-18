from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, EmailStr, Field

from app.schemas.common import FebGridModel, MetadataField, Timestamped


class EmployeeBase(MetadataField):
    company_id: UUID
    manager_id: UUID | None = None
    full_name: str = Field(min_length=1, max_length=160)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=40)
    role: str = Field(min_length=1, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    employment_type: str = Field(default="full_time", max_length=80)
    status: str = Field(default="available", max_length=60)
    location: str | None = Field(default=None, max_length=160)
    profile_image_url: str | None = None
    skills: list[str] = Field(default_factory=list)


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(FebGridModel):
    manager_id: UUID | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    role: str | None = Field(default=None, min_length=1, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    employment_type: str | None = Field(default=None, max_length=80)
    status: str | None = Field(default=None, max_length=60)
    location: str | None = Field(default=None, max_length=160)
    profile_image_url: str | None = None
    skills: list[str] | None = None
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata", "metadata_json"),
        serialization_alias="metadata",
    )


class EmployeeStatusUpdate(FebGridModel):
    company_id: UUID
    status: str = Field(min_length=1, max_length=60)
    actor_employee_id: UUID | None = None


class EmployeeRead(EmployeeBase, Timestamped):
    id: UUID


class EmployeeActivityRead(FebGridModel):
    employee: EmployeeRead
    events: list[Any]
    generated_at: datetime
