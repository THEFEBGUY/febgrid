from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.core.permissions import OWNER_ADMIN_ROLES, ensure_company_access, ensure_role
from app.core.security import create_access_token
from app.models.company import Company
from app.models.employee_invitation import EmployeeInvitation
from app.models.user import User
from app.schemas.auth import AuthSessionRead
from app.schemas.invitation import (
    EmployeeInvitationActionRead,
    EmployeeInvitationCreate,
    EmployeeInvitationRead,
    InvitationAcceptRead,
    InvitationAcceptRequest,
    InvitationDecisionRequest,
    InvitationPreviewRead,
    InvitationProfileCompleteRead,
    InvitationProfileCompleteRequest,
    InvitationRejectRequest,
)
from app.services.invitation_service import InvitationService, metadata_dict

router = APIRouter(prefix="/invitations", tags=["employee onboarding"])


def build_auth_session(user: User, company: Company) -> AuthSessionRead:
    token = create_access_token(user_id=user.id, company_id=user.company_id, role=user.role)
    return AuthSessionRead(access_token=token, user=user, company=company)


def preview_response(invitation: EmployeeInvitation) -> InvitationPreviewRead:
    company = invitation.company
    employee = invitation.employee
    return InvitationPreviewRead(
        company_id=invitation.company_id,
        company_name=company.name if company else "FebGrid company",
        employee_id=invitation.employee_id,
        employee_name=employee.full_name if employee else None,
        invited_email=invitation.invited_email,
        invited_role=invitation.invited_role,
        invite_source=invitation.invite_source,
        approval_required=invitation.approval_required,
        status=invitation.status,
        expires_at=invitation.expires_at,
        inviter_name=invitation.invited_by.full_name if invitation.invited_by else None,
        job_title=invitation.job_title,
        employment_type=invitation.employment_type,
        joining_date=invitation.joining_date,
        department_name=invitation.employee.department_ref.name if invitation.employee and invitation.employee.department_ref else None,
        team_name=invitation.employee.team_ref.name if invitation.employee and invitation.employee.team_ref else None,
        manager_name=invitation.manager.full_name if invitation.manager else None,
        account_status=employee.account_status if employee else None,
        activation_status=employee.activation_status if employee else None,
        profile_completion_status=employee.profile_completion_status if employee else None,
        metadata={key: value for key, value in metadata_dict(invitation.metadata_json).items() if key != "email_delivery"},
    )


@router.get("/preview/{token}", response_model=InvitationPreviewRead)
def preview_invitation(token: str, db: Session = Depends(db_session)) -> InvitationPreviewRead:
    try:
        invitation = InvitationService.preview(db, token=token)
    except HTTPException:
        db.commit()
        raise
    return preview_response(invitation)


@router.post("/accept", response_model=InvitationAcceptRead)
def accept_invitation(payload: InvitationAcceptRequest, db: Session = Depends(db_session)) -> InvitationAcceptRead:
    try:
        invitation, employee, user = InvitationService.accept(
            db,
            token=payload.token,
            email=str(payload.email),
            password=payload.password,
            full_name=payload.full_name,
        )
    except HTTPException:
        db.commit()
        raise
    db.commit()
    db.refresh(invitation)
    db.refresh(employee)
    db.refresh(user)
    return InvitationAcceptRead(
        invitation=invitation,
        employee=employee,
        user=user,
        requires_profile=True,
        approval_required=invitation.approval_required,
        message="Invitation accepted. Complete your employee profile to continue.",
    )


@router.post("/complete-profile", response_model=InvitationProfileCompleteRead)
def complete_profile(
    payload: InvitationProfileCompleteRequest,
    db: Session = Depends(db_session),
) -> InvitationProfileCompleteRead:
    try:
        invitation, employee, user, company = InvitationService.complete_profile(db, payload=payload)
    except HTTPException:
        db.commit()
        raise
    db.commit()
    db.refresh(invitation)
    db.refresh(employee)
    db.refresh(user)
    session = None if invitation.approval_required else build_auth_session(user, company)
    message = (
        "Profile submitted for approval."
        if invitation.approval_required
        else "Profile complete. Your employee account is active."
    )
    return InvitationProfileCompleteRead(
        invitation=invitation,
        employee=employee,
        session=session,
        approval_required=invitation.approval_required,
        message=message,
    )


@router.get("", response_model=list[EmployeeInvitationRead])
def list_invitations(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[EmployeeInvitation]:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    return InvitationService.list_company_invitations(
        db,
        company_id=company_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=EmployeeInvitationActionRead, status_code=status.HTTP_201_CREATED)
def create_invitation(
    payload: EmployeeInvitationCreate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> EmployeeInvitationActionRead:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    invitation, acceptance_url, delivery = InvitationService.create_invitation(db, payload=payload, actor_user=current_user)
    db.commit()
    db.refresh(invitation)
    return EmployeeInvitationActionRead(invitation=invitation, acceptance_url=acceptance_url, email_delivery=delivery)


@router.post("/{invitation_id}/resend", response_model=EmployeeInvitationActionRead)
def resend_invitation(
    invitation_id: UUID,
    payload: InvitationDecisionRequest,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> EmployeeInvitationActionRead:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    invitation = InvitationService.get_company_invitation(db, company_id=payload.company_id, invitation_id=invitation_id)
    invitation, acceptance_url, delivery = InvitationService.resend(db, invitation=invitation, actor_user=current_user)
    db.commit()
    db.refresh(invitation)
    return EmployeeInvitationActionRead(invitation=invitation, acceptance_url=acceptance_url, email_delivery=delivery)


@router.post("/{invitation_id}/revoke", response_model=EmployeeInvitationRead)
def revoke_invitation(
    invitation_id: UUID,
    payload: InvitationDecisionRequest,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> EmployeeInvitation:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    invitation = InvitationService.get_company_invitation(db, company_id=payload.company_id, invitation_id=invitation_id)
    invitation = InvitationService.revoke(db, invitation=invitation, actor_user=current_user)
    db.commit()
    db.refresh(invitation)
    return invitation


@router.post("/{invitation_id}/approve", response_model=EmployeeInvitationRead)
def approve_invitation(
    invitation_id: UUID,
    payload: InvitationDecisionRequest,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> EmployeeInvitation:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    invitation = InvitationService.get_company_invitation(db, company_id=payload.company_id, invitation_id=invitation_id)
    invitation, _, _ = InvitationService.approve(db, invitation=invitation, actor_user=current_user)
    db.commit()
    db.refresh(invitation)
    return invitation


@router.post("/{invitation_id}/reject", response_model=EmployeeInvitationRead)
def reject_invitation(
    invitation_id: UUID,
    payload: InvitationRejectRequest,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> EmployeeInvitation:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    invitation = InvitationService.get_company_invitation(db, company_id=payload.company_id, invitation_id=invitation_id)
    invitation, _, _ = InvitationService.reject(
        db,
        invitation=invitation,
        actor_user=current_user,
        reason=payload.rejection_reason,
    )
    db.commit()
    db.refresh(invitation)
    return invitation
