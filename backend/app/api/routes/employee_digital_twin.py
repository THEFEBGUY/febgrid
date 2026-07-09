from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.employee_digital_twin import EmployeeDigitalTwinSnapshot
from app.models.user import User
from app.schemas.employee_digital_twin import EmployeeDigitalTwinSignalsRead, EmployeeDigitalTwinSnapshotRead
from app.services.employee_digital_twin_service import EmployeeDigitalTwinService

router = APIRouter(prefix="/employees/{employee_id}/digital-twin", tags=["employee-digital-twin"])


@router.get("/latest", response_model=EmployeeDigitalTwinSnapshotRead | None)
def latest_employee_digital_twin(
    employee_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> EmployeeDigitalTwinSnapshot | None:
    return EmployeeDigitalTwinService.latest_snapshot(
        db,
        company_id=company_id,
        employee_id=employee_id,
        current_user=current_user,
    )


@router.post("/generate", response_model=EmployeeDigitalTwinSnapshotRead)
def generate_employee_digital_twin(
    employee_id: UUID,
    company_id: UUID,
    period_days: int = Query(default=30),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> EmployeeDigitalTwinSnapshot:
    snapshot = EmployeeDigitalTwinService.generate_snapshot(
        db,
        company_id=company_id,
        employee_id=employee_id,
        current_user=current_user,
        period_days=period_days,
    )
    db.commit()
    db.refresh(snapshot)
    return snapshot


@router.get("/history", response_model=list[EmployeeDigitalTwinSnapshotRead])
def employee_digital_twin_history(
    employee_id: UUID,
    company_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> list[EmployeeDigitalTwinSnapshot]:
    return EmployeeDigitalTwinService.history(
        db,
        company_id=company_id,
        employee_id=employee_id,
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


@router.get("/signals", response_model=EmployeeDigitalTwinSignalsRead)
def employee_digital_twin_signals(
    employee_id: UUID,
    company_id: UUID,
    period_days: int = Query(default=30),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> EmployeeDigitalTwinSignalsRead:
    payload = EmployeeDigitalTwinService.signals(
        db,
        company_id=company_id,
        employee_id=employee_id,
        current_user=current_user,
        period_days=period_days,
    )
    return EmployeeDigitalTwinSignalsRead(**payload)
