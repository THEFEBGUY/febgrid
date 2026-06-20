from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_optional_current_user
from app.api.serializers import serialize_events
from app.api.utils import ensure_company, get_or_404, update_model
from app.core.permissions import MANAGER_ROLES, ensure_company_access, ensure_role
from app.models.attachment import Attachment
from app.models.company import Company
from app.models.employee import Employee
from app.models.event import Event
from app.models.project import Project
from app.models.user import User
from app.models.work_object import WorkObject
from app.schemas.attachment import AttachmentCreate, AttachmentRead, WorkObjectAttachmentCreate
from app.schemas.event import EventRead
from app.schemas.work_object import WorkObjectCreate, WorkObjectRead, WorkObjectStatusUpdate, WorkObjectUpdate
from app.services.event_service import EventService
from app.services.file_service import FileService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/work-objects", tags=["work-objects"])


def validate_work_object_refs(db: Session, payload: WorkObjectCreate | WorkObjectUpdate, company_id: UUID) -> None:
    if getattr(payload, "project_id", None):
        project = get_or_404(db, Project, payload.project_id, label="Project")
        ensure_company(project, company_id, label="Project")
    if getattr(payload, "created_by_employee_id", None):
        creator = get_or_404(db, Employee, payload.created_by_employee_id, label="Creator")
        ensure_company(creator, company_id, label="Creator")
    if getattr(payload, "assigned_to_employee_id", None):
        assignee = get_or_404(db, Employee, payload.assigned_to_employee_id, label="Assignee")
        ensure_company(assignee, company_id, label="Assignee")


@router.post("", response_model=WorkObjectRead, status_code=status.HTTP_201_CREATED)
def create_work_object(
    payload: WorkObjectCreate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObject:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, MANAGER_ROLES)
    get_or_404(db, Company, payload.company_id, label="Company")
    validate_work_object_refs(db, payload, payload.company_id)
    work_object = WorkObject(**payload.model_dump())
    db.add(work_object)
    db.flush()
    EventService.record_event(
        db,
        company_id=work_object.company_id,
        actor_employee_id=work_object.created_by_employee_id,
        event_type="work_object.created",
        title=f"{work_object.title} created",
        target_entity_type="work_object",
        target_entity_id=work_object.id,
        metadata={"object_type": work_object.object_type, "status": work_object.status},
    )
    if work_object.assigned_to_employee_id:
        NotificationService.create_notification(
            db,
            company_id=work_object.company_id,
            recipient_employee_id=work_object.assigned_to_employee_id,
            title="Work assigned",
            message=f"{work_object.title} was assigned to you.",
            notification_type="work_assigned",
            related_entity_type="work_object",
            related_entity_id=work_object.id,
        )
    db.commit()
    db.refresh(work_object)
    return work_object


