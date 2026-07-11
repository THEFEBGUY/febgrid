import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import ALL_ROLES, OWNER_ADMIN_ROLES
from app.core.security import hash_password, verify_password
from app.models.company import Company
from app.models.department import Department
from app.models.employee import Employee
from app.models.employee_invitation import EmployeeInvitation
from app.models.team import Team
from app.models.user import User
from app.schemas.invitation import EmployeeInvitationCreate, InvitationProfileCompleteRequest
from app.services.email_service import EmailService
from app.services.event_service import EventService
from app.services.notification_service import NotificationService

INVITATION_PENDING = "pending"
INVITATION_ACCEPTED = "accepted"
INVITATION_EXPIRED = "expired"
INVITATION_REVOKED = "revoked"
INVITATION_SUBMITTED = "submitted_for_approval"
INVITATION_APPROVED = "approved"
INVITATION_REJECTED = "rejected"
INVITATION_ACTIVATION_SENT = "activation_sent"

FINAL_INVITATION_STATUSES = {INVITATION_ACCEPTED, INVITATION_APPROVED, INVITATION_REJECTED}
OPEN_INVITATION_STATUSES = {INVITATION_PENDING, INVITATION_ACTIVATION_SENT, INVITATION_SUBMITTED}
RESENDABLE_STATUSES = {INVITATION_PENDING, INVITATION_ACTIVATION_SENT, INVITATION_EXPIRED}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def metadata_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class InvitationService:
    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(36)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def acceptance_url(token: str) -> str:
        return f"/accept-invite/{token}"

    @staticmethod
    def invited_name_from_email(email: str) -> str:
        local_part = email.split("@", 1)[0].replace(".", " ").replace("_", " ").strip()
        return local_part.title() or "Invited Employee"

    @classmethod
    def issue_token(cls, invitation: EmployeeInvitation, *, expires_in_hours: int) -> str:
        token = cls.generate_token()
        invitation.token_hash = cls.hash_token(token)
        invitation.expires_at = utc_now() + timedelta(hours=expires_in_hours)
        invitation.sent_at = utc_now()
        return token

    @classmethod
    def _delivery_metadata(cls, invitation: EmployeeInvitation, *, token: str, template: str) -> dict[str, Any]:
        return EmailService.prepare_employee_onboarding_delivery(
            template=template,
            recipient_email=invitation.invited_email,
            company_name=invitation.company.name if invitation.company else None,
            action_path=cls.acceptance_url(token),
        )

    @staticmethod
    def _validate_role(role: str) -> str:
        normalized = role.strip()
        if normalized not in ALL_ROLES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid invited role")
        if normalized in OWNER_ADMIN_ROLES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Employee invitations cannot assign owner/admin roles",
            )
        return normalized

    @staticmethod
    def _company(db: Session, company_id: UUID) -> Company:
        company = db.get(Company, company_id)
        if company is None or not company.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        return company

    @staticmethod
    def _validate_refs(
        db: Session,
        *,
        company_id: UUID,
        department_id: UUID | None = None,
        team_id: UUID | None = None,
        manager_employee_id: UUID | None = None,
    ) -> tuple[Department | None, Team | None, Employee | None]:
        department = None
        if department_id is not None:
            department = db.get(Department, department_id)
            if department is None or department.company_id != company_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")

        team = None
        if team_id is not None:
            team = db.get(Team, team_id)
            if team is None or team.company_id != company_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")

        manager = None
        if manager_employee_id is not None:
            manager = db.get(Employee, manager_employee_id)
            if manager is None or manager.company_id != company_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manager not found")

        return department, team, manager

    @staticmethod
    def _employee_by_email(db: Session, *, company_id: UUID, email: str) -> Employee | None:
        return db.scalar(
            select(Employee).where(
                Employee.company_id == company_id,
                Employee.email.is_not(None),
                func.lower(Employee.email) == email,
            )
        )

    @staticmethod
    def _active_invitation_for_email(db: Session, *, company_id: UUID, email: str) -> EmployeeInvitation | None:
        return db.scalar(
            select(EmployeeInvitation)
            .where(
                EmployeeInvitation.company_id == company_id,
                EmployeeInvitation.normalized_email == email,
                EmployeeInvitation.status.in_(OPEN_INVITATION_STATUSES),
            )
            .order_by(EmployeeInvitation.created_at.desc())
            .limit(1)
        )

    @classmethod
    def _invitation_by_token(cls, db: Session, token: str) -> EmployeeInvitation:
        token_hash = cls.hash_token(token)
        invitation = db.scalar(select(EmployeeInvitation).where(EmployeeInvitation.token_hash == token_hash))
        if invitation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
        if invitation.status in {INVITATION_REVOKED, INVITATION_REJECTED}:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation is no longer available")
        if invitation.status not in {INVITATION_ACCEPTED, INVITATION_APPROVED, INVITATION_SUBMITTED}:
            if ensure_aware(invitation.expires_at) < utc_now():
                invitation.status = INVITATION_EXPIRED
                EventService.record_event(
                    db,
                    company_id=invitation.company_id,
                    event_type="employee_invite.expired",
                    title="Employee invitation expired",
                    target_entity_type="employee_invitation",
                    target_entity_id=invitation.id,
                    related_entity_type="employee",
                    related_entity_id=invitation.employee_id,
                    metadata={"invited_email": invitation.normalized_email, "invite_source": invitation.invite_source},
                )
                db.flush()
                raise HTTPException(status_code=status.HTTP_410_GONE, detail="Invitation has expired")
        return invitation

    @staticmethod
    def _ensure_invited_email(invitation: EmployeeInvitation, email: str) -> str:
        normalized = normalize_email(email)
        if normalized != invitation.normalized_email:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invitation email does not match")
        return normalized

    @classmethod
    def create_invitation(
        cls,
        db: Session,
        *,
        payload: EmployeeInvitationCreate,
        actor_user: User,
    ) -> tuple[EmployeeInvitation, str, dict[str, Any]]:
        company = cls._company(db, payload.company_id)
        payload_metadata = metadata_dict(payload.metadata)
        employee_code = payload_metadata.get("employee_code")
        if not isinstance(employee_code, str) or not employee_code.strip():
            employee_code = None
        invited_email = normalize_email(str(payload.invited_email))
        invited_role = cls._validate_role(payload.invited_role)
        department, team, manager = cls._validate_refs(
            db,
            company_id=company.id,
            department_id=payload.department_id,
            team_id=payload.team_id,
            manager_employee_id=payload.manager_employee_id,
        )

        existing_user = db.scalar(select(User).where(User.email == invited_email))
        if existing_user is not None and existing_user.company_id != company.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This email is already used by another company account")

        employee = cls._employee_by_email(db, company_id=company.id, email=invited_email)
        if employee is not None and employee.user_id is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee already has a linked user account")

        existing_invitation = cls._active_invitation_for_email(db, company_id=company.id, email=invited_email)
        if existing_invitation is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An active invitation already exists for this email")

        if employee is None:
            employee = Employee(
                company_id=company.id,
                department_id=payload.department_id,
                team_id=payload.team_id,
                manager_id=payload.manager_employee_id,
                full_name=payload.full_name or cls.invited_name_from_email(invited_email),
                email=invited_email,
                role=payload.job_title or invited_role.replace("_", " ").title(),
                department=department.name if department else None,
                employment_type=payload.employment_type or "full_time",
                status="offline",
                skills=[],
                metadata_json={
                    "invite_source": "invite",
                    **({"employee_code": employee_code.strip()} if employee_code else {}),
                },
                is_active=True,
                account_status="pending_activation",
                activation_status="invitation_sent",
                profile_completion_status="prefill_pending",
            )
            if payload.joining_date is not None:
                employee.joined_at = payload.joining_date
            db.add(employee)
            db.flush()
        else:
            if payload.full_name:
                employee.full_name = payload.full_name
            if payload.department_id is not None:
                employee.department_id = payload.department_id
                employee.department = department.name if department else employee.department
            if payload.team_id is not None:
                employee.team_id = payload.team_id
            if payload.manager_employee_id is not None:
                employee.manager_id = payload.manager_employee_id
            if payload.job_title:
                employee.role = payload.job_title
            if payload.employment_type:
                employee.employment_type = payload.employment_type
            if employee_code:
                employee.metadata_json = {**metadata_dict(employee.metadata_json), "employee_code": employee_code.strip()}
            employee.account_status = "pending_activation"
            employee.activation_status = "invitation_sent"
            employee.profile_completion_status = "prefill_pending"

        token = cls.generate_token()
        issued_at = utc_now()
        expires_at = issued_at + timedelta(hours=payload.expires_in_hours)
        invitation = EmployeeInvitation(
            company_id=company.id,
            employee_id=employee.id,
            invited_email=invited_email,
            normalized_email=invited_email,
            invited_role=invited_role,
            department_id=payload.department_id,
            team_id=payload.team_id,
            manager_employee_id=payload.manager_employee_id,
            job_title=payload.job_title,
            employment_type=payload.employment_type,
            joining_date=payload.joining_date,
            invite_source="invite",
            approval_required=payload.approval_required,
            status=INVITATION_PENDING,
            token_hash=cls.hash_token(token),
            expires_at=expires_at,
            sent_at=issued_at,
            invited_by_user_id=actor_user.id,
            metadata_json={**payload_metadata, "note": payload.note},
        )
        db.add(invitation)
        db.flush()
        delivery = cls._delivery_metadata(invitation, token=token, template="employee_invitation")
        invitation.metadata_json = {**metadata_dict(invitation.metadata_json), "email_delivery": delivery}
        event = EventService.record_event(
            db,
            company_id=company.id,
            actor_user_id=actor_user.id,
            event_type="employee_invite.sent",
            title=f"Invitation sent to {invited_email}",
            target_entity_type="employee_invitation",
            target_entity_id=invitation.id,
            related_entity_type="employee",
            related_entity_id=employee.id,
            metadata={
                "invited_email": invited_email,
                "employee_id": str(employee.id),
                "approval_required": payload.approval_required,
                "delivery": delivery,
            },
        )
        NotificationService.create_for_owner_admins(
            db,
            company_id=company.id,
            title="Employee invitation sent",
            message=f"Invitation sent to {invited_email}.",
            notification_type="employee_invite.sent",
            actor_user_id=actor_user.id,
            event_id=event.id,
            target_entity_type="employee_invitation",
            target_entity_id=invitation.id,
            priority="low",
            exclude_user_ids={actor_user.id},
        )
        return invitation, cls.acceptance_url(token), delivery

    @classmethod
    def create_manual_activation_for_employee(
        cls,
        db: Session,
        *,
        employee: Employee,
        actor_user: User,
        expires_in_hours: int = 168,
    ) -> tuple[EmployeeInvitation, str, dict[str, Any]] | None:
        if not employee.email or employee.user_id is not None:
            return None
        email = normalize_email(employee.email)
        existing_invitation = cls._active_invitation_for_email(db, company_id=employee.company_id, email=email)
        if existing_invitation is not None:
            return None

        token = cls.generate_token()
        issued_at = utc_now()
        expires_at = issued_at + timedelta(hours=expires_in_hours)
        invitation = EmployeeInvitation(
            company_id=employee.company_id,
            employee_id=employee.id,
            invited_email=email,
            normalized_email=email,
            invited_role="employee",
            department_id=employee.department_id,
            team_id=employee.team_id,
            manager_employee_id=employee.manager_id,
            job_title=employee.role,
            employment_type=employee.employment_type,
            joining_date=employee.joined_at,
            invite_source="manual_add",
            approval_required=False,
            status=INVITATION_ACTIVATION_SENT,
            token_hash=cls.hash_token(token),
            expires_at=expires_at,
            sent_at=issued_at,
            invited_by_user_id=actor_user.id,
            metadata_json={"source": "manual_employee_add"},
        )
        db.add(invitation)
        db.flush()
        delivery = cls._delivery_metadata(invitation, token=token, template="manual_employee_activation")
        invitation.metadata_json = {**metadata_dict(invitation.metadata_json), "email_delivery": delivery}
        EventService.record_event(
            db,
            company_id=employee.company_id,
            actor_user_id=actor_user.id,
            event_type="manual_employee.activation_sent",
            title=f"Activation link prepared for {employee.full_name}",
            target_entity_type="employee_invitation",
            target_entity_id=invitation.id,
            related_entity_type="employee",
            related_entity_id=employee.id,
            metadata={"employee_id": str(employee.id), "invited_email": email, "delivery": delivery},
        )
        return invitation, cls.acceptance_url(token), delivery

    @classmethod
    def list_company_invitations(
        cls,
        db: Session,
        *,
        company_id: UUID,
        status_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[EmployeeInvitation]:
        statement = select(EmployeeInvitation).where(EmployeeInvitation.company_id == company_id)
        if status_filter:
            statement = statement.where(EmployeeInvitation.status == status_filter)
        statement = statement.order_by(EmployeeInvitation.created_at.desc()).limit(limit).offset(offset)
        return list(db.scalars(statement).all())

    @classmethod
    def preview(cls, db: Session, *, token: str) -> EmployeeInvitation:
        return cls._invitation_by_token(db, token)

    @classmethod
    def accept(
        cls,
        db: Session,
        *,
        token: str,
        email: str,
        password: str,
        full_name: str | None = None,
    ) -> tuple[EmployeeInvitation, Employee, User]:
        invitation = cls._invitation_by_token(db, token)
        if invitation.status not in {INVITATION_PENDING, INVITATION_ACTIVATION_SENT}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invitation cannot be accepted in its current state")
        normalized_email = cls._ensure_invited_email(invitation, email)
        employee = db.get(Employee, invitation.employee_id) if invitation.employee_id else None
        if employee is None or employee.company_id != invitation.company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee profile not found")

        user = db.scalar(select(User).where(User.email == normalized_email))
        if user is not None:
            if user.company_id != invitation.company_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invitation email does not match this company")
            if user.role != invitation.invited_role:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Existing account role does not match this invitation")
            if not verify_password(password, user.password_hash):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        else:
            user = User(
                company_id=invitation.company_id,
                full_name=full_name or employee.full_name,
                email=normalized_email,
                password_hash=hash_password(password),
                role=invitation.invited_role,
                auth_provider="local",
                is_active=False,
            )
            db.add(user)
            db.flush()

        if employee.user_id is not None and employee.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee already has a linked user account")

        employee.user_id = user.id
        employee.email = normalized_email
        employee.account_status = "profile_pending"
        employee.activation_status = "accepted"
        employee.profile_completion_status = "needs_completion"
        user.role = invitation.invited_role
        user.is_active = False
        if full_name:
            employee.full_name = full_name
            user.full_name = full_name

        invitation.status = INVITATION_ACCEPTED
        invitation.accepted_at = utc_now()
        event_type = "manual_employee.activation_accepted" if invitation.invite_source == "manual_add" else "employee_invite.accepted"
        EventService.record_event(
            db,
            company_id=invitation.company_id,
            actor_user_id=user.id,
            event_type=event_type,
            title=f"{employee.full_name} accepted onboarding",
            target_entity_type="employee_invitation",
            target_entity_id=invitation.id,
            related_entity_type="employee",
            related_entity_id=employee.id,
            metadata={"employee_id": str(employee.id), "approval_required": invitation.approval_required},
        )
        EventService.record_event(
            db,
            company_id=invitation.company_id,
            actor_user_id=user.id,
            event_type="employee_account.linked",
            title=f"{employee.full_name} linked an account",
            target_entity_type="employee",
            target_entity_id=employee.id,
            related_entity_type="user",
            related_entity_id=user.id,
        )
        return invitation, employee, user

    @classmethod
    def complete_profile(
        cls,
        db: Session,
        *,
        payload: InvitationProfileCompleteRequest,
    ) -> tuple[EmployeeInvitation, Employee, User, Company]:
        invitation = cls._invitation_by_token(db, payload.token)
        if invitation.status != INVITATION_ACCEPTED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invitation must be accepted before profile completion")
        normalized_email = cls._ensure_invited_email(invitation, str(payload.email))
        employee = db.get(Employee, invitation.employee_id) if invitation.employee_id else None
        if employee is None or employee.company_id != invitation.company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee profile not found")
        user = db.get(User, employee.user_id) if employee.user_id else None
        if user is None or user.email != normalized_email or user.company_id != invitation.company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked user account not found")
        if employee.account_status != "profile_pending" or employee.profile_completion_status != "needs_completion":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Employee profile has already been completed or submitted")
        company = cls._company(db, invitation.company_id)

        if payload.full_name:
            employee.full_name = payload.full_name
            user.full_name = payload.full_name
        if payload.phone is not None:
            employee.phone = payload.phone
        if payload.location is not None:
            employee.location = payload.location
        if payload.profile_image_url is not None:
            employee.profile_image_url = payload.profile_image_url
        if payload.skills is not None:
            employee.skills = payload.skills

        profile_metadata = metadata_dict(employee.metadata_json)
        profile_metadata.update(metadata_dict(payload.metadata))
        if payload.bio is not None:
            profile_metadata["bio"] = payload.bio
        if payload.emergency_contact_name is not None or payload.emergency_contact_phone is not None:
            profile_metadata["emergency_contact"] = {
                "name": payload.emergency_contact_name,
                "phone": payload.emergency_contact_phone,
            }
        employee.metadata_json = profile_metadata

        if invitation.approval_required:
            invitation.status = INVITATION_SUBMITTED
            employee.account_status = "pending_approval"
            employee.profile_completion_status = "submitted_for_approval"
            user.is_active = False
            event = EventService.record_event(
                db,
                company_id=company.id,
                actor_user_id=user.id,
                event_type="employee_profile.submitted",
                title=f"{employee.full_name} submitted a profile",
                target_entity_type="employee",
                target_entity_id=employee.id,
                related_entity_type="employee_invitation",
                related_entity_id=invitation.id,
            )
            NotificationService.create_for_owner_admins(
                db,
                company_id=company.id,
                title="Employee profile approval needed",
                message=f"{employee.full_name} submitted onboarding details for approval.",
                notification_type="employee_profile.approval_needed",
                actor_user_id=user.id,
                event_id=event.id,
                target_entity_type="employee",
                target_entity_id=employee.id,
                priority="normal",
            )
        else:
            user.is_active = True
            employee.is_active = True
            employee.account_status = "active"
            employee.activation_status = "activated"
            employee.profile_completion_status = "complete"
            EventService.record_event(
                db,
                company_id=company.id,
                actor_user_id=user.id,
                event_type="employee_profile.updated",
                title=f"{employee.full_name} completed a profile",
                target_entity_type="employee",
                target_entity_id=employee.id,
                related_entity_type="employee_invitation",
                related_entity_id=invitation.id,
            )
            EventService.record_event(
                db,
                company_id=company.id,
                actor_user_id=user.id,
                event_type="employee.joined",
                title=f"{employee.full_name} joined FebGrid",
                target_entity_type="employee",
                target_entity_id=employee.id,
                related_entity_type="user",
                related_entity_id=user.id,
            )
        return invitation, employee, user, company

    @classmethod
    def get_company_invitation(cls, db: Session, *, company_id: UUID, invitation_id: UUID) -> EmployeeInvitation:
        invitation = db.get(EmployeeInvitation, invitation_id)
        if invitation is None or invitation.company_id != company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
        return invitation

    @classmethod
    def resend(
        cls,
        db: Session,
        *,
        invitation: EmployeeInvitation,
        actor_user: User,
        expires_in_hours: int = 168,
    ) -> tuple[EmployeeInvitation, str, dict[str, Any]]:
        if invitation.status not in RESENDABLE_STATUSES:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invitation cannot be resent in its current state")
        token = cls.issue_token(invitation, expires_in_hours=expires_in_hours)
        if invitation.status == INVITATION_EXPIRED:
            invitation.status = INVITATION_ACTIVATION_SENT if invitation.invite_source == "manual_add" else INVITATION_PENDING
        delivery = cls._delivery_metadata(
            invitation,
            token=token,
            template="manual_employee_activation" if invitation.invite_source == "manual_add" else "employee_invitation",
        )
        invitation.metadata_json = {**metadata_dict(invitation.metadata_json), "email_delivery": delivery}
        EventService.record_event(
            db,
            company_id=invitation.company_id,
            actor_user_id=actor_user.id,
            event_type="employee_invite.resent",
            title=f"Invitation resent to {invitation.invited_email}",
            target_entity_type="employee_invitation",
            target_entity_id=invitation.id,
            related_entity_type="employee",
            related_entity_id=invitation.employee_id,
            metadata={"delivery": delivery, "invite_source": invitation.invite_source},
        )
        return invitation, cls.acceptance_url(token), delivery

    @classmethod
    def revoke(cls, db: Session, *, invitation: EmployeeInvitation, actor_user: User) -> EmployeeInvitation:
        if invitation.status in FINAL_INVITATION_STATUSES or invitation.status == INVITATION_SUBMITTED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invitation cannot be revoked in its current state")
        invitation.status = INVITATION_REVOKED
        invitation.revoked_at = utc_now()
        invitation.revoked_by_user_id = actor_user.id
        if invitation.employee_id is not None:
            employee = db.get(Employee, invitation.employee_id)
            if employee is not None and employee.company_id == invitation.company_id and employee.user_id is None:
                employee.activation_status = "revoked"
                employee.account_status = "activation_revoked"
        EventService.record_event(
            db,
            company_id=invitation.company_id,
            actor_user_id=actor_user.id,
            event_type="employee_invite.revoked",
            title=f"Invitation revoked for {invitation.invited_email}",
            target_entity_type="employee_invitation",
            target_entity_id=invitation.id,
            related_entity_type="employee",
            related_entity_id=invitation.employee_id,
        )
        return invitation

    @classmethod
    def approve(cls, db: Session, *, invitation: EmployeeInvitation, actor_user: User) -> tuple[EmployeeInvitation, Employee, User]:
        if invitation.status != INVITATION_SUBMITTED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only submitted profiles can be approved")
        employee = db.get(Employee, invitation.employee_id) if invitation.employee_id else None
        if employee is None or employee.company_id != invitation.company_id or employee.user_id is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked employee profile not found")
        user = db.get(User, employee.user_id)
        if user is None or user.company_id != invitation.company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked user account not found")
        invitation.status = INVITATION_APPROVED
        invitation.approved_at = utc_now()
        invitation.approved_by_user_id = actor_user.id
        user.is_active = True
        employee.is_active = True
        employee.account_status = "active"
        employee.activation_status = "activated"
        employee.profile_completion_status = "complete"
        event = EventService.record_event(
            db,
            company_id=invitation.company_id,
            actor_user_id=actor_user.id,
            event_type="employee_profile.approved",
            title=f"{employee.full_name} approved",
            target_entity_type="employee",
            target_entity_id=employee.id,
            related_entity_type="employee_invitation",
            related_entity_id=invitation.id,
        )
        EventService.record_event(
            db,
            company_id=invitation.company_id,
            actor_user_id=user.id,
            event_type="employee.joined",
            title=f"{employee.full_name} joined FebGrid",
            target_entity_type="employee",
            target_entity_id=employee.id,
            related_entity_type="user",
            related_entity_id=user.id,
        )
        NotificationService.create_notification(
            db,
            company_id=invitation.company_id,
            recipient_user_id=user.id,
            recipient_employee_id=employee.id,
            actor_user_id=actor_user.id,
            event_id=event.id,
            notification_type="employee_profile.approved",
            title="Your FebGrid profile was approved",
            message="Your employee account is active.",
            target_entity_type="employee",
            target_entity_id=employee.id,
            priority="normal",
        )
        return invitation, employee, user

    @classmethod
    def reject(
        cls,
        db: Session,
        *,
        invitation: EmployeeInvitation,
        actor_user: User,
        reason: str | None = None,
    ) -> tuple[EmployeeInvitation, Employee, User | None]:
        if invitation.status != INVITATION_SUBMITTED:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only submitted profiles can be rejected")
        employee = db.get(Employee, invitation.employee_id) if invitation.employee_id else None
        if employee is None or employee.company_id != invitation.company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked employee profile not found")
        user = db.get(User, employee.user_id) if employee.user_id else None
        invitation.status = INVITATION_REJECTED
        invitation.rejected_at = utc_now()
        invitation.rejected_by_user_id = actor_user.id
        invitation.rejection_reason = reason
        employee.account_status = "rejected"
        employee.profile_completion_status = "rejected"
        if user is not None:
            user.is_active = False
        event = EventService.record_event(
            db,
            company_id=invitation.company_id,
            actor_user_id=actor_user.id,
            event_type="employee_profile.rejected",
            title=f"{employee.full_name} rejected",
            target_entity_type="employee",
            target_entity_id=employee.id,
            related_entity_type="employee_invitation",
            related_entity_id=invitation.id,
            metadata={"reason": reason},
        )
        if user is not None:
            NotificationService.create_notification(
                db,
                company_id=invitation.company_id,
                recipient_user_id=user.id,
                recipient_employee_id=employee.id,
                actor_user_id=actor_user.id,
                event_id=event.id,
                notification_type="employee_profile.rejected",
                title="Your FebGrid profile needs review",
                message=reason or "Your employee profile was not approved yet.",
                target_entity_type="employee",
                target_entity_id=employee.id,
                priority="normal",
            )
        return invitation, employee, user
