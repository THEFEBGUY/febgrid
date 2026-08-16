from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.api.serializers import serialize_events
from app.api.utils import ensure_company, get_or_404, update_model
from app.core.permissions import OWNER_ADMIN_ROLES, ensure_company_access, ensure_role
from app.models.company import Company
from app.models.department import Department
from app.models.employee import Employee
from app.models.event import Event
from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.employee import EmployeeActivationUpdate, EmployeeCreate, EmployeeRead, EmployeeSelfUpdate, EmployeeStatusUpdate, EmployeeUpdate
from app.schemas.event import EventRead
from app.services.event_service import EventService
from app.services.invitation_service import InvitationService

router = APIRouter(prefix="/employees", tags=["employees"])

EMPLOYEE_STATUSES = {"working", "online", "on_break", "offline", "on_leave", "done_for_the_day", "busy", "available"}


def ensure_employee_status(status_value: str) -> None:
    if status_value not in EMPLOYEE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid employee status",
        )


def validate_employee_refs(
    db: Session,
    *,
    company_id: UUID,
    user_id: UUID | None = None,
    department_id: UUID | None = None,
    team_id: UUID | None = None,
    manager_id: UUID | None = None,
) -> None:
    if user_id:
        user = get_or_404(db, User, user_id, label="User")
        ensure_company_access(user, company_id)
    if department_id:
        department = get_or_404(db, Department, department_id, label="Department")
        ensure_company(department, company_id, label="Department")
    if team_id:
        team = get_or_404(db, Team, team_id, label="Team")
        ensure_company(team, company_id, label="Team")
    if manager_id:
        manager = get_or_404(db, Employee, manager_id, label="Manager")
        ensure_company(manager, company_id, label="Manager")


def can_view_employee(current_user: User | None, employee: Employee) -> bool:
    if current_user is None:
        return True
    if current_user.role in {"company_owner", "admin", "manager"}:
        return True
    return employee.user_id == current_user.id


