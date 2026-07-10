from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import ALL_ROLES, OWNER_ADMIN_ROLES
from app.core.security import create_bulk_invite_preview_token
from app.models.department import Department
from app.models.employee import Employee
from app.models.employee_invitation import EmployeeInvitation
from app.models.team import Team
from app.models.user import User
from app.schemas.bulk_invite import (
    BulkInviteNormalizedRow,
    BulkInvitePreviewRead,
    BulkInvitePreviewRow,
    BulkInviteValidationIssue,
    JavaBulkInviteValidationResponse,
)
from app.services.event_service import EventService
from app.services.invitation_service import OPEN_INVITATION_STATUSES


PREVIEW_EXPIRY_MINUTES = 20
INVITABLE_ROLES = ALL_ROLES - OWNER_ADMIN_ROLES


def _lookup_key(value: str) -> str:
    return value.strip().casefold()


def _metadata_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _issue(code: str, message: str) -> BulkInviteValidationIssue:
    return BulkInviteValidationIssue(code=code, message=message)


class BulkInvitePreviewService:
    """Enrich Java's structural CSV results using tenant-scoped FebGrid data.

    This is preview-only. It does not create employees, invitations, tokens for
    invitation acceptance, email deliveries, notifications, or database rows.
    """

    @classmethod
    def build_preview(
        cls,
        db: Session,
        *,
        company_id: UUID,
        actor_user: User,
        validation: JavaBulkInviteValidationResponse,
    ) -> BulkInvitePreviewRead:
        context = cls._load_context(db, company_id=company_id)
        employee_code_counts = Counter(
            _lookup_key(row.normalized.employee_code)
            for row in validation.rows
            if row.normalized.employee_code
        )
        rows = [
            cls._enrich_row(
                row,
                context=context,
                employee_code_counts=employee_code_counts,
            )
            for row in validation.rows
        ]
        row_hash = cls._normalized_rows_hash(rows)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=PREVIEW_EXPIRY_MINUTES)
        preview_token = create_bulk_invite_preview_token(
            company_id=company_id,
            user_id=actor_user.id,
            normalized_rows_hash=row_hash,
            expires_in_minutes=PREVIEW_EXPIRY_MINUTES,
        )
        valid_count = sum(row.status == "VALID" for row in rows)
        invalid_count = sum(row.status == "INVALID" for row in rows)
        duplicate_count = sum(row.status == "DUPLICATE" for row in rows)
        existing_employee_count = sum(row.status == "EXISTING_EMPLOYEE" for row in rows)
        existing_invitation_count = sum(row.status == "EXISTING_INVITATION" for row in rows)
        return BulkInvitePreviewRead(
            company_id=company_id,
            file_name=validation.file_name,
            total_rows=len(rows),
            valid_row_count=valid_count,
            invalid_row_count=invalid_count,
            duplicate_row_count=duplicate_count,
            existing_employee_count=existing_employee_count,
            existing_invitation_count=existing_invitation_count,
            preview_token=preview_token,
            preview_expires_at=expires_at,
            rows=rows,
        )

    @staticmethod
    def record_preview_event(db: Session, *, preview: BulkInvitePreviewRead, actor_user: User) -> None:
        EventService.record_event(
            db,
            company_id=preview.company_id,
            actor_user_id=actor_user.id,
            event_type="bulk_invite_preview_generated",
            title="Bulk invite CSV preview generated",
            target_entity_type="company",
            target_entity_id=preview.company_id,
            metadata={
                "total_rows": preview.total_rows,
                "valid_rows": preview.valid_row_count,
                "invalid_rows": preview.invalid_row_count,
                "duplicate_rows": preview.duplicate_row_count,
                "existing_employee_rows": preview.existing_employee_count,
                "existing_invitation_rows": preview.existing_invitation_count,
            },
        )

    @classmethod
    def _load_context(cls, db: Session, *, company_id: UUID) -> dict[str, dict[str, object]]:
        employees = list(db.scalars(select(Employee).where(Employee.company_id == company_id)).all())
        departments = list(
            db.scalars(select(Department).where(Department.company_id == company_id, Department.is_active.is_(True))).all()
        )
        teams = list(db.scalars(select(Team).where(Team.company_id == company_id, Team.is_active.is_(True))).all())
        invitations = list(
            db.scalars(
                select(EmployeeInvitation).where(
                    EmployeeInvitation.company_id == company_id,
                    EmployeeInvitation.status.in_(OPEN_INVITATION_STATUSES),
                )
            ).all()
        )
        employee_by_email = {_lookup_key(employee.email): employee for employee in employees if employee.email}
        manager_by_email = {
            _lookup_key(employee.email): employee
            for employee in employees
            if employee.email and employee.is_active
        }
        employee_by_code = {
            _lookup_key(str(_metadata_dict(employee.metadata_json).get("employee_code", ""))): employee
            for employee in employees
            if _metadata_dict(employee.metadata_json).get("employee_code")
        }
        return {
            "employees": employee_by_email,
            "managers": manager_by_email,
            "employee_codes": employee_by_code,
            "departments": {_lookup_key(department.name): department for department in departments},
            "teams": {_lookup_key(team.name): team for team in teams},
            "invitations": {_lookup_key(invitation.normalized_email): invitation for invitation in invitations},
        }

    @classmethod
    def _enrich_row(
        cls,
        row,
        *,
        context: dict[str, dict[str, object]],
        employee_code_counts: Counter[str],
    ) -> BulkInvitePreviewRow:
        errors = list(row.errors)
        warnings = list(row.warnings)
        normalized: BulkInviteNormalizedRow = row.normalized
        department = context["departments"].get(_lookup_key(normalized.department)) if normalized.department else None
        team = context["teams"].get(_lookup_key(normalized.team)) if normalized.team else None
        manager = context["managers"].get(_lookup_key(normalized.manager_email)) if normalized.manager_email else None

        if row.status == "VALID":
            if normalized.role not in INVITABLE_ROLES:
                errors.append(_issue("INVALID_ROLE", "Role is not allowed for employee invitations"))
            if normalized.department and department is None:
                errors.append(_issue("DEPARTMENT_NOT_FOUND", "Department was not found in this company"))
            if normalized.team and team is None:
                errors.append(_issue("TEAM_NOT_FOUND", "Team was not found in this company"))
            if department is not None and team is not None and team.department_id is not None and team.department_id != department.id:
                errors.append(_issue("TEAM_DEPARTMENT_MISMATCH", "Team does not belong to the selected department"))
            if normalized.manager_email and manager is None:
                errors.append(_issue("MANAGER_NOT_FOUND", "Active manager was not found in this company"))
            code_key = _lookup_key(normalized.employee_code) if normalized.employee_code else ""
            if code_key and employee_code_counts[code_key] > 1:
                errors.append(_issue("DUPLICATE_EMPLOYEE_CODE", "Employee code appears more than once in this CSV"))
            if code_key and code_key in context["employee_codes"]:
                errors.append(_issue("EMPLOYEE_CODE_EXISTS", "Employee code is already used in this company"))

        status = row.status
        email_key = _lookup_key(normalized.email)
        if status == "VALID" and errors:
            status = "INVALID"
        if status == "VALID" and email_key in context["employees"]:
            status = "EXISTING_EMPLOYEE"
            warnings.append(_issue("EXISTING_EMPLOYEE", "An employee profile already exists for this email"))
        if status == "VALID" and email_key in context["invitations"]:
            status = "EXISTING_INVITATION"
            warnings.append(_issue("EXISTING_INVITATION", "An active invitation already exists for this email"))

        return BulkInvitePreviewRow(
            row_number=row.row_number,
            status=status,
            normalized=normalized,
            errors=errors,
            warnings=warnings,
            department_id=department.id if department is not None else None,
            team_id=team.id if team is not None else None,
            manager_employee_id=manager.id if manager is not None else None,
        )

    @staticmethod
    def _normalized_rows_hash(rows: list[BulkInvitePreviewRow]) -> str:
        safe_rows = [
            {
                "row_number": row.row_number,
                "status": row.status,
                "normalized": row.normalized.model_dump(mode="json"),
                "department_id": str(row.department_id) if row.department_id else None,
                "team_id": str(row.team_id) if row.team_id else None,
                "manager_employee_id": str(row.manager_employee_id) if row.manager_employee_id else None,
            }
            for row in rows
        ]
        canonical = json.dumps(safe_rows, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
