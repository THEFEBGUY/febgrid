from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from urllib.parse import quote
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user, get_optional_current_user
from app.api.utils import ensure_company, get_or_404
from app.core.permissions import MANAGER_ROLES, ensure_company_access, ensure_role
from app.models.attachment import Attachment
from app.models.company import Company
from app.models.employee import Employee
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.models.work_object import WorkObject
from app.schemas.ai_job import AIJobRead
from app.schemas.attachment import AttachmentCreate, AttachmentRead, AttachmentUpdate
from app.services.ai_service import ai_service
from app.services.event_service import EventService
from app.services.file_service import FileService

router = APIRouter(prefix="/attachments", tags=["attachments"])
uploads_router = APIRouter(prefix="/uploads", tags=["attachments"])
files_router = APIRouter(prefix="/files", tags=["attachments"])


def get_linked_employee(db: Session, current_user: User | None) -> Employee | None:
    if current_user is None:
        return None
    return db.scalar(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.user_id == current_user.id,
            Employee.is_active.is_(True),
        )
    )


def actor_employee_id(db: Session, current_user: User | None, fallback_employee_id: UUID | None = None) -> UUID | None:
    linked_employee = get_linked_employee(db, current_user)
    return linked_employee.id if linked_employee else fallback_employee_id


def can_view_work_object(db: Session, current_user: User | None, work_object: WorkObject) -> bool:
    if current_user is None or current_user.role in MANAGER_ROLES:
        return True
    if work_object.creator_user_id == current_user.id:
        return True
    linked_employee = get_linked_employee(db, current_user)
    if linked_employee is None:
        return False
    return work_object.assignee_employee_id == linked_employee.id or work_object.creator_employee_id == linked_employee.id


def can_view_project(db: Session, current_user: User | None, project: Project) -> bool:
    if current_user is None or current_user.role in MANAGER_ROLES:
        return True
    if project.owner_user_id == current_user.id:
        return True
    linked_employee = get_linked_employee(db, current_user)
    if linked_employee is None:
        return False
    if project.owner_employee_id == linked_employee.id:
        return True
    membership = db.scalar(
        select(ProjectMember.id).where(
            ProjectMember.company_id == project.company_id,
            ProjectMember.project_id == project.id,
            ProjectMember.employee_id == linked_employee.id,
            ProjectMember.is_active.is_(True),
        )
    )
    return membership is not None


def ensure_work_object_visible(db: Session, current_user: User | None, work_object: WorkObject) -> None:
    if not can_view_work_object(db, current_user, work_object):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work object not found")


def ensure_project_visible(db: Session, current_user: User | None, project: Project) -> None:
    if not can_view_project(db, current_user, project):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


def attachment_visibility_conditions(db: Session, current_user: User | None, company_id: UUID) -> list[object]:
    if current_user is None or current_user.role in MANAGER_ROLES:
        return []
    linked_employee = get_linked_employee(db, current_user)
    visible_work_conditions = [WorkObject.creator_user_id == current_user.id]
    conditions: list[object] = [Attachment.uploaded_by_user_id == current_user.id]
    if linked_employee is not None:
        visible_work_conditions.extend(
            [
                WorkObject.assignee_employee_id == linked_employee.id,
                WorkObject.creator_employee_id == linked_employee.id,
            ]
        )
        conditions.append(Attachment.uploaded_by_employee_id == linked_employee.id)
    visible_work_ids = select(WorkObject.id).where(
        WorkObject.company_id == company_id,
        WorkObject.is_active.is_(True),
        or_(*visible_work_conditions),
    )
    conditions.append(Attachment.work_object_id.in_(visible_work_ids))

    visible_project_conditions = [Project.owner_user_id == current_user.id]
    if linked_employee is not None:
        visible_project_conditions.extend(
            [
                Project.owner_employee_id == linked_employee.id,
                Project.id.in_(
                    select(ProjectMember.project_id).where(
                        ProjectMember.company_id == company_id,
                        ProjectMember.employee_id == linked_employee.id,
                        ProjectMember.is_active.is_(True),
                    )
                ),
            ]
        )
    visible_project_ids = select(Project.id).where(
        Project.company_id == company_id,
        Project.is_active.is_(True),
        or_(*visible_project_conditions),
    )
    conditions.append(Attachment.project_id.in_(visible_project_ids))
    return conditions


