from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.company_pulse import CompanyPulseSnapshot
from app.models.user import User
from app.schemas.company_pulse import CompanyPulseSignalsRead, CompanyPulseSnapshotRead
from app.services.company_pulse_service import CompanyPulseService

router = APIRouter(prefix="/company-pulse", tags=["company-pulse"])


@router.get("/latest", response_model=CompanyPulseSnapshotRead | None)
def latest_company_pulse(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> CompanyPulseSnapshot | None:
    return CompanyPulseService.latest_snapshot(db, company_id=company_id, current_user=current_user)


@router.post("/generate", response_model=CompanyPulseSnapshotRead)
def generate_company_pulse(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> CompanyPulseSnapshot:
    snapshot = CompanyPulseService.generate_snapshot(db, company_id=company_id, current_user=current_user)
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.get("/history", response_model=list[CompanyPulseSnapshotRead])
def company_pulse_history(
    company_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> list[CompanyPulseSnapshot]:
    return CompanyPulseService.history(
        db,
        company_id=company_id,
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


@router.get("/signals", response_model=CompanyPulseSignalsRead)
def company_pulse_signals(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> CompanyPulseSignalsRead:
    payload = CompanyPulseService.calculate_signals(db, company_id=company_id, current_user=current_user)
    return CompanyPulseSignalsRead(**payload)
