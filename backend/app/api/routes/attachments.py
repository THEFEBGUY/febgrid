from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.api.utils import ensure_company, get_or_404, update_model
from app.models.ai_job import AIJob
from app.models.attachment import Attachment
from app.models.company import Company
from app.models.employee import Employee
from app.models.event import Event
from app.models.leave_request import LeaveRequest
from app.models.notification import Notification
from app.models.project import Project
from app.models.team import Team
from app.models.work_object import WorkObject
from app.schemas.attachment import AttachmentCreate, AttachmentRead, AttachmentUpdate
from app.services.event_service import EventService
from app.services.file_service import FileService

router = APIRouter(prefix="/attachments", tags=["attachments"])
uploads_router = APIRouter(prefix="/uploads", tags=["attachments"])
files_router = APIRouter(prefix="/files", tags=["attachments"])

LINKED_MODELS = {
    "employee": Employee,
    "team": Team,
    "project": Project,
    "work_object": WorkObject,
    "leave_request": LeaveRequest,
    "event": Event,
    "notification": Notification,
    "ai_job": AIJob,
}


def validate_linked_entity(db: Session, payload: AttachmentCreate) -> None:
    if payload.linked_entity_type == "company":
        get_or_404(db, Company, payload.linked_entity_id, label="Company")
        if payload.linked_entity_id != payload.company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        return

    model = LINKED_MODELS.get(payload.linked_entity_type)
    if model is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported linked_entity_type")
    entity = get_or_404(db, model, payload.linked_entity_id, label="Linked entity")
    ensure_company(entity, payload.company_id, label="Linked entity")


@router.post("", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
def create_attachment(payload: AttachmentCreate, db: Session = Depends(db_session)) -> Attachment:
    get_or_404(db, Company, payload.company_id, label="Company")
    if payload.uploaded_by_employee_id:
        uploader = get_or_404(db, Employee, payload.uploaded_by_employee_id, label="Uploader")
        ensure_company(uploader, payload.company_id, label="Uploader")
    validate_linked_entity(db, payload)
    attachment = FileService.build_attachment(payload)
    db.add(attachment)
    db.flush()
    EventService.record_event(
        db,
        company_id=payload.company_id,
        actor_employee_id=payload.uploaded_by_employee_id,
        event_type="attachment.created",
        title=f"{payload.file_name} uploaded",
        target_entity_type=payload.linked_entity_type,
        target_entity_id=payload.linked_entity_id,
        metadata={"attachment_id": str(attachment.id), "file_type": payload.file_type},
    )
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("", response_model=list[AttachmentRead])
def list_attachments(
    company_id: UUID,
    db: Session = Depends(db_session),
    linked_entity_type: str | None = None,
    linked_entity_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Attachment]:
    statement = select(Attachment).where(Attachment.company_id == company_id)
    if linked_entity_type:
        statement = statement.where(Attachment.linked_entity_type == linked_entity_type)
    if linked_entity_id:
        statement = statement.where(Attachment.linked_entity_id == linked_entity_id)
    statement = statement.order_by(Attachment.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@router.get("/{attachment_id}", response_model=AttachmentRead)
def get_attachment(attachment_id: UUID, company_id: UUID, db: Session = Depends(db_session)) -> Attachment:
    attachment = get_or_404(db, Attachment, attachment_id, label="Attachment")
    ensure_company(attachment, company_id, label="Attachment")
    return attachment


@router.put("/{attachment_id}", response_model=AttachmentRead)
def update_attachment(
    attachment_id: UUID,
    company_id: UUID,
    payload: AttachmentUpdate,
    db: Session = Depends(db_session),
) -> Attachment:
    attachment = get_or_404(db, Attachment, attachment_id, label="Attachment")
    ensure_company(attachment, company_id, label="Attachment")
    changed = update_model(attachment, payload, alias_fields={"metadata": "metadata_json"})
    if changed:
        EventService.record_event(
            db,
            company_id=company_id,
            actor_employee_id=attachment.uploaded_by_employee_id,
            event_type="attachment.updated",
            title=f"{attachment.file_name} updated",
            target_entity_type=attachment.linked_entity_type,
            target_entity_id=attachment.linked_entity_id,
            metadata={"attachment_id": str(attachment.id), "changed_fields": sorted(changed.keys())},
        )
    db.commit()
    db.refresh(attachment)
    return attachment


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: UUID,
    company_id: UUID,
    actor_employee_id: UUID | None = None,
    db: Session = Depends(db_session),
) -> Response:
    attachment = get_or_404(db, Attachment, attachment_id, label="Attachment")
    ensure_company(attachment, company_id, label="Attachment")
    EventService.record_event(
        db,
        company_id=company_id,
        actor_employee_id=actor_employee_id,
        event_type="attachment.deleted",
        title=f"{attachment.file_name} deleted",
        target_entity_type=attachment.linked_entity_type,
        target_entity_id=attachment.linked_entity_id,
        metadata={"attachment_id": str(attachment.id)},
    )
    db.delete(attachment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@uploads_router.post("", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
def upload_file_metadata(payload: AttachmentCreate, db: Session = Depends(db_session)) -> Attachment:
    return create_attachment(payload, db)


@files_router.get("", response_model=list[AttachmentRead])
def list_files(
    company_id: UUID,
    db: Session = Depends(db_session),
    linked_entity_type: str | None = None,
    linked_entity_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Attachment]:
    return list_attachments(company_id, db, linked_entity_type, linked_entity_id, limit, offset)


@files_router.get("/{attachment_id}", response_model=AttachmentRead)
def get_file(attachment_id: UUID, company_id: UUID, db: Session = Depends(db_session)) -> Attachment:
    return get_attachment(attachment_id, company_id, db)
