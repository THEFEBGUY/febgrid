from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, EmailStr, Field

from app.schemas.common import FebGridModel, MetadataField, Timestamped


class EmployeeBase(MetadataField):
    company_id: UUID
    user_id: UUID | None = None
    department_id: UUID | None = None
    team_id: UUID | None = None
    manager_id: UUID | None = None
    full_name: str = Field(min_length=1, max_length=160)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    role_title: str = Field(
        min_length=1,
        max_length=120,
        validation_alias=AliasChoices("role_title", "role"),
        serialization_alias="role_title",
    )
    department: str | None = Field(default=None, max_length=120)
    employment_type: str = Field(default="full_time", max_length=80)
    current_status: str = Field(
        default="available",
        min_length=1,
        max_length=60,
        validation_alias=AliasChoices("current_status", "status"),
        serialization_alias="current_status",
    )
    location: str | None = Field(default=None, max_length=160)
    profile_image_url: str | None = None
    skills: list[str] = Field(default_factory=list)
    joined_at: datetime | None = None
    is_active: bool = True


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(FebGridModel):
    user_id: UUID | None = None
    department_id: UUID | None = None
    team_id: UUID | None = None
    manager_id: UUID | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)
    role_title: str | None = Field(
        default=None,
        min_length=1,
        max_length=120,
        validation_alias=AliasChoices("role_title", "role"),
        serialization_alias="role_title",
    )
    department: str | None = Field(default=None, max_length=120)
    employment_type: str | None = Field(default=None, max_length=80)
    current_status: str | None = Field(
        default=None,
        min_length=1,
        max_length=60,
        validation_alias=AliasChoices("current_status", "status"),
        serialization_alias="current_status",
    )
    location: str | None = Field(default=None, max_length=160)
    profile_image_url: str | None = None
    skills: list[str] | None = None
    joined_at: datetime | None = None
    is_active: bool | None = None
    metadata: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )


class EmployeeStatusUpdate(FebGridModel):
    company_id: UUID
    current_status: str = Field(
        min_length=1,
        max_length=60,
        validation_alias=AliasChoices("current_status", "status"),
        serialization_alias="current_status",
    )
    actor_employee_id: UUID | None = None


class EmployeeRead(EmployeeBase, Timestamped):
    id: UUID


class EmployeeActivityRead(FebGridModel):
    employee: EmployeeRead
    events: list[Any]
    generated_at: datetime
