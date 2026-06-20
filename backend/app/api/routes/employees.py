from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_optional_current_user
from app.api.serializers import serialize_events
from app.api.utils import ensure_company, get_or_404, update_model
from app.core.permissions import OWNER_ADMIN_ROLES, ensure_company_access, ensure_role
from app.models.company import Company
from app.models.employee import Employee
from app.models.event import Event
from app.models.team import TeamMember
from app.models.user import User
from app.schemas.employee import EmployeeCreate, EmployeeRead, EmployeeStatusUpdate, EmployeeUpdate
from app.schemas.event import EventRead
from app.services.event_service import EventService

router = APIRouter(prefix="/employees", tags=["employees"])


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Employee:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    get_or_404(db, Company, payload.company_id, label="Company")
    if payload.manager_id:
        manager = get_or_404(db, Employee, payload.manager_id, label="Manager")
        ensure_company(manager, payload.company_id, label="Manager")

    employee = Employee(
        company_id=payload.company_id,
        manager_id=payload.manager_id,
        full_name=payload.full_name,
        email=str(payload.email),
        phone=payload.phone,
        role=payload.role,
        department=payload.department,
        employment_type=payload.employment_type,
        status=payload.status,
        location=payload.location,
        profile_image_url=payload.profile_image_url,
        skills=payload.skills,
        metadata_json=payload.metadata,
    )
    db.add(employee)
    db.flush()
    EventService.record_event(
        db,
        company_id=employee.company_id,
        event_type="employee.created",
        title=f"{employee.full_name} added",
        target_entity_type="employee",
        target_entity_id=employee.id,
        metadata={"role": employee.role, "department": employee.department},
    )
    db.commit()
    db.refresh(employee)
    return employee


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    status_filter: str | None = Query(default=None, alias="status"),
    team_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Employee]:
    ensure_company_access(current_user, company_id)
    statement = select(Employee).where(Employee.company_id == company_id)
    if status_filter:
        statement = statement.where(Employee.status == status_filter)
    if team_id:
        statement = statement.join(TeamMember, TeamMember.employee_id == Employee.id).where(
            TeamMember.company_id == company_id,
            TeamMember.team_id == team_id,
        )
    statement = statement.order_by(Employee.full_name.asc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Employee:
    ensure_company_access(current_user, company_id)
    employee = get_or_404(db, Employee, employee_id, label="Employee")
    ensure_company(employee, company_id, label="Employee")
    return employee


@router.put("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: UUID,
    company_id: UUID,
    payload: EmployeeUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Employee:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    employee = get_or_404(db, Employee, employee_id, label="Employee")
    ensure_company(employee, company_id, label="Employee")
    if "manager_id" in payload.model_fields_set and payload.manager_id:
        manager = get_or_404(db, Employee, payload.manager_id, label="Manager")
        ensure_company(manager, company_id, label="Manager")
    changed = update_model(employee, payload, alias_fields={"metadata": "metadata_json"})
    if changed:
        EventService.record_event(
            db,
            company_id=company_id,
            event_type="employee.updated",
            title=f"{employee.full_name} updated",
            target_entity_type="employee",
            target_entity_id=employee.id,
            metadata={"changed_fields": sorted(changed.keys())},
        )
    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: UUID,
    company_id: UUID,
    actor_employee_id: UUID | None = None,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Response:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    employee = get_or_404(db, Employee, employee_id, label="Employee")
    ensure_company(employee, company_id, label="Employee")
    EventService.record_event(
        db,
        company_id=company_id,
        actor_employee_id=actor_employee_id,
        event_type="employee.deleted",
        title=f"{employee.full_name} removed",
        target_entity_type="employee",
        target_entity_id=employee.id,
    )
    db.delete(employee)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{employee_id}/status", response_model=EmployeeRead)
def update_employee_status(
    employee_id: UUID,
    payload: EmployeeStatusUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Employee:
    ensure_company_access(current_user, payload.company_id)
    employee = get_or_404(db, Employee, employee_id, label="Employee")
    ensure_company(employee, payload.company_id, label="Employee")
    old_status = employee.status
    employee.status = payload.status
    EventService.record_event(
        db,
        company_id=payload.company_id,
        actor_employee_id=payload.actor_employee_id,
        event_type="employee.status_changed",
        title=f"{employee.full_name} status changed",
        target_entity_type="employee",
        target_entity_id=employee.id,
        metadata={"from": old_status, "to": payload.status},
    )
    db.commit()
    db.refresh(employee)
    return employee


@router.get("/{employee_id}/activity", response_model=list[EventRead])
def get_employee_activity(
    employee_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[EventRead]:
    ensure_company_access(current_user, company_id)
    employee = get_or_404(db, Employee, employee_id, label="Employee")
    ensure_company(employee, company_id, label="Employee")
    statement = (
        select(Event)
        .where(
            Event.company_id == company_id,
            or_(
                Event.actor_employee_id == employee_id,
                (Event.target_entity_type == "employee") & (Event.target_entity_id == employee_id),
            ),
        )
        .order_by(Event.created_at.desc())
        .limit(limit)
    )
    return serialize_events(db.scalars(statement).all())
