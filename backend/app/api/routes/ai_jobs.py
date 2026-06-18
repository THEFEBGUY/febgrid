from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.api.utils import ensure_company, get_or_404
from app.models.ai_job import AIJob
from app.models.attachment import Attachment
from app.models.company import Company
from app.models.employee import Employee
from app.models.work_object import WorkObject
from app.schemas.ai_job import AIJobCreate, AIJobRead
from app.services.ai_service import ai_service
from app.services.event_service import EventService

router = APIRouter(prefix="/ai-jobs", tags=["ai-jobs"])


def enrich_ai_payload(db: Session, payload: AIJobCreate) -> dict:
    enriched = dict(payload.input_payload)
    if payload.related_entity_type == "work_object" and payload.related_entity_id:
        work_object = get_or_404(db, WorkObject, payload.related_entity_id, label="Work object")
        ensure_company(work_object, payload.company_id, label="Work object")
        enriched.setdefault("title", work_object.title)
        enriched.setdefault("description", work_object.description)
    if payload.related_entity_type == "attachment" and payload.related_entity_id:
        attachment = get_or_404(db, Attachment, payload.related_entity_id, label="Attachment")
        ensure_company(attachment, payload.company_id, label="Attachment")
        enriched.setdefault("file_name", attachment.file_name)
        enriched.setdefault("file_type", attachment.file_type)
    return enriched


@router.post("", response_model=AIJobRead)
def create_ai_job(payload: AIJobCreate, db: Session = Depends(db_session)) -> AIJob:
    get_or_404(db, Company, payload.company_id, label="Company")
    if payload.requested_by_employee_id:
        requester = get_or_404(db, Employee, payload.requested_by_employee_id, label="Requester")
        ensure_company(requester, payload.company_id, label="Requester")

    input_payload = enrich_ai_payload(db, payload)
    job = AIJob(
        company_id=payload.company_id,
        requested_by_employee_id=payload.requested_by_employee_id,
        job_type=payload.job_type,
        status="completed",
        input_payload=input_payload,
        output_payload=ai_service.run_job(payload.job_type, input_payload),
        related_entity_type=payload.related_entity_type,
        related_entity_id=payload.related_entity_id,
    )
    db.add(job)
    db.flush()
    EventService.record_event(
        db,
        company_id=job.company_id,
        actor_employee_id=job.requested_by_employee_id,
        event_type="ai_job.completed",
        title=f"Mock AI job completed: {job.job_type}",
        target_entity_type="ai_job",
        target_entity_id=job.id,
        metadata={"provider": ai_service.provider, "related_entity_type": job.related_entity_type},
    )
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[AIJobRead])
def list_ai_jobs(
    company_id: UUID,
    db: Session = Depends(db_session),
    status_filter: str | None = Query(default=None, alias="status"),
    job_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[AIJob]:
    statement = select(AIJob).where(AIJob.company_id == company_id)
    if status_filter:
        statement = statement.where(AIJob.status == status_filter)
    if job_type:
        statement = statement.where(AIJob.job_type == job_type)
    statement = statement.order_by(AIJob.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@router.get("/{ai_job_id}", response_model=AIJobRead)
def get_ai_job(ai_job_id: UUID, company_id: UUID, db: Session = Depends(db_session)) -> AIJob:
    job = get_or_404(db, AIJob, ai_job_id, label="AI job")
    ensure_company(job, company_id, label="AI job")
    return job
