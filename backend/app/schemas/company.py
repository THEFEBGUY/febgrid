from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, Field

from app.schemas.common import FebGridModel, Timestamped


class CompanyBase(FebGridModel):
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    industry: str | None = Field(default=None, max_length=120)
    size: str | None = Field(default=None, max_length=80)
    timezone: str = Field(default="UTC", max_length=80)
    description: str | None = None
    settings: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("settings", "settings_json"),
        serialization_alias="settings",
    )


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(FebGridModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    industry: str | None = Field(default=None, max_length=120)
    size: str | None = Field(default=None, max_length=80)
    timezone: str | None = Field(default=None, max_length=80)
    description: str | None = None
    settings: dict[str, Any] | None = Field(
        default=None,
        validation_alias=AliasChoices("settings", "settings_json"),
        serialization_alias="settings",
    )
    is_active: bool | None = None


class CompanyRead(CompanyBase, Timestamped):
    id: UUID
    is_active: bool


class HealthRead(FebGridModel):
    status: str
    service: str
    environment: str
    checked_at: datetime