def get_current_employee_profile(db: Session, current_user: User) -> Employee:
    employee = db.scalar(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.user_id == current_user.id,
        )
    )
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee profile not found")
    return employee


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee(
    payload: EmployeeCreate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Employee:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    get_or_404(db, Company, payload.company_id, label="Company")
    ensure_employee_status(payload.current_status)
    validate_employee_refs(
        db,
        company_id=payload.company_id,
        user_id=payload.user_id,
        department_id=payload.department_id,
        team_id=payload.team_id,
        manager_id=payload.manager_id,
    )

    employee = Employee(
        company_id=payload.company_id,
        user_id=payload.user_id,
        department_id=payload.department_id,
        team_id=payload.team_id,
        manager_id=payload.manager_id,
        full_name=payload.full_name,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
        role=payload.role_title,
        department=payload.department,
        employment_type=payload.employment_type,
        status=payload.current_status,
        location=payload.location,
        profile_image_url=payload.profile_image_url,
        skills=payload.skills,
        metadata_json=payload.metadata,
        is_active=payload.is_active,
    )
    if payload.joined_at:
        employee.joined_at = payload.joined_at
    if payload.user_id is not None:
        employee.account_status = "active"
        employee.activation_status = "activated"
        employee.profile_completion_status = "complete"
    elif payload.email is not None:
        employee.account_status = "pending_activation"
        employee.activation_status = "activation_sent"
        employee.profile_completion_status = "prefill_pending"
    else:
        employee.account_status = "manual_no_login"
        employee.activation_status = "email_missing"
        employee.profile_completion_status = "prefill_pending"
    db.add(employee)
    db.flush()
    EventService.record_event(
        db,
        company_id=employee.company_id,
        actor_user_id=current_user.id,
        event_type="manual_employee.created",
        title=f"{employee.full_name} manually added",
        target_entity_type="employee",
        target_entity_id=employee.id,
        metadata={"role_title": employee.role, "email_provided": bool(employee.email)},
    )
    EventService.record_event(
        db,
        company_id=employee.company_id,
        actor_user_id=current_user.id,
        event_type="employee.created",
        title=f"{employee.full_name} added",
        target_entity_type="employee",
        target_entity_id=employee.id,
        metadata={"role_title": employee.role, "department_id": str(employee.department_id) if employee.department_id else None},
    )
    InvitationService.create_manual_activation_for_employee(db, employee=employee, actor_user=current_user)
    db.commit()
    return employee


@router.get("", response_model=list[EmployeeRead])
def list_employees(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
    status_filter: str | None = Query(default=None, alias="status"),
    team_id: UUID | None = None,
    include_inactive: bool = True,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Employee]:
    ensure_company_access(current_user, company_id)
    statement = select(Employee).where(Employee.company_id == company_id)
    if current_user is not None and current_user.role == "employee":
        statement = statement.where(Employee.user_id == current_user.id)
    if not include_inactive:
        statement = statement.where(Employee.is_active.is_(True))
    if status_filter:
        statement = statement.where(Employee.status == status_filter)
    if team_id:
        membership_exists = (
            select(TeamMember.id)
            .where(
                TeamMember.company_id == company_id,
                TeamMember.team_id == team_id,
                TeamMember.employee_id == Employee.id,
            )
            .exists()
        )
        statement = statement.where(or_(Employee.team_id == team_id, membership_exists))
    statement = statement.order_by(Employee.full_name.asc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@router.get("/me", response_model=EmployeeRead)
def get_my_employee_profile(
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Employee:
    return get_current_employee_profile(db, current_user)


@router.patch("/me", response_model=EmployeeRead)
def update_my_employee_profile(
    payload: EmployeeSelfUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Employee:
    employee = get_current_employee_profile(db, current_user)
    changed = update_model(employee, payload, alias_fields={"metadata": "metadata_json"})
    if changed:
        employee.profile_completion_status = "complete"
        EventService.record_event(
            db,
            company_id=employee.company_id,
            actor_user_id=current_user.id,
            event_type="employee_profile.updated",
            title=f"{employee.full_name} updated their profile",
            target_entity_type="employee",
            target_entity_id=employee.id,
            metadata={"changed_fields": sorted(changed.keys())},
        )
    db.commit()
    return employee


@router.get("/{employee_id}", response_model=EmployeeRead)
def get_employee(
    employee_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Employee:
    ensure_company_access(current_user, company_id)
    employee = get_or_404(db, Employee, employee_id, label="Employee")
    ensure_company(employee, company_id, label="Employee")
    if not can_view_employee(current_user, employee):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    return employee


@router.put("/{employee_id}", response_model=EmployeeRead)
def update_employee(
    employee_id: UUID,
    company_id: UUID,
    payload: EmployeeUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Employee:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    employee = get_or_404(db, Employee, employee_id, label="Employee")
    ensure_company(employee, company_id, label="Employee")
    if payload.current_status is not None:
        ensure_employee_status(payload.current_status)
    validate_employee_refs(
        db,
        company_id=company_id,
        user_id=payload.user_id,
        department_id=payload.department_id,
        team_id=payload.team_id,
        manager_id=payload.manager_id,
    )
    changed = update_model(
        employee,
        payload,
        alias_fields={"metadata": "metadata_json", "role_title": "role", "current_status": "status"},
    )
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
    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee(
    employee_id: UUID,
    company_id: UUID,
    actor_employee_id: UUID | None = None,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    employee = get_or_404(db, Employee, employee_id, label="Employee")
    ensure_company(employee, company_id, label="Employee")
    
    user = db.get(User, employee.user_id) if employee.user_id else None
    
    EventService.record_event(
        db,
        company_id=company_id,
        actor_employee_id=actor_employee_id,
        event_type="employee.deleted",
        title=f"{employee.full_name} deleted",
        target_entity_type="employee",
        target_entity_id=employee.id,
    )
    
    if user:
        user.is_active = False
        
    db.delete(employee)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{employee_id}/activation", response_model=EmployeeRead)
def update_employee_activation(
    employee_id: UUID,
    payload: EmployeeActivationUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Employee:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    employee = get_or_404(db, Employee, employee_id, label="Employee")
    ensure_company(employee, payload.company_id, label="Employee")
    
    if employee.is_active == payload.is_active:
        return employee
        
    employee.is_active = payload.is_active
    user = db.get(User, employee.user_id) if employee.user_id else None
    
    if user:
        user.is_active = payload.is_active

    if not payload.is_active:
        employee.status = "offline"
        
    event_type = "employee.activated" if payload.is_active else "employee.deactivated"
    title = f"{employee.full_name} activated" if payload.is_active else f"{employee.full_name} deactivated"
    
    EventService.record_event(
        db,
        company_id=payload.company_id,
        actor_employee_id=payload.actor_employee_id,
        event_type=event_type,
        title=title,
        target_entity_type="employee",
        target_entity_id=employee.id,
    )
    db.commit()
    return employee


@router.patch("/{employee_id}/status", response_model=EmployeeRead)
def update_employee_status(
    employee_id: UUID,
    payload: EmployeeStatusUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Employee:
    ensure_company_access(current_user, payload.company_id)
    employee = get_or_404(db, Employee, employee_id, label="Employee")
    ensure_company(employee, payload.company_id, label="Employee")
    if current_user.role not in OWNER_ADMIN_ROLES and employee.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission for this action")
    old_status = employee.status
    ensure_employee_status(payload.current_status)
    employee.status = payload.current_status
    EventService.record_event(
        db,
        company_id=payload.company_id,
        actor_employee_id=payload.actor_employee_id,
        event_type="employee.status_changed",
        title=f"{employee.full_name} status changed",
        target_entity_type="employee",
        target_entity_id=employee.id,
        metadata={"from": old_status, "to": payload.current_status},
    )
    db.commit()
    return employee


@router.get("/{employee_id}/activity", response_model=list[EventRead])
def get_employee_activity(
    employee_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[EventRead]:
    ensure_company_access(current_user, company_id)
    employee = get_or_404(db, Employee, employee_id, label="Employee")
    ensure_company(employee, company_id, label="Employee")
    if not can_view_employee(current_user, employee):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
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