@router.get("", response_model=list[WorkObjectRead])
def list_work_objects(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    status_filter: str | None = Query(default=None, alias="status"),
    project_id: UUID | None = None,
    assigned_to_employee_id: UUID | None = None,
    object_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[WorkObject]:
    ensure_company_access(current_user, company_id)
    statement = select(WorkObject).where(WorkObject.company_id == company_id)
    if status_filter:
        statement = statement.where(WorkObject.status == status_filter)
    if project_id:
        statement = statement.where(WorkObject.project_id == project_id)
    if assigned_to_employee_id:
        statement = statement.where(WorkObject.assigned_to_employee_id == assigned_to_employee_id)
    if object_type:
        statement = statement.where(WorkObject.object_type == object_type)
    statement = statement.order_by(WorkObject.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@router.get("/{work_object_id}", response_model=WorkObjectRead)
def get_work_object(
    work_object_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObject:
    ensure_company_access(current_user, company_id)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, company_id, label="Work object")
    return work_object


@router.put("/{work_object_id}", response_model=WorkObjectRead)
def update_work_object(
    work_object_id: UUID,
    company_id: UUID,
    payload: WorkObjectUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObject:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, MANAGER_ROLES)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, company_id, label="Work object")
    validate_work_object_refs(db, payload, company_id)
    old_assignee = work_object.assigned_to_employee_id
    changed = update_model(work_object, payload)
    if changed:
        EventService.record_event(
            db,
            company_id=company_id,
            actor_employee_id=work_object.created_by_employee_id,
            event_type="work_object.updated",
            title=f"{work_object.title} updated",
            target_entity_type="work_object",
            target_entity_id=work_object.id,
            metadata={"changed_fields": sorted(changed.keys())},
        )
    if work_object.assigned_to_employee_id and work_object.assigned_to_employee_id != old_assignee:
        NotificationService.create_notification(
            db,
            company_id=company_id,
            recipient_employee_id=work_object.assigned_to_employee_id,
            title="Work reassigned",
            message=f"{work_object.title} was assigned to you.",
            notification_type="work_assigned",
            related_entity_type="work_object",
            related_entity_id=work_object.id,
        )
    db.commit()
    db.refresh(work_object)
    return work_object


@router.delete("/{work_object_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_object(
    work_object_id: UUID,
    company_id: UUID,
    actor_employee_id: UUID | None = None,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Response:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, MANAGER_ROLES)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, company_id, label="Work object")
    EventService.record_event(
        db,
        company_id=company_id,
        actor_employee_id=actor_employee_id,
        event_type="work_object.deleted",
        title=f"{work_object.title} deleted",
        target_entity_type="work_object",
        target_entity_id=work_object.id,
    )
    db.delete(work_object)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{work_object_id}/status", response_model=WorkObjectRead)
def update_work_object_status(
    work_object_id: UUID,
    payload: WorkObjectStatusUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObject:
    ensure_company_access(current_user, payload.company_id)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, payload.company_id, label="Work object")
    old_status = work_object.status
    work_object.status = payload.status
    EventService.record_event(
        db,
        company_id=payload.company_id,
        actor_employee_id=payload.actor_employee_id,
        event_type="work_object.status_changed",
        title=f"{work_object.title} status changed",
        target_entity_type="work_object",
        target_entity_id=work_object.id,
        metadata={"from": old_status, "to": payload.status},
    )
    db.commit()
    db.refresh(work_object)
    return work_object


@router.get("/{work_object_id}/timeline", response_model=list[EventRead])
def get_work_object_timeline(
    work_object_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[EventRead]:
    ensure_company_access(current_user, company_id)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, company_id, label="Work object")
    statement = (
        select(Event)
        .where(
            Event.company_id == company_id,
            Event.target_entity_type == "work_object",
            Event.target_entity_id == work_object_id,
        )
        .order_by(Event.created_at.desc())
        .limit(limit)
    )
    return serialize_events(db.scalars(statement).all())


@router.post("/{work_object_id}/attachments", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
def add_work_object_attachment(
    work_object_id: UUID,
    payload: WorkObjectAttachmentCreate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Attachment:
    ensure_company_access(current_user, payload.company_id)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, payload.company_id, label="Work object")
    attachment_payload = AttachmentCreate(
        **payload.model_dump(),
        linked_entity_type="work_object",
        linked_entity_id=work_object_id,
    )
    attachment = FileService.build_attachment(attachment_payload)
    db.add(attachment)
    db.flush()
    EventService.record_event(
        db,
        company_id=payload.company_id,
        actor_employee_id=payload.uploaded_by_employee_id,
        event_type="attachment.created",
        title=f"{payload.file_name} attached",
        target_entity_type="work_object",
        target_entity_id=work_object_id,
        metadata={"attachment_id": str(attachment.id), "file_type": payload.file_type},
    )
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/{work_object_id}/attachments", response_model=list[AttachmentRead])
def list_work_object_attachments(
    work_object_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Attachment]:
    ensure_company_access(current_user, company_id)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, company_id, label="Work object")
    statement = (
        select(Attachment)
        .where(
            Attachment.company_id == company_id,
            Attachment.linked_entity_type == "work_object",
            Attachment.linked_entity_id == work_object_id,
        )
        .order_by(Attachment.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())