def validate_attachment_refs(
    db: Session,
    *,
    company_id: UUID,
    work_object_id: UUID | None = None,
    project_id: UUID | None = None,
    uploaded_by_employee_id: UUID | None = None,
    uploaded_by_user_id: UUID | None = None,
) -> None:
    if work_object_id is not None:
        work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
        ensure_company(work_object, company_id, label="Work object")
    if project_id is not None:
        project = get_or_404(db, Project, project_id, label="Project")
        ensure_company(project, company_id, label="Project")
    if uploaded_by_employee_id is not None:
        employee = get_or_404(db, Employee, uploaded_by_employee_id, label="Uploader")
        ensure_company(employee, company_id, label="Uploader")
    if uploaded_by_user_id is not None:
        user = get_or_404(db, User, uploaded_by_user_id, label="Uploader")
        ensure_company_access(user, company_id)


def record_file_event(
    db: Session,
    *,
    attachment: Attachment,
    current_user: User | None,
    event_type: str,
    title: str,
    description: str,
    metadata: dict[str, object] | None = None,
) -> None:
    event_metadata: dict[str, object] = {
        "attachment_id": str(attachment.id),
        "work_object_id": str(attachment.work_object_id) if attachment.work_object_id else None,
        "project_id": str(attachment.project_id) if attachment.project_id else None,
        "content_type": attachment.content_type,
        "file_size": attachment.file_size,
        "extension": attachment.extension,
        "processing_status": attachment.processing_status,
        "scan_status": attachment.scan_status,
    }
    if current_user is not None:
        event_metadata["actor_user_id"] = str(current_user.id)
    if metadata:
        event_metadata.update(metadata)
    EventService.record_event(
        db,
        company_id=attachment.company_id,
        actor_user_id=current_user.id if current_user is not None else None,
        actor_employee_id=actor_employee_id(db, current_user, attachment.uploaded_by_employee_id),
        event_type=event_type,
        title=title,
        description=description,
        target_entity_type="attachment",
        target_entity_id=attachment.id,
        related_entity_type="work_object" if attachment.work_object_id else None,
        related_entity_id=attachment.work_object_id,
        metadata=event_metadata,
    )


def get_attachment_for_user(
    db: Session,
    current_user: User | None,
    *,
    attachment_id: UUID,
    company_id: UUID,
    include_inactive: bool = False,
) -> Attachment:
    ensure_company_access(current_user, company_id)
    attachment = get_or_404(db, Attachment, attachment_id, label="Attachment")
    ensure_company(attachment, company_id, label="Attachment")
    if not include_inactive and (not attachment.is_active or attachment.is_deleted):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    if attachment.work_object_id is not None:
        work_object = get_or_404(db, WorkObject, attachment.work_object_id, label="Work object")
        ensure_company(work_object, company_id, label="Work object")
        ensure_work_object_visible(db, current_user, work_object)
    elif attachment.project_id is not None:
        project = get_or_404(db, Project, attachment.project_id, label="Project")
        ensure_company(project, company_id, label="Project")
        ensure_project_visible(db, current_user, project)
    return attachment


def build_attachment_from_payload(payload: AttachmentCreate) -> Attachment:
    return FileService.build_attachment(payload)


