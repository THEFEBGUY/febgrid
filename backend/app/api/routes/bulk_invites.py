from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.core.config import get_settings
from app.core.permissions import OWNER_ADMIN_ROLES, ensure_company_access, ensure_role
from app.models.company import Company
from app.models.user import User
from app.schemas.bulk_invite import BulkInvitePreviewRead
from app.services.bulk_invite_preview_service import BulkInvitePreviewService
from app.services.java_bulk_invite_client import JavaBulkInviteClient, JavaBulkInviteClientError


router = APIRouter(prefix="/companies/{company_id}/bulk-invites", tags=["bulk employee invitations"])

CSV_TEMPLATE = (
    "email,full_name,job_title,role,department,team,manager_email,employment_type,phone,employee_code\n"
    "rahul@example.com,Rahul Patil,Backend Developer,employee,Software Engineering,Backend,manager@example.com,full_time,+919999999999,EMP-001\n"
    "priya@example.com,Priya Shah,UI Designer,employee,Design,Product Design,manager@example.com,full_time,+918888888888,EMP-002\n"
)
ALLOWED_CSV_CONTENT_TYPES = {"text/csv", "application/csv", "text/plain", "application/vnd.ms-excel"}


def ensure_bulk_invite_access(db: Session, *, company_id: UUID, current_user: User) -> Company:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    company = db.get(Company, company_id)
    if company is None or not company.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


def validate_upload(file: UploadFile, *, max_bytes: int) -> tuple[str, bytes]:
    file_name = (file.filename or "").replace("\\", "/").split("/")[-1].strip()
    if not file_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="BULK_INVITE_FILE_REQUIRED")
    if not file_name.lower().endswith(".csv") or (file.content_type and file.content_type.lower() not in ALLOWED_CSV_CONTENT_TYPES):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="BULK_INVITE_UNSUPPORTED_FILE")
    content = file.file.read(max_bytes + 1)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="BULK_INVITE_FILE_REQUIRED")
    if len(content) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="BULK_INVITE_FILE_TOO_LARGE")
    return file_name, content


@router.get("/template")
def download_bulk_invite_template(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    ensure_bulk_invite_access(db, company_id=company_id, current_user=current_user)
    return Response(
        content=CSV_TEMPLATE,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="febgrid-bulk-invite-template.csv"'},
    )


@router.post("/preview", response_model=BulkInvitePreviewRead)
def preview_bulk_invites(
    company_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> BulkInvitePreviewRead:
    ensure_bulk_invite_access(db, company_id=company_id, current_user=current_user)
    settings = get_settings()
    file_name, content = validate_upload(file, max_bytes=settings.bulk_invite_max_file_bytes)
    try:
        validation = JavaBulkInviteClient(settings).validate_csv(
            file_name=file_name,
            content=content,
            request_id=uuid4(),
        )
    except JavaBulkInviteClientError as error:
        raise HTTPException(status_code=error.status_code, detail=error.code) from None

    preview = BulkInvitePreviewService.build_preview(
        db,
        company_id=company_id,
        actor_user=current_user,
        validation=validation,
    )
    BulkInvitePreviewService.record_preview_event(db, preview=preview, actor_user=current_user)
    db.commit()
    return preview
