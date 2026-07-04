from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.schemas.company_memory import (
    CompanyMemoryActionPayload,
    CompanyMemoryCreate,
    CompanyMemoryFromAIJobPayload,
    CompanyMemoryRead,
    CompanyMemoryUpdate,
)
from app.services.company_memory_service import CompanyMemoryService

router = APIRouter(prefix="/company-memory", tags=["company-memory"])


@router.get("", response_model=list[CompanyMemoryRead])
def list_company_memory(
    company_id: UUID,
    status: str | None = None,
    memory_type: str | None = None,
    scope_type: str | None = None,
    source_type: str | None = None,
    importance: str | None = None,
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> list[CompanyMemoryRead]:
    return CompanyMemoryService.list_memories(
        db,
        company_id=company_id,
        current_user=current_user,
        status_filter=status,
        memory_type=memory_type,
        scope_type=scope_type,
        source_type=source_type,
        importance=importance,
        query=q,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=CompanyMemoryRead)
def create_company_memory(
    payload: CompanyMemoryCreate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> CompanyMemoryRead:
    return CompanyMemoryService.create_memory(db, payload=payload, current_user=current_user)


@router.post("/from-ai-job/{ai_job_id}", response_model=CompanyMemoryRead)
def create_company_memory_from_ai_job(
    ai_job_id: UUID,
    payload: CompanyMemoryFromAIJobPayload,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> CompanyMemoryRead:
    return CompanyMemoryService.create_from_ai_job(db, ai_job_id=ai_job_id, payload=payload, current_user=current_user)


@router.get("/sources/{source_type}/{source_id}", response_model=list[CompanyMemoryRead])
def list_company_memory_for_source(
    source_type: str,
    source_id: UUID,
    company_id: UUID,
    status: str | None = None,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> list[CompanyMemoryRead]:
    CompanyMemoryService.validate_source(db, company_id=company_id, source_type=source_type, source_id=source_id, source_ai_job_id=None)
    return CompanyMemoryService.list_memories(
        db,
        company_id=company_id,
        current_user=current_user,
        status_filter=status,
        source_type=source_type,
        source_id=source_id,
        limit=100,
    )


@router.get("/{memory_id}", response_model=CompanyMemoryRead)
def get_company_memory(
    memory_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> CompanyMemoryRead:
    return CompanyMemoryService.get_memory(db, memory_id=memory_id, company_id=company_id, current_user=current_user)


@router.patch("/{memory_id}", response_model=CompanyMemoryRead)
def update_company_memory(
    memory_id: UUID,
    company_id: UUID,
    payload: CompanyMemoryUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> CompanyMemoryRead:
    return CompanyMemoryService.update_memory(
        db,
        memory_id=memory_id,
        company_id=company_id,
        payload=payload,
        current_user=current_user,
    )


@router.post("/{memory_id}/approve", response_model=CompanyMemoryRead)
def approve_company_memory(
    memory_id: UUID,
    payload: CompanyMemoryActionPayload,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> CompanyMemoryRead:
    return CompanyMemoryService.approve_memory(db, memory_id=memory_id, company_id=payload.company_id, current_user=current_user)


@router.post("/{memory_id}/reject", response_model=CompanyMemoryRead)
def reject_company_memory(
    memory_id: UUID,
    payload: CompanyMemoryActionPayload,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> CompanyMemoryRead:
    return CompanyMemoryService.reject_memory(
        db,
        memory_id=memory_id,
        company_id=payload.company_id,
        current_user=current_user,
        note=payload.note,
    )


@router.post("/{memory_id}/archive", response_model=CompanyMemoryRead)
def archive_company_memory(
    memory_id: UUID,
    payload: CompanyMemoryActionPayload,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> CompanyMemoryRead:
    return CompanyMemoryService.archive_memory(db, memory_id=memory_id, company_id=payload.company_id, current_user=current_user)
