from typing import Any
from uuid import UUID

from pydantic import AliasChoices, Field, field_validator

from app.schemas.common import FebGridModel, Timestamped

CUSTOM_FIELD_TYPES = {"text", "textarea", "number", "date", "checkbox", "select", "multiselect"}
KEY_PATTERN = r"^[a-z][a-z0-9_]*$"


def safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


class CompanySettingsRead(FebGridModel):
    company_id: UUID
    name: str
    industry: str | None = None
    size: str | None = None
    timezone: str
    description: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    work_week: list[str] = Field(default_factory=list)
    default_work_object_type: str = "task"
    default_priority: str = "medium"
    file_upload_max_mb: int = 10
    template_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompanySettingsUpdate(FebGridModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    industry: str | None = Field(default=None, max_length=120)
    size: str | None = Field(default=None, max_length=80)
    timezone: str | None = Field(default=None, max_length=80)
    description: str | None = None
    work_week: list[str] | None = None
    default_work_object_type: str | None = Field(default=None, max_length=80, pattern=KEY_PATTERN)
    default_priority: str | None = Field(default=None, max_length=40)
    file_upload_max_mb: int | None = Field(default=None, ge=1, le=100)
    dashboard_flags: dict[str, Any] | None = None
    notification_defaults: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None

    @field_validator("metadata", "dashboard_flags", "notification_defaults", mode="before")
    @classmethod
    def ensure_optional_dict(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        return safe_dict(value)


class IndustryTemplateWorkObjectType(FebGridModel):
    key: str
    name: str
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    is_default: bool = False
    sort_order: int = 100


class IndustryTemplateCustomField(FebGridModel):
    type_key: str
    field_key: str
    label: str
    field_type: str
    required: bool = False
    options: list[str] = Field(default_factory=list)
    default_value: Any | None = None
    help_text: str | None = None
    sort_order: int = 100


class IndustryTemplateRead(FebGridModel):
    key: str
    name: str
    description: str
    industry: str
    work_object_types: list[IndustryTemplateWorkObjectType]
    custom_fields: list[IndustryTemplateCustomField]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApplyIndustryTemplatePayload(FebGridModel):
    template_key: str = Field(min_length=1, max_length=80)


class ApplyIndustryTemplateResult(FebGridModel):
    company_id: UUID
    template_key: str
    created_type_count: int
    created_custom_field_count: int
    skipped_type_count: int
    skipped_custom_field_count: int


class WorkObjectTypeBase(FebGridModel):
    company_id: UUID
    key: str = Field(min_length=1, max_length=80, pattern=KEY_PATTERN)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    icon: str | None = Field(default=None, max_length=80)
    color: str | None = Field(default=None, max_length=40)
    is_default: bool = False
    is_active: bool = True
    sort_order: int = 100
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_metadata_dict(cls, value: Any) -> dict[str, Any]:
        return safe_dict(value)


class WorkObjectTypeCreate(WorkObjectTypeBase):
    pass


class WorkObjectTypeUpdate(FebGridModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    icon: str | None = Field(default=None, max_length=80)
    color: str | None = Field(default=None, max_length=40)
    is_default: bool | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    metadata: dict[str, Any] | None = Field(default=None, validation_alias=AliasChoices("metadata_json", "metadata"), serialization_alias="metadata")

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_optional_metadata_dict(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        return safe_dict(value)


class WorkObjectTypeRead(WorkObjectTypeBase, Timestamped):
    id: UUID


class CustomFieldDefinitionBase(FebGridModel):
    company_id: UUID
    work_object_type_id: UUID | None = None
    type_key: str = Field(min_length=1, max_length=80, pattern=KEY_PATTERN)
    field_key: str = Field(min_length=1, max_length=80, pattern=KEY_PATTERN)
    label: str = Field(min_length=1, max_length=140)
    field_type: str = Field(min_length=1, max_length=40)
    required: bool = False
    options: list[str] = Field(default_factory=list)
    default_value: Any | None = None
    help_text: str | None = None
    sort_order: int = 100
    is_active: bool = True
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )

    @field_validator("field_type")
    @classmethod
    def ensure_field_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in CUSTOM_FIELD_TYPES:
            raise ValueError("Invalid custom field type")
        return normalized

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_metadata_dict(cls, value: Any) -> dict[str, Any]:
        return safe_dict(value)


class CustomFieldDefinitionCreate(CustomFieldDefinitionBase):
    pass


class CustomFieldDefinitionUpdate(FebGridModel):
    work_object_type_id: UUID | None = None
    label: str | None = Field(default=None, min_length=1, max_length=140)
    field_type: str | None = Field(default=None, max_length=40)
    required: bool | None = None
    options: list[str] | None = None
    default_value: Any | None = None
    help_text: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    metadata: dict[str, Any] | None = Field(default=None, validation_alias=AliasChoices("metadata_json", "metadata"), serialization_alias="metadata")

    @field_validator("field_type")
    @classmethod
    def ensure_optional_field_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized not in CUSTOM_FIELD_TYPES:
            raise ValueError("Invalid custom field type")
        return normalized

    @field_validator("metadata", mode="before")
    @classmethod
    def ensure_optional_metadata_dict(cls, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        return safe_dict(value)


class CustomFieldDefinitionRead(CustomFieldDefinitionBase, Timestamped):
    id: UUID
