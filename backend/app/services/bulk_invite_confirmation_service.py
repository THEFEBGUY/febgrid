from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import decode_bulk_invite_preview_token
from app.models.bulk_invite_operation import BulkInviteOperation
from app.models.user import User
from app.schemas.bulk_invite import BulkInviteConfirmRead, BulkInviteConfirmRequest, BulkInviteConfirmRowResult, BulkInvitePreviewRow
from app.schemas.invitation import EmployeeInvitationCreate
from app.services.bulk_invite_preview_service import BulkInvitePreviewService, INVITABLE_ROLES, _lookup_key
from app.services.event_service import EventService
from app.services.invitation_service import InvitationService


class BulkInviteConfirmationService:
    """Confirm a signed preview through the existing invitation service only."""

    @classmethod
    def confirm(
        cls,
        db: Session,
        *,
        company_id: UUID,
        actor_user: User,
        payload: BulkInviteConfirmRequest,
    ) -> BulkInviteConfirmRead:
        token = decode_bulk_invite_preview_token(payload.preview_token)
        rows_hash = BulkInvitePreviewService.normalized_rows_hash(payload.rows)
        if token.get("company_id") != str(company_id) or token.get("sub") != str(actor_user.id) or token.get("rows_hash") != rows_hash:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="BULK_INVITE_PREVIEW_MISMATCH")

        operation = db.scalar(
            select(BulkInviteOperation).where(
                BulkInviteOperation.company_id == company_id,
                BulkInviteOperation.actor_user_id == actor_user.id,
                BulkInviteOperation.idempotency_key == payload.idempotency_key,
            )
        )
        if operation is not None:
            if operation.request_hash != rows_hash:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="BULK_INVITE_PREVIEW_MISMATCH")
            if operation.status == "processing":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="BULK_INVITE_CONFIRMATION_IN_PROGRESS")
            return cls._replay(operation)

        operation = BulkInviteOperation(
            company_id=company_id,
            actor_user_id=actor_user.id,
            idempotency_key=payload.idempotency_key,
            request_hash=rows_hash,
            file_name=payload.file_name,
            total_rows=len(payload.rows),
            valid_rows=sum(row.status == "VALID" for row in payload.rows),
            status="processing",
        )
        try:
            # The unique key is the final guard against a double-submit race
            # from two browser requests sharing one idempotency key.
            with db.begin_nested():
                db.add(operation)
                db.flush()
        except IntegrityError:
            operation = db.scalar(
                select(BulkInviteOperation).where(
                    BulkInviteOperation.company_id == company_id,
                    BulkInviteOperation.actor_user_id == actor_user.id,
                    BulkInviteOperation.idempotency_key == payload.idempotency_key,
                )
            )
            if operation is None or operation.request_hash != rows_hash:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="BULK_INVITE_PREVIEW_MISMATCH")
            if operation.status == "processing":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="BULK_INVITE_CONFIRMATION_IN_PROGRESS")
            return cls._replay(operation)
        EventService.record_event(
            db,
            company_id=company_id,
            actor_user_id=actor_user.id,
            event_type="bulk_invite_confirmed",
            title="Bulk employee invitation confirmed",
            target_entity_type="bulk_invite_operation",
            target_entity_id=operation.id,
            metadata={"total_rows": operation.total_rows, "valid_rows": operation.valid_rows},
        )

        context = BulkInvitePreviewService._load_context(db, company_id=company_id)
        results = [
            cls._process_row(
                db,
                company_id=company_id,
                actor_user=actor_user,
                operation=operation,
                row=row,
                approval_required=payload.approval_required,
                context=context,
            )
            for row in payload.rows
        ]
        operation.invited_rows = sum(result.status == "INVITED" for result in results)
        operation.skipped_rows = sum(result.status.startswith("SKIPPED_") for result in results)
        operation.failed_rows = sum(result.status.startswith("FAILED_") for result in results)
        operation.status = "completed" if operation.failed_rows == 0 else "partially_failed"
        operation.completed_at = datetime.now(timezone.utc)
        EventService.record_event(
            db,
            company_id=company_id,
            actor_user_id=actor_user.id,
            event_type="bulk_invite_completed" if operation.failed_rows == 0 else "bulk_invite_partially_failed",
            title="Bulk employee invitation completed",
            target_entity_type="bulk_invite_operation",
            target_entity_id=operation.id,
            metadata={
                "invited_rows": operation.invited_rows,
                "skipped_rows": operation.skipped_rows,
                "failed_rows": operation.failed_rows,
            },
        )
        return BulkInviteConfirmRead(
            operation_id=operation.id,
            company_id=company_id,
            status=operation.status,
            total_rows=operation.total_rows,
            invited_rows=operation.invited_rows,
            skipped_rows=operation.skipped_rows,
            failed_rows=operation.failed_rows,
            rows=results,
        )

    @classmethod
    def _process_row(
        cls,
        db: Session,
        *,
        company_id: UUID,
        actor_user: User,
        operation: BulkInviteOperation,
        row: BulkInvitePreviewRow,
        approval_required: bool,
        context: dict[str, dict[str, object]],
    ) -> BulkInviteConfirmRowResult:
        email = row.normalized.email
        if row.status == "DUPLICATE":
            return cls._result(row, "SKIPPED_DUPLICATE_CSV_ROW", "Duplicate email in the CSV was skipped")
        if row.status == "EXISTING_EMPLOYEE":
            return cls._result(row, "SKIPPED_EXISTING_EMPLOYEE", "Employee already exists and was skipped")
        if row.status == "EXISTING_INVITATION":
            return cls._result(row, "SKIPPED_ACTIVE_INVITATION", "An active invitation already exists and was skipped")
        if row.status != "VALID":
            return cls._result(row, "FAILED_VALIDATION", "Row did not pass preview validation")

        validation_error = cls._revalidate(row, context=context)
        if validation_error is not None:
            return cls._result(row, validation_error[0], validation_error[1])

        department = context["departments"].get(_lookup_key(row.normalized.department)) if row.normalized.department else None
        team = context["teams"].get(_lookup_key(row.normalized.team)) if row.normalized.team else None
        manager = context["managers"].get(_lookup_key(row.normalized.manager_email)) if row.normalized.manager_email else None
        invite_payload = EmployeeInvitationCreate(
            company_id=company_id,
            invited_email=email,
            invited_role=row.normalized.role,
            full_name=row.normalized.full_name,
            department_id=department.id if department is not None else None,
            team_id=team.id if team is not None else None,
            manager_employee_id=manager.id if manager is not None else None,
            job_title=row.normalized.job_title,
            employment_type=row.normalized.employment_type or "full_time",
            approval_required=approval_required,
            metadata={
                "employee_code": row.normalized.employee_code or None,
                "bulk_invite_operation_id": str(operation.id),
                "bulk_invite_row_number": row.row_number,
            },
        )
        try:
            with db.begin_nested():
                invitation, acceptance_url, _ = InvitationService.create_invitation(db, payload=invite_payload, actor_user=actor_user)
                EventService.record_event(
                    db,
                    company_id=company_id,
                    actor_user_id=actor_user.id,
                    event_type="employee_invited_via_bulk",
                    title="Employee invited through bulk operation",
                    target_entity_type="employee_invitation",
                    target_entity_id=invitation.id,
                    related_entity_type="bulk_invite_operation",
                    related_entity_id=operation.id,
                    metadata={"row_number": row.row_number},
                )
        except HTTPException as error:
            return cls._result(row, "FAILED_VALIDATION", cls._safe_error_message(error))
        except Exception:
            return cls._result(row, "FAILED_INTERNAL", "Invitation could not be created")

        context["employees"][_lookup_key(email)] = SimpleNamespace(id=invitation.employee_id, email=email)
        context["invitations"][_lookup_key(email)] = invitation
        return BulkInviteConfirmRowResult(
            row_number=row.row_number,
            email=email,
            status="INVITED",
            message="Invitation prepared using the standard onboarding flow",
            invitation_id=invitation.id,
            acceptance_url=acceptance_url,
        )

    @staticmethod
    def _revalidate(row: BulkInvitePreviewRow, *, context: dict[str, dict[str, object]]) -> tuple[str, str] | None:
        normalized = row.normalized
        email = _lookup_key(normalized.email)
        if email in context["employees"]:
            return "SKIPPED_EXISTING_EMPLOYEE", "Employee now exists and was skipped"
        if email in context["invitations"]:
            return "SKIPPED_ACTIVE_INVITATION", "An active invitation now exists and was skipped"
        if normalized.role not in INVITABLE_ROLES:
            return "FAILED_VALIDATION", "Role is no longer allowed for employee invitations"
        department = context["departments"].get(_lookup_key(normalized.department)) if normalized.department else None
        team = context["teams"].get(_lookup_key(normalized.team)) if normalized.team else None
        manager = context["managers"].get(_lookup_key(normalized.manager_email)) if normalized.manager_email else None
        if normalized.department and department is None:
            return "FAILED_VALIDATION", "Department is no longer available"
        if normalized.team and team is None:
            return "FAILED_VALIDATION", "Team is no longer available"
        if department is not None and team is not None and team.department_id is not None and team.department_id != department.id:
            return "FAILED_VALIDATION", "Team no longer matches the selected department"
        if normalized.manager_email and manager is None:
            return "FAILED_VALIDATION", "Manager is no longer available"
        code = _lookup_key(normalized.employee_code) if normalized.employee_code else ""
        if code and code in context["employee_codes"]:
            return "FAILED_VALIDATION", "Employee code is already used"
        return None

    @staticmethod
    def _result(row: BulkInvitePreviewRow, result_status: str, message: str) -> BulkInviteConfirmRowResult:
        return BulkInviteConfirmRowResult(row_number=row.row_number, email=row.normalized.email, status=result_status, message=message)

    @staticmethod
    def _safe_error_message(error: HTTPException) -> str:
        if error.status_code == status.HTTP_409_CONFLICT:
            return "The invitation is no longer eligible"
        if error.status_code in {status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND, status.HTTP_422_UNPROCESSABLE_ENTITY}:
            return "The invitation data is no longer valid"
        return "Invitation could not be created"

    @staticmethod
    def _replay(operation: BulkInviteOperation) -> BulkInviteConfirmRead:
        return BulkInviteConfirmRead(
            operation_id=operation.id,
            company_id=operation.company_id,
            status=operation.status,
            total_rows=operation.total_rows,
            invited_rows=operation.invited_rows,
            skipped_rows=operation.skipped_rows,
            failed_rows=operation.failed_rows,
            idempotent_replay=True,
            rows=[],
        )