@router.post("", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
def create_attachment_metadata(
    payload: AttachmentCreate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Attachment:
    ensure_company_access(current_user, payload.company_id)
    if payload.storage_provider != FileService.STORAGE_PROVIDER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New attachments must use the configured secure storage provider",
        )
    FileService.ensure_company_storage_path(company_id=payload.company_id, storage_path=payload.storage_path)
    get_or_404(db, Company, payload.company_id, label="Company")
    validate_attachment_refs(
        db,
        company_id=payload.company_id,
        work_object_id=payload.work_object_id,
        project_id=payload.project_id,
        uploaded_by_employee_id=payload.uploaded_by_employee_id,
        uploaded_by_user_id=payload.uploaded_by_user_id,
    )
    attachment = build_attachment_from_payload(payload)
    db.add(attachment)
    db.flush()
    record_file_event(
        db,
        attachment=attachment,
        current_user=current_user,
        event_type="file.uploaded",
        title=f"{attachment.original_file_name} uploaded",
        description="File metadata was created.",
    )
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("", response_model=list[AttachmentRead])
def list_attachments(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    work_object_id: UUID | None = None,
    project_id: UUID | None = None,
    linked_entity_type: str | None = None,
    linked_entity_id: UUID | None = None,
    include_inactive: bool = False,
    include_deleted: bool = False,
    q: str | None = Query(default=None, max_length=200),
    content_type: str | None = None,
    uploaded_by_employee_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Attachment]:
    ensure_company_access(current_user, company_id)
    statement = select(Attachment).where(Attachment.company_id == company_id)
    if not include_inactive:
        statement = statement.where(Attachment.is_active.is_(True))
    if not include_deleted:
        statement = statement.where(Attachment.is_deleted.is_(False))
    visibility_conditions = attachment_visibility_conditions(db, current_user, company_id)
    if visibility_conditions:
        statement = statement.where(or_(*visibility_conditions))
    if work_object_id:
        work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
        ensure_company(work_object, company_id, label="Work object")
        ensure_work_object_visible(db, current_user, work_object)
        statement = statement.where(Attachment.work_object_id == work_object_id)
    if project_id:
        statement = statement.where(Attachment.project_id == project_id)
    if linked_entity_type:
        statement = statement.where(Attachment.linked_entity_type == linked_entity_type)
    if linked_entity_id:
        statement = statement.where(Attachment.linked_entity_id == linked_entity_id)
    if q:
        term = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                Attachment.file_name.ilike(term),
                Attachment.original_file_name.ilike(term),
                Attachment.description.ilike(term),
                Attachment.content_type.ilike(term),
                Attachment.extension.ilike(term),
            )
        )
    if content_type:
        statement = statement.where(Attachment.content_type == content_type)
    if uploaded_by_employee_id:
        statement = statement.where(Attachment.uploaded_by_employee_id == uploaded_by_employee_id)
    if date_from:
        statement = statement.where(Attachment.created_at >= date_from)
    if date_to:
        statement = statement.where(Attachment.created_at <= date_to)
    statement = statement.order_by(Attachment.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@router.get("/{attachment_id}", response_model=AttachmentRead)
def get_attachment(
    attachment_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Attachment:
    return get_attachment_for_user(db, current_user, attachment_id=attachment_id, company_id=company_id)


@router.get("/{attachment_id}/download")
def download_attachment(
    attachment_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> StreamingResponse:
    attachment = get_attachment_for_user(db, current_user, attachment_id=attachment_id, company_id=company_id)
    content = FileService.read_attachment_bytes(attachment)
    filename = quote(attachment.original_file_name or attachment.file_name, safe="")
    return StreamingResponse(
        iter((content,)),
        media_type=attachment.content_type or "application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.get("/{attachment_id}/preview")
def preview_attachment(
    attachment_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> StreamingResponse:
    attachment = get_attachment_for_user(db, current_user, attachment_id=attachment_id, company_id=company_id)
    previewable_types = {
        "application/json",
        "application/pdf",
        "text/csv",
        "text/markdown",
        "text/plain",
        "image/jpeg",
        "image/png",
        "image/webp",
    }
    if (attachment.content_type or "").lower() not in previewable_types:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Preview is not available for this file type")
    content = FileService.read_attachment_bytes(attachment)
    filename = quote(attachment.original_file_name or attachment.file_name, safe="")
    return StreamingResponse(
        iter((content,)),
        media_type=attachment.content_type or "application/octet-stream",
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{filename}"},
    )


@router.patch("/{attachment_id}", response_model=AttachmentRead)
def update_attachment(
    attachment_id: UUID,
    company_id: UUID,
    payload: AttachmentUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Attachment:
    attachment = get_attachment_for_user(db, current_user, attachment_id=attachment_id, company_id=company_id)
    data = payload.model_dump(exclude_unset=True)
    changed: list[str] = []
    if "description" in data:
        attachment.description = data["description"]
        changed.append("description")
    if "tags" in data:
        attachment.tags = data["tags"] or []
        changed.append("tags")
    if "processing_status" in data and data["processing_status"]:
        attachment.processing_status = data["processing_status"]
        changed.append("processing_status")
    if "scan_status" in data and data["scan_status"]:
        attachment.scan_status = data["scan_status"]
        changed.append("scan_status")
    if "metadata" in data:
        attachment.metadata_json = data["metadata"] or {}
        changed.append("metadata")
    if changed:
        record_file_event(
            db,
            attachment=attachment,
            current_user=current_user,
            event_type="file.updated",
            title=f"{attachment.original_file_name} updated",
            description="File metadata was updated.",
            metadata={"changed_fields": sorted(changed)},
        )
    db.commit()
    db.refresh(attachment)
    return attachment


@router.put("/{attachment_id}", response_model=AttachmentRead)
def replace_attachment_metadata(
    attachment_id: UUID,
    company_id: UUID,
    payload: AttachmentUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Attachment:
    return update_attachment(attachment_id, company_id, payload, db, current_user)


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: UUID,
    company_id: UUID,
    remove_file: bool = True,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Response:
    attachment = get_attachment_for_user(db, current_user, attachment_id=attachment_id, company_id=company_id)
    ensure_role(current_user, MANAGER_ROLES)
    attachment.is_active = False
    attachment.is_deleted = True
    attachment.deleted_at = datetime.now(timezone.utc)
    record_file_event(
        db,
        attachment=attachment,
        current_user=current_user,
        event_type="file.deleted",
        title=f"{attachment.original_file_name} deleted",
        description="File attachment was removed.",
    )
    if remove_file:
        FileService.delete_stored_file(attachment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@uploads_router.post("", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
def upload_file_metadata(
    payload: AttachmentCreate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Attachment:
    return create_attachment_metadata(payload, db, current_user)


@files_router.get("", response_model=list[AttachmentRead])
def list_files(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    linked_entity_type: str | None = None,
    linked_entity_id: UUID | None = None,
    q: str | None = Query(default=None, max_length=200),
    content_type: str | None = None,
    uploaded_by: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    include_archived: bool = False,
    include_deleted: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Attachment]:
    return list_attachments(
        company_id,
        db,
        current_user,
        None,
        None,
        linked_entity_type or entity_type,
        linked_entity_id or entity_id,
        include_archived,
        include_deleted,
        q,
        content_type,
        uploaded_by,
        date_from,
        date_to,
        limit,
        offset,
    )


@files_router.get("/{attachment_id}", response_model=AttachmentRead)
def get_file(
    attachment_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Attachment:
    return get_attachment(attachment_id, company_id, db, current_user)


@files_router.post("/{attachment_id}/ai-summary", response_model=AIJobRead)
def generate_file_ai_summary(
    attachment_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJobRead:
    attachment = get_attachment_for_user(db, current_user, attachment_id=attachment_id, company_id=company_id)
    job = ai_service.generate_summary(
        db,
        company_id=company_id,
        job_type="file_summary_safe",
        input_entity_type="attachment",
        input_entity_id=attachment.id,
        current_user=current_user,
    )
    db.commit()
    db.refresh(job)
    return job


@files_router.get("/{attachment_id}/ai-summary/latest", response_model=AIJobRead | None)
def get_latest_file_ai_summary(
    attachment_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJobRead | None:
    attachment = get_attachment_for_user(db, current_user, attachment_id=attachment_id, company_id=company_id)
    return ai_service.latest_summary_job(
        db,
        company_id=company_id,
        job_type="file_summary_safe",
        input_entity_type="attachment",
        input_entity_id=attachment.id,
        current_user=current_user,
    )


@files_router.post("/{attachment_id}/ai-analysis", response_model=AIJobRead)
def generate_file_ai_analysis(
    attachment_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJobRead:
    attachment = get_attachment_for_user(db, current_user, attachment_id=attachment_id, company_id=company_id)
    job = ai_service.generate_summary(
        db,
        company_id=company_id,
        job_type="document_analysis_safe",
        input_entity_type="attachment",
        input_entity_id=attachment.id,
        current_user=current_user,
    )
    db.commit()
    db.refresh(job)
    return job


@files_router.get("/{attachment_id}/ai-analysis/latest", response_model=AIJobRead | None)
def get_latest_file_ai_analysis(
    attachment_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJobRead | None:
    attachment = get_attachment_for_user(db, current_user, attachment_id=attachment_id, company_id=company_id)
    return ai_service.latest_summary_job(
        db,
        company_id=company_id,
        job_type="document_analysis_safe",
        input_entity_type="attachment",
        input_entity_id=attachment.id,
        current_user=current_user,
    )


@files_router.post("/{attachment_id}/ai-image-analysis", response_model=AIJobRead)
def generate_file_ai_image_analysis(
    attachment_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJobRead:
    attachment = get_attachment_for_user(db, current_user, attachment_id=attachment_id, company_id=company_id)
    job = ai_service.generate_summary(
        db,
        company_id=company_id,
        job_type="image_analysis_safe",
        input_entity_type="attachment",
        input_entity_id=attachment.id,
        current_user=current_user,
    )
    db.commit()
    db.refresh(job)
    return job


@files_router.get("/{attachment_id}/ai-image-analysis/latest", response_model=AIJobRead | None)
def get_latest_file_ai_image_analysis(
    attachment_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJobRead | None:
    attachment = get_attachment_for_user(db, current_user, attachment_id=attachment_id, company_id=company_id)
    return ai_service.latest_summary_job(
        db,
        company_id=company_id,
        job_type="image_analysis_safe",
        input_entity_type="attachment",
        input_entity_id=attachment.id,
        current_user=current_user,
    )


@files_router.post("/{attachment_id}/ai-transcription", response_model=AIJobRead)
def generate_file_ai_transcription(
    attachment_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJobRead:
    attachment = get_attachment_for_user(db, current_user, attachment_id=attachment_id, company_id=company_id)
    job = ai_service.generate_summary(
        db,
        company_id=company_id,
        job_type="audio_transcription_safe",
        input_entity_type="attachment",
        input_entity_id=attachment.id,
        current_user=current_user,
    )
    db.commit()
    db.refresh(job)
    return job


@files_router.get("/{attachment_id}/ai-transcription/latest", response_model=AIJobRead | None)
def get_latest_file_ai_transcription(
    attachment_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJobRead | None:
    attachment = get_attachment_for_user(db, current_user, attachment_id=attachment_id, company_id=company_id)
    return ai_service.latest_summary_job(
        db,
        company_id=company_id,
        job_type="audio_transcription_safe",
        input_entity_type="attachment",
        input_entity_id=attachment.id,
        current_user=current_user,
    )


@files_router.patch("/{attachment_id}", response_model=AttachmentRead)
def update_file(
    attachment_id: UUID,
    company_id: UUID,
    payload: AttachmentUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Attachment:
    return update_attachment(attachment_id, company_id, payload, db, current_user)


@files_router.post("/{attachment_id}/archive", response_model=AttachmentRead)
def archive_file(
    attachment_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Attachment:
    attachment = get_attachment_for_user(db, current_user, attachment_id=attachment_id, company_id=company_id)
    ensure_role(current_user, MANAGER_ROLES)
    attachment.is_active = False
    attachment.is_deleted = False
    attachment.archived_at = datetime.now(timezone.utc)
    record_file_event(
        db,
        attachment=attachment,
        current_user=current_user,
        event_type="file.archived",
        title=f"{attachment.original_file_name} archived",
        description="File was archived.",
    )
    db.commit()
    db.refresh(attachment)
    return attachment


@files_router.post("/{attachment_id}/restore", response_model=AttachmentRead)
def restore_file(
    attachment_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Attachment:
    attachment = get_attachment_for_user(db, current_user, attachment_id=attachment_id, company_id=company_id, include_inactive=True)
    ensure_role(current_user, MANAGER_ROLES)
    attachment.is_active = True
    attachment.is_deleted = False
    attachment.archived_at = None
    attachment.deleted_at = None
    record_file_event(
        db,
        attachment=attachment,
        current_user=current_user,
        event_type="file.restored",
        title=f"{attachment.original_file_name} restored",
        description="File was restored.",
    )
    db.commit()
    db.refresh(attachment)
    return attachment
