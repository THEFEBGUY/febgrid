from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_company, get_current_user
from app.api.utils import ensure_company, get_or_404, update_model
from app.core.permissions import OWNER_ADMIN_ROLES, ensure_company_access, ensure_role
from app.models.company import Company
from app.models.department import Department
from app.models.user import User
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.services.event_service import EventService

router = APIRouter(prefix="/departments", tags=["departments"])


def ensure_current_company(current_company: Company, company_id: UUID) -> None:
    if current_company.id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")


@router.post("", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Department:
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    ensure_company_access(current_user, payload.company_id)
    department = Department(id=uuid4(), **payload.model_dump())
    db.add(department)
    EventService.record_event(
        db,
        company_id=department.company_id,
        event_type="department.created",
        title=f"{department.name} department created",
        target_entity_type="department",
        target_entity_id=department.id,
    )
    db.commit()
    return department


@router.get("", response_model=list[DepartmentRead])
def list_departments(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_company: Company = Depends(get_current_company),
    include_inactive: bool = False,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Department]:
    ensure_current_company(current_company, company_id)
    statement = select(Department).where(Department.company_id == company_id)
    if not include_inactive:
        statement = statement.where(Department.is_active.is_(True))
    statement = statement.order_by(Department.name.asc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@router.get("/{department_id}", response_model=DepartmentRead)
def get_department(
    department_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_company: Company = Depends(get_current_company),
) -> Department:
    ensure_current_company(current_company, company_id)
    department = get_or_404(db, Department, department_id, label="Department")
    ensure_company(department, company_id, label="Department")
    return department


@router.put("/{department_id}", response_model=DepartmentRead)
def update_department(
    department_id: UUID,
    company_id: UUID,
    payload: DepartmentUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Department:
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    ensure_company_access(current_user, company_id)
    department = get_or_404(db, Department, department_id, label="Department")
    ensure_company(department, company_id, label="Department")
    changed = update_model(department, payload)
    if changed:
        EventService.record_event(
            db,
            company_id=company_id,
            event_type="department.updated",
            title=f"{department.name} department updated",
            target_entity_type="department",
            target_entity_id=department.id,
            metadata={"changed_fields": sorted(changed.keys())},
        )
    db.commit()
    return department


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_department(
    department_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    ensure_company_access(current_user, company_id)
    department = get_or_404(db, Department, department_id, label="Department")
    ensure_company(department, company_id, label="Department")
    department.is_active = False
    EventService.record_event(
        db,
        company_id=company_id,
        event_type="department.deactivated",
        title=f"{department.name} department deactivated",
        target_entity_type="department",
        target_entity_id=department.id,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
