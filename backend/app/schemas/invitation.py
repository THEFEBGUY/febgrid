from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import AliasChoices, EmailStr, Field

from app.schemas.auth import AuthSessionRead
from app.schemas.common import FebGridModel, MetadataField, Timestamped
from app.schemas.employee import EmployeeRead
from app.schemas.user import UserRead


class EmployeeInvitationRead(MetadataField, Timestamped):
    id: UUID
    company_id: UUID
    employee_id: UUID | None = None
    invited_email: EmailStr
    normalized_email: str
    invited_role: str
    department_id: UUID | None = None
    team_id: UUID | None = None
    manager_employee_id: UUID | None = None
    job_title: str | None = None
    employment_type: str | None = None
    joining_date: datetime | None = None
    invite_source: str
    approval_required: bool
    status: str
    expires_at: datetime
    sent_at: datetime
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None
    revoked_by_user_id: UUID | None = None
    approved_at: datetime | None = None
    approved_by_user_id: UUID | None = None
    rejected_at: datetime | None = None
    rejected_by_user_id: UUID | None = None
    rejection_reason: str | None = None
    invited_by_user_id: UUID | None = None


class EmployeeInvitationCreate(FebGridModel):
    company_id: UUID
    invited_email: EmailStr
    invited_role: str = Field(default="employee", max_length=40)
    full_name: str | None = Field(default=None, max_length=160)
    department_id: UUID | None = None
    team_id: UUID | None = None
    manager_employee_id: UUID | None = None
    job_title: str | None = Field(default=None, max_length=120)
    employment_type: str | None = Field(default="full_time", max_length=80)
    joining_date: datetime | None = None
    approval_required: bool = False
    expires_in_hours: int = Field(default=168, ge=1, le=2160)
    note: str | None = Field(default=None, max_length=500)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )


class EmployeeInvitationActionRead(FebGridModel):
    invitation: EmployeeInvitationRead
    acceptance_url: str
    email_delivery: dict[str, Any]


class InvitationPreviewRead(MetadataField):
    company_id: UUID
    company_name: str
    employee_id: UUID | None = None
    employee_name: str | None = None
    invited_email: EmailStr
    invited_role: str
    invite_source: str
    approval_required: bool
    status: str
    expires_at: datetime
    inviter_name: str | None = None
    job_title: str | None = None
    employment_type: str | None = None
    joining_date: datetime | None = None
    department_name: str | None = None
    team_name: str | None = None
    manager_name: str | None = None
    account_status: str | None = None
    activation_status: str | None = None
    profile_completion_status: str | None = None


class InvitationAcceptRequest(FebGridModel):
    token: str = Field(min_length=20, max_length=512)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, min_length=1, max_length=160)


class InvitationMagicLinkAcceptRequest(FebGridModel):
    token: str = Field(min_length=20, max_length=512)
    access_token: str = Field(min_length=20, max_length=8192)


class InvitationAcceptRead(FebGridModel):
    invitation: EmployeeInvitationRead
    employee: EmployeeRead
    user: UserRead
    requires_profile: bool = True
    approval_required: bool
    message: str


class InvitationProfileCompleteRequest(FebGridModel):
    token: str = Field(min_length=20, max_length=512)
    email: EmailStr
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, max_length=160)
    profile_image_url: str | None = None
    skills: list[str] | None = None
    bio: str | None = Field(default=None, max_length=2000)
    emergency_contact_name: str | None = Field(default=None, max_length=160)
    emergency_contact_phone: str | None = Field(default=None, max_length=40)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        validation_alias=AliasChoices("metadata_json", "metadata"),
        serialization_alias="metadata",
    )


class InvitationProfileCompleteRead(FebGridModel):
    invitation: EmployeeInvitationRead
    employee: EmployeeRead
    session: AuthSessionRead | None = None
    approval_required: bool
    message: str


class InvitationDecisionRequest(FebGridModel):
    company_id: UUID
    note: str | None = Field(default=None, max_length=1000)


class InvitationRejectRequest(FebGridModel):
    company_id: UUID
    rejection_reason: str | None = Field(default=None, max_length=1000)
