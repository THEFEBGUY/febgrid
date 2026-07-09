from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.models.work_dna import WorkDNASnapshot
from app.schemas.work_dna import WorkDNASignalsRead, WorkDNASnapshotRead
from app.services.work_dna_service import WorkDNAService

router = APIRouter(prefix="/work-dna", tags=["work-dna"])


@router.get("/latest", response_model=WorkDNASnapshotRead | None)
def latest_work_dna(
    company_id: UUID,
    scope_type: str = Query(default="company"),
    scope_id: UUID | None = None,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> WorkDNASnapshot | None:
    return WorkDNAService.latest_snapshot(
        db,
        company_id=company_id,
        scope_type=scope_type,
        scope_id=scope_id,
        current_user=current_user,
    )


@router.post("/generate", response_model=WorkDNASnapshotRead)
def generate_work_dna(
    company_id: UUID,
    scope_type: str = Query(default="company"),
    scope_id: UUID | None = None,
    period_days: int = Query(default=30),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> WorkDNASnapshot:
    snapshot = WorkDNAService.generate_snapshot(
        db,
        company_id=company_id,
        scope_type=scope_type,
        scope_id=scope_id,
        current_user=current_user,
        period_days=period_days,
    )
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.get("/history", response_model=list[WorkDNASnapshotRead])
def work_dna_history(
    company_id: UUID,
    scope_type: str = Query(default="company"),
    scope_id: UUID | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> list[WorkDNASnapshot]:
    return WorkDNAService.history(
        db,
        company_id=company_id,
        scope_type=scope_type,
        scope_id=scope_id,
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


@router.get("/signals", response_model=WorkDNASignalsRead)
def work_dna_signals(
    company_id: UUID,
    scope_type: str = Query(default="company"),
    scope_id: UUID | None = None,
    period_days: int = Query(default=30),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> WorkDNASignalsRead:
    payload = WorkDNAService.signals(
        db,
        company_id=company_id,
        scope_type=scope_type,
        scope_id=scope_id,
        current_user=current_user,
        period_days=period_days,
    )
    return WorkDNASignalsRead(**payload)
