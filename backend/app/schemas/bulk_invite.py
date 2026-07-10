from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AliasChoices, Field

from app.schemas.common import FebGridModel


BulkInviteRowStatus = Literal[
    "VALID",
    "INVALID",
    "DUPLICATE",
    "EXISTING_EMPLOYEE",
    "EXISTING_INVITATION",
]


class BulkInviteValidationIssue(FebGridModel):
    code: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=300)


class BulkInviteNormalizedRow(FebGridModel):
    email: str = Field(default="", max_length=255)
    full_name: str = Field(default="", validation_alias=AliasChoices("fullName", "full_name"), max_length=160)
    job_title: str = Field(default="", validation_alias=AliasChoices("jobTitle", "job_title"), max_length=120)
    role: str = Field(default="", max_length=40)
    department: str = Field(default="", max_length=140)
    team: str = Field(default="", max_length=140)
    manager_email: str = Field(default="", validation_alias=AliasChoices("managerEmail", "manager_email"), max_length=255)
    employment_type: str = Field(default="", validation_alias=AliasChoices("employmentType", "employment_type"), max_length=80)
    phone: str = Field(default="", max_length=40)
    employee_code: str = Field(default="", validation_alias=AliasChoices("employeeCode", "employee_code"), max_length=80)


class JavaBulkInviteValidationRow(FebGridModel):
    row_number: int = Field(validation_alias=AliasChoices("rowNumber", "row_number"), ge=2)
    status: Literal["VALID", "INVALID", "DUPLICATE"]
    normalized: BulkInviteNormalizedRow
    errors: list[BulkInviteValidationIssue] = Field(default_factory=list)
    warnings: list[BulkInviteValidationIssue] = Field(default_factory=list)


class JavaBulkInviteValidationResponse(FebGridModel):
    request_id: str = Field(validation_alias=AliasChoices("requestId", "request_id"), min_length=1, max_length=160)
    file_name: str = Field(validation_alias=AliasChoices("fileName", "file_name"), min_length=1, max_length=255)
    total_rows: int = Field(validation_alias=AliasChoices("totalRows", "total_rows"), ge=0)
    valid_row_count: int = Field(validation_alias=AliasChoices("validRowCount", "valid_row_count"), ge=0)
    invalid_row_count: int = Field(validation_alias=AliasChoices("invalidRowCount", "invalid_row_count"), ge=0)
    duplicate_row_count: int = Field(validation_alias=AliasChoices("duplicateRowCount", "duplicate_row_count"), ge=0)
    rows: list[JavaBulkInviteValidationRow] = Field(default_factory=list)


class BulkInvitePreviewRow(FebGridModel):
    row_number: int = Field(ge=2)
    status: BulkInviteRowStatus
    normalized: BulkInviteNormalizedRow
    errors: list[BulkInviteValidationIssue] = Field(default_factory=list)
    warnings: list[BulkInviteValidationIssue] = Field(default_factory=list)
    department_id: UUID | None = None
    team_id: UUID | None = None
    manager_employee_id: UUID | None = None


class BulkInvitePreviewRead(FebGridModel):
    company_id: UUID
    file_name: str
    total_rows: int = Field(ge=0)
    valid_row_count: int = Field(ge=0)
    invalid_row_count: int = Field(ge=0)
    duplicate_row_count: int = Field(ge=0)
    existing_employee_count: int = Field(ge=0)
    existing_invitation_count: int = Field(ge=0)
    preview_token: str
    preview_expires_at: datetime
    rows: list[BulkInvitePreviewRow] = Field(default_factory=list)
