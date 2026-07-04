from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.core.permissions import OWNER_ADMIN_ROLES, ensure_company_access, ensure_role
from app.models.ai_job import AIJob
from app.models.user import User
from app.schemas.ai_job import (
    AICapabilitiesRead,
    AIJobCreate,
    AIJobProcessResult,
    AIJobQueueSummaryRead,
    AIJobRead,
    AIJobRecoveryResult,
    AIProviderStatusRead,
    AISafetySettingsRead,
    AISafetySettingsUpdate,
)
from app.services.ai_job_runner import AIJobRunner
from app.services.ai_service import ai_service

router = APIRouter(prefix="/ai", tags=["ai"])
legacy_router = APIRouter(prefix="/ai-jobs", tags=["ai-jobs"])


def list_jobs_for_company(
    *,
    company_id: UUID,
    db: Session,
    current_user: User,
    status_filter: str | None,
    job_type: str | None,
    limit: int,
    offset: int,
) -> list[AIJob]:
    statement = ai_service.visible_statement(company_id, current_user)
    if status_filter:
        statement = statement.where(AIJob.status == ai_service.ensure_status(status_filter))
    if job_type:
        statement = statement.where(AIJob.job_type == ai_service.ensure_job_type(job_type))
    statement = statement.order_by(AIJob.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@router.get("/capabilities", response_model=AICapabilitiesRead)
def get_ai_capabilities(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AICapabilitiesRead:
    ensure_company_access(current_user, company_id)
    return ai_service.capabilities(db, company_id=company_id, current_user=current_user)


@router.get("/provider-status", response_model=AIProviderStatusRead)
def get_ai_provider_status(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIProviderStatusRead:
    return ai_service.provider_status(db, company_id=company_id, current_user=current_user)


@router.get("/safety-settings", response_model=AISafetySettingsRead)
def get_ai_safety_settings(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AISafetySettingsRead:
    return ai_service.safety_settings(db, company_id=company_id, current_user=current_user)


@router.put("/safety-settings", response_model=AISafetySettingsRead)
def update_ai_safety_settings(
    company_id: UUID,
    payload: AISafetySettingsUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AISafetySettingsRead:
    settings = ai_service.update_safety_settings(db, company_id=company_id, payload=payload, current_user=current_user)
    db.commit()
    return settings


@router.get("/jobs", response_model=list[AIJobRead])
def list_ai_jobs(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
    status_filter: str | None = Query(default=None, alias="status"),
    job_type: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[AIJob]:
    return list_jobs_for_company(
        company_id=company_id,
        db=db,
        current_user=current_user,
        status_filter=status_filter,
        job_type=job_type,
        limit=limit,
        offset=offset,
    )


@router.get("/jobs/queue-summary", response_model=AIJobQueueSummaryRead)
def get_ai_job_queue_summary(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJobQueueSummaryRead:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    return AIJobRunner().queue_summary(db, company_id=company_id)


@router.post("/jobs", response_model=AIJobRead, status_code=status.HTTP_201_CREATED)
def create_ai_job(
    payload: AIJobCreate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJob:
    job = ai_service.create_job(db, payload=payload, current_user=current_user)
    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs/process-next", response_model=AIJobProcessResult)
def process_next_ai_job(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJobProcessResult:
    job = AIJobRunner().process_next(db, company_id=company_id, current_user=current_user)
    db.commit()
    if job is None:
        return AIJobProcessResult(processed=False, message="No queued AI job is ready to process.", job=None)
    db.refresh(job)
    return AIJobProcessResult(processed=True, message="Processed one queued AI job.", job=job)


@router.post("/jobs/recover-stale", response_model=AIJobRecoveryResult)
def recover_stale_ai_jobs(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJobRecoveryResult:
    recovered = AIJobRunner().recover_stale_jobs(db, company_id=company_id, current_user=current_user)
    db.commit()
    return AIJobRecoveryResult(recovered=recovered, message=f"Recovered {recovered} stale AI job(s).")


@router.get("/jobs/{ai_job_id}", response_model=AIJobRead)
def get_ai_job(
    ai_job_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJob:
    return ai_service.get_visible_job(db, job_id=ai_job_id, company_id=company_id, current_user=current_user)


@router.post("/jobs/{ai_job_id}/retry", response_model=AIJobRead)
def retry_ai_job(
    ai_job_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJob:
    job = ai_service.get_visible_job(db, job_id=ai_job_id, company_id=company_id, current_user=current_user)
    job = AIJobRunner().retry_failed_job(db, job=job, current_user=current_user)
    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs/{ai_job_id}/run", response_model=AIJobRead)
def run_ai_job(
    ai_job_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJob:
    job = ai_service.get_visible_job(db, job_id=ai_job_id, company_id=company_id, current_user=current_user)
    job = ai_service.run_job(db, job=job, current_user=current_user)
    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs/{ai_job_id}/cancel", response_model=AIJobRead)
def cancel_ai_job(
    ai_job_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJob:
    job = ai_service.get_visible_job(db, job_id=ai_job_id, company_id=company_id, current_user=current_user)
    job = ai_service.cancel_job(db, job=job, current_user=current_user)
    db.commit()
    db.refresh(job)
    return job


@legacy_router.get("", response_model=list[AIJobRead])
def list_legacy_ai_jobs(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
    status_filter: str | None = Query(default=None, alias="status"),
    job_type: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[AIJob]:
    return list_jobs_for_company(
        company_id=company_id,
        db=db,
        current_user=current_user,
        status_filter=status_filter,
        job_type=job_type,
        limit=limit,
        offset=offset,
    )


@legacy_router.post("", response_model=AIJobRead, status_code=status.HTTP_201_CREATED)
def create_legacy_ai_job(
    payload: AIJobCreate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJob:
    return create_ai_job(payload=payload, db=db, current_user=current_user)


@legacy_router.get("/{ai_job_id}", response_model=AIJobRead)
def get_legacy_ai_job(
    ai_job_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJob:
    return get_ai_job(ai_job_id=ai_job_id, company_id=company_id, db=db, current_user=current_user)
