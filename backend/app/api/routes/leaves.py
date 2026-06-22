from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_optional_current_user
from app.api.serializers import serialize_events
from app.api.utils import ensure_company, get_or_404
from app.core.permissions import MANAGER_ROLES, ensure_company_access, ensure_role
from app.models.company import Company
from app.models.employee import Employee
from app.models.event import Event
from app.models.leave_request import LeaveRequest
from app.models.user import User
from app.schemas.event import EventRead
from app.schemas.leave_request import (
    LeaveCancel,
    LeaveDecision,
    LeaveRequestCreate,
    LeaveRequestRead,
    LeaveRequestUpdate,
    LeaveSummary,
)
from app.services.event_service import EventService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/leaves", tags=["leaves"])
employee_router = APIRouter(prefix="/employees", tags=["leaves"])

LEAVE_TYPES = {"paid_leave", "sick_leave", "casual_leave", "half_day", "unpaid_leave", "work_from_home", "other"}
LEAVE_STATUSES = {"pending", "approved", "rejected", "cancelled"}


def normalize_choice(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def ensure_leave_type(leave_type: str) -> str:
    normalized = normalize_choice(leave_type)
    if normalized not in LEAVE_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid leave type")
    return normalized


def ensure_leave_status(status_value: str) -> str:
    normalized = normalize_choice(status_value)
    if normalized not in LEAVE_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid leave status")
    return normalized


def ensure_date_range(start_date: date, end_date: date) -> None:
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be on or after start_date",
        )


def calculate_total_days(start_date: date, end_date: date, leave_type: str) -> float:
    ensure_date_range(start_date, end_date)
    if ensure_leave_type(leave_type) == "half_day":
        return 0.5
    return float((end_date - start_date).days + 1)


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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


def validate_leave_refs(
    db: Session,
    *,
    company_id: UUID,
    employee_id: UUID | None = None,
    approver_employee_id: UUID | None = None,
    requested_by_user_id: UUID | None = None,
) -> None:
    if employee_id is not None:
        employee = get_or_404(db, Employee, employee_id, label="Employee")
        ensure_company(employee, company_id, label="Employee")
    if approver_employee_id is not None:
        approver = get_or_404(db, Employee, approver_employee_id, label="Approver")
        ensure_company(approver, company_id, label="Approver")
    if requested_by_user_id is not None:
        requested_by = get_or_404(db, User, requested_by_user_id, label="Requester")
        ensure_company_access(requested_by, company_id)


def can_manage_leaves(current_user: User | None) -> bool:
    return current_user is None or current_user.role in MANAGER_ROLES


def can_view_leave(db: Session, current_user: User | None, leave: LeaveRequest) -> bool:
    if can_manage_leaves(current_user):
        return True
    if current_user is not None and leave.requested_by_user_id == current_user.id:
        return True
    linked_employee = get_linked_employee(db, current_user)
    if linked_employee is None:
        return False
    return leave.employee_id == linked_employee.id or leave.approver_employee_id == linked_employee.id


def ensure_leave_visible(db: Session, current_user: User | None, leave: LeaveRequest) -> None:
    if not can_view_leave(db, current_user, leave):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Leave request not found")


def ensure_leave_actor(db: Session, current_user: User | None, leave: LeaveRequest) -> None:
    if can_manage_leaves(current_user):
        return
    linked_employee = get_linked_employee(db, current_user)
    if linked_employee is None or linked_employee.id != leave.employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission for this action")


def ensure_can_submit_for_employee(db: Session, current_user: User | None, employee_id: UUID) -> None:
    if can_manage_leaves(current_user):
        return
    linked_employee = get_linked_employee(db, current_user)
    if linked_employee is None or linked_employee.id != employee_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only submit leave for yourself")


def ensure_pending(leave: LeaveRequest) -> None:
    if leave.status != "pending":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending leave requests can be changed")


def record_leave_event(
    db: Session,
    *,
    leave: LeaveRequest,
    current_user: User | None,
    event_type: str,
    title: str,
    description: str,
    metadata: dict[str, object] | None = None,
    fallback_actor_employee_id: UUID | None = None,
) -> Event:
    event_metadata: dict[str, object] = {}
    if current_user is not None:
        event_metadata["actor_user_id"] = str(current_user.id)
    if metadata:
        event_metadata.update(metadata)
    return EventService.record_event(
        db,
        company_id=leave.company_id,
        actor_user_id=current_user.id if current_user is not None else None,
        actor_employee_id=actor_employee_id(db, current_user, fallback_actor_employee_id),
        event_type=event_type,
        title=title,
        description=description,
        target_entity_type="leave_request",
        target_entity_id=leave.id,
        metadata=event_metadata,
    )


def notify_leave_approval_needed(db: Session, leave: LeaveRequest, current_user: User | None, event: Event | None = None) -> None:
    if leave.approver_employee_id is None:
        NotificationService.create_notification(
            db,
            company_id=leave.company_id,
            actor_user_id=current_user.id if current_user is not None else None,
            actor_employee_id=actor_employee_id(db, current_user, leave.employee_id),
            event_id=event.id if event is not None else None,
            title="Leave approval needed",
            message="A leave request is waiting for review.",
            notification_type="leave.approval_needed",
            target_entity_type="leave_request",
            target_entity_id=leave.id,
            priority="normal",
            action_url="#/leaves",
            metadata={"leave_request_id": str(leave.id), "employee_id": str(leave.employee_id)},
            company_wide=True,
        )
        return
    NotificationService.create_notification(
        db,
        company_id=leave.company_id,
        recipient_employee_id=leave.approver_employee_id,
        actor_user_id=current_user.id if current_user is not None else None,
        actor_employee_id=actor_employee_id(db, current_user, leave.employee_id),
        event_id=event.id if event is not None else None,
        title="Leave approval needed",
        message="A leave request is waiting for your review.",
        notification_type="leave.approval_needed",
        target_entity_type="leave_request",
        target_entity_id=leave.id,
        priority="normal",
        action_url="#/leaves",
        metadata={"leave_request_id": str(leave.id), "employee_id": str(leave.employee_id)},
    )


def notify_leave_decision(db: Session, leave: LeaveRequest, current_user: User | None, event: Event | None = None, *, approved: bool) -> None:
    NotificationService.create_notification(
        db,
        company_id=leave.company_id,
        recipient_employee_id=leave.employee_id,
        actor_user_id=current_user.id if current_user is not None else None,
        actor_employee_id=actor_employee_id(db, current_user, leave.approver_employee_id),
        event_id=event.id if event is not None else None,
        title="Leave approved" if approved else "Leave rejected",
        message="Your leave request was approved." if approved else "Your leave request was rejected.",
        notification_type="leave.approved" if approved else "leave.rejected",
        target_entity_type="leave_request",
        target_entity_id=leave.id,
        priority="normal" if approved else "high",
        action_url="#/leaves",
        metadata={"leave_request_id": str(leave.id), "status": leave.status},
    )


def resolve_approver_employee_id(
    db: Session,
    *,
    current_user: User | None,
    company_id: UUID,
    approver_employee_id: UUID | None,
) -> UUID | None:
    if approver_employee_id is not None:
        validate_leave_refs(db, company_id=company_id, approver_employee_id=approver_employee_id)
        return approver_employee_id
    linked_employee = get_linked_employee(db, current_user)
    if linked_employee is not None and linked_employee.company_id == company_id:
        return linked_employee.id
    return None


def apply_leave_update(leave: LeaveRequest, data: dict[str, object]) -> list[str]:
    changed_fields: list[str] = []
    for field, value in data.items():
        model_field = "metadata_json" if field == "metadata" else field
        public_field = "metadata" if field == "metadata" else field
        setattr(leave, model_field, value)
        changed_fields.append(public_field)
    return sorted(set(changed_fields))


@router.post("", response_model=LeaveRequestRead, status_code=status.HTTP_201_CREATED)
def create_leave_request(
    payload: LeaveRequestCreate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> LeaveRequest:
    ensure_company_access(current_user, payload.company_id)
    get_or_404(db, Company, payload.company_id, label="Company")
    ensure_can_submit_for_employee(db, current_user, payload.employee_id)
    requested_by_user_id = payload.requested_by_user_id
    if current_user is not None and requested_by_user_id is None:
        requested_by_user_id = current_user.id
    validate_leave_refs(
        db,
        company_id=payload.company_id,
        employee_id=payload.employee_id,
        approver_employee_id=payload.approver_employee_id,
        requested_by_user_id=requested_by_user_id,
    )
    leave_type = ensure_leave_type(payload.leave_type)
    requested_status = ensure_leave_status(payload.status)
    if requested_status != "pending":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="New leave requests must start as pending")
    leave = LeaveRequest(
        company_id=payload.company_id,
        employee_id=payload.employee_id,
        approver_employee_id=payload.approver_employee_id,
        requested_by_user_id=requested_by_user_id,
        leave_type=leave_type,
        status="pending",
        start_date=payload.start_date,
        end_date=payload.end_date,
        total_days=calculate_total_days(payload.start_date, payload.end_date, leave_type),
        reason=payload.reason,
        manager_note=payload.manager_note,
        submitted_at=datetime.now(timezone.utc),
        metadata_json=payload.metadata,
        is_active=True,
    )
    db.add(leave)
    db.flush()
    requested_event = record_leave_event(
        db,
        leave=leave,
        current_user=current_user,
        event_type="leave.requested",
        title="Leave requested",
        description="Leave request was submitted.",
        metadata={
            "employee_id": str(leave.employee_id),
            "approver_employee_id": str(leave.approver_employee_id) if leave.approver_employee_id else None,
            "start_date": leave.start_date.isoformat(),
            "end_date": leave.end_date.isoformat(),
            "total_days": leave.total_days,
            "leave_type": leave.leave_type,
        },
        fallback_actor_employee_id=leave.employee_id,
    )
    notify_leave_approval_needed(db, leave, current_user, requested_event)
    db.commit()
    db.refresh(leave)
    return leave


@router.get("/summary", response_model=LeaveSummary)
def get_leave_summary(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> LeaveSummary:
    ensure_company_access(current_user, company_id)
    statement = select(LeaveRequest).where(LeaveRequest.company_id == company_id, LeaveRequest.is_active.is_(True))
    if current_user is not None and current_user.role not in MANAGER_ROLES:
        linked_employee = get_linked_employee(db, current_user)
        visibility_conditions = [LeaveRequest.requested_by_user_id == current_user.id]
        if linked_employee is not None:
            visibility_conditions.extend(
                [
                    LeaveRequest.employee_id == linked_employee.id,
                    LeaveRequest.approver_employee_id == linked_employee.id,
                ]
            )
        statement = statement.where(or_(*visibility_conditions))
    leaves = list(db.scalars(statement).all())
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=7)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return LeaveSummary(
        company_id=company_id,
        total=len(leaves),
        pending=sum(1 for item in leaves if item.status == "pending"),
        approved=sum(1 for item in leaves if item.status == "approved"),
        rejected=sum(1 for item in leaves if item.status == "rejected"),
        cancelled=sum(1 for item in leaves if item.status == "cancelled"),
        this_week=sum(1 for item in leaves if ensure_aware_utc(item.submitted_at) >= week_start),
        this_month=sum(1 for item in leaves if ensure_aware_utc(item.submitted_at) >= month_start),
    )


@router.get("", response_model=list[LeaveRequestRead])
def list_leave_requests(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    status_filter: str | None = Query(default=None, alias="status"),
    employee_id: UUID | None = None,
    include_inactive: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[LeaveRequest]:
    ensure_company_access(current_user, company_id)
    statement = select(LeaveRequest).where(LeaveRequest.company_id == company_id)
    if not include_inactive:
        statement = statement.where(LeaveRequest.is_active.is_(True))
    if status_filter:
        statement = statement.where(LeaveRequest.status == ensure_leave_status(status_filter))
    if employee_id:
        statement = statement.where(LeaveRequest.employee_id == employee_id)
    if current_user is not None and current_user.role not in MANAGER_ROLES:
        linked_employee = get_linked_employee(db, current_user)
        visibility_conditions = [LeaveRequest.requested_by_user_id == current_user.id]
        if linked_employee is not None:
            visibility_conditions.extend(
                [
                    LeaveRequest.employee_id == linked_employee.id,
                    LeaveRequest.approver_employee_id == linked_employee.id,
                ]
            )
        statement = statement.where(or_(*visibility_conditions))
    statement = statement.order_by(LeaveRequest.submitted_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@router.get("/{leave_id}", response_model=LeaveRequestRead)
def get_leave_request(
    leave_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> LeaveRequest:
    ensure_company_access(current_user, company_id)
    leave = get_or_404(db, LeaveRequest, leave_id, label="Leave request")
    ensure_company(leave, company_id, label="Leave request")
    ensure_leave_visible(db, current_user, leave)
    return leave


@router.put("/{leave_id}", response_model=LeaveRequestRead)
def update_leave_request(
    leave_id: UUID,
    company_id: UUID,
    payload: LeaveRequestUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> LeaveRequest:
    ensure_company_access(current_user, company_id)
    leave = get_or_404(db, LeaveRequest, leave_id, label="Leave request")
    ensure_company(leave, company_id, label="Leave request")
    ensure_leave_visible(db, current_user, leave)
    ensure_leave_actor(db, current_user, leave)
    ensure_pending(leave)

    data = payload.model_dump(exclude_unset=True)
    if "status" in data:
        requested_status = ensure_leave_status(str(data.pop("status")))
        if requested_status != leave.status:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Use leave workflow endpoints to change status")
    if "leave_type" in data and data["leave_type"] is not None:
        data["leave_type"] = ensure_leave_type(str(data["leave_type"]))
    if "employee_id" in data or "approver_employee_id" in data:
        validate_leave_refs(
            db,
            company_id=company_id,
            employee_id=data.get("employee_id") if isinstance(data.get("employee_id"), UUID) else None,
            approver_employee_id=data.get("approver_employee_id") if isinstance(data.get("approver_employee_id"), UUID) else None,
        )
    if "is_active" in data:
        ensure_role(current_user, MANAGER_ROLES)

    changed_fields = apply_leave_update(leave, data)
    leave.total_days = calculate_total_days(leave.start_date, leave.end_date, leave.leave_type)
    if changed_fields:
        updated_event = record_leave_event(
            db,
            leave=leave,
            current_user=current_user,
            event_type="leave.updated",
            title="Leave request updated",
            description="Pending leave request was updated.",
            metadata={"changed_fields": changed_fields},
            fallback_actor_employee_id=leave.employee_id,
        )
        if "approver_employee_id" in changed_fields:
            notify_leave_approval_needed(db, leave, current_user, updated_event)
    db.commit()
    db.refresh(leave)
    return leave


@router.post("/{leave_id}/approve", response_model=LeaveRequestRead)
def approve_leave_request(
    leave_id: UUID,
    payload: LeaveDecision,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> LeaveRequest:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, MANAGER_ROLES)
    leave = get_or_404(db, LeaveRequest, leave_id, label="Leave request")
    ensure_company(leave, payload.company_id, label="Leave request")
    ensure_pending(leave)
    approver_employee_id = resolve_approver_employee_id(
        db,
        current_user=current_user,
        company_id=payload.company_id,
        approver_employee_id=payload.approver_employee_id,
    )
    leave.status = "approved"
    leave.approver_employee_id = approver_employee_id
    leave.manager_note = payload.manager_note
    leave.approved_at = datetime.now(timezone.utc)
    leave.rejected_at = None
    leave.cancelled_at = None
    approved_event = record_leave_event(
        db,
        leave=leave,
        current_user=current_user,
        event_type="leave.approved",
        title="Leave request approved",
        description="Leave request was approved.",
        metadata={
            "employee_id": str(leave.employee_id),
            "approver_employee_id": str(leave.approver_employee_id) if leave.approver_employee_id else None,
            "manager_note": leave.manager_note,
        },
        fallback_actor_employee_id=leave.approver_employee_id,
    )
    notify_leave_decision(db, leave, current_user, approved_event, approved=True)
    db.commit()
    db.refresh(leave)
    return leave


@router.post("/{leave_id}/reject", response_model=LeaveRequestRead)
def reject_leave_request(
    leave_id: UUID,
    payload: LeaveDecision,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> LeaveRequest:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, MANAGER_ROLES)
    leave = get_or_404(db, LeaveRequest, leave_id, label="Leave request")
    ensure_company(leave, payload.company_id, label="Leave request")
    ensure_pending(leave)
    approver_employee_id = resolve_approver_employee_id(
        db,
        current_user=current_user,
        company_id=payload.company_id,
        approver_employee_id=payload.approver_employee_id,
    )
    leave.status = "rejected"
    leave.approver_employee_id = approver_employee_id
    leave.manager_note = payload.manager_note
    leave.rejected_at = datetime.now(timezone.utc)
    leave.approved_at = None
    leave.cancelled_at = None
    rejected_event = record_leave_event(
        db,
        leave=leave,
        current_user=current_user,
        event_type="leave.rejected",
        title="Leave request rejected",
        description="Leave request was rejected.",
        metadata={
            "employee_id": str(leave.employee_id),
            "approver_employee_id": str(leave.approver_employee_id) if leave.approver_employee_id else None,
            "manager_note": leave.manager_note,
        },
        fallback_actor_employee_id=leave.approver_employee_id,
    )
    notify_leave_decision(db, leave, current_user, rejected_event, approved=False)
    db.commit()
    db.refresh(leave)
    return leave


@router.post("/{leave_id}/cancel", response_model=LeaveRequestRead)
def cancel_leave_request(
    leave_id: UUID,
    payload: LeaveCancel,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> LeaveRequest:
    ensure_company_access(current_user, payload.company_id)
    leave = get_or_404(db, LeaveRequest, leave_id, label="Leave request")
    ensure_company(leave, payload.company_id, label="Leave request")
    ensure_leave_visible(db, current_user, leave)
    ensure_leave_actor(db, current_user, leave)
    if leave.status not in {"pending", "approved"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only pending or approved leave can be cancelled")
    previous_status = leave.status
    leave.status = "cancelled"
    leave.cancelled_at = datetime.now(timezone.utc)
    leave.manager_note = payload.manager_note or leave.manager_note
    record_leave_event(
        db,
        leave=leave,
        current_user=current_user,
        event_type="leave.cancelled",
        title="Leave request cancelled",
        description="Leave request was cancelled.",
        metadata={"from": previous_status, "manager_note": leave.manager_note},
        fallback_actor_employee_id=payload.actor_employee_id or leave.employee_id,
    )
    db.commit()
    db.refresh(leave)
    return leave


@router.delete("/{leave_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_leave_request(
    leave_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Response:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, MANAGER_ROLES)
    leave = get_or_404(db, LeaveRequest, leave_id, label="Leave request")
    ensure_company(leave, company_id, label="Leave request")
    leave.is_active = False
    record_leave_event(
        db,
        leave=leave,
        current_user=current_user,
        event_type="leave.updated",
        title="Leave request archived",
        description="Leave request was archived.",
        metadata={"status": leave.status, "is_active": leave.is_active},
        fallback_actor_employee_id=leave.approver_employee_id or leave.employee_id,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{leave_id}/timeline", response_model=list[EventRead])
def get_leave_timeline(
    leave_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[EventRead]:
    leave = get_leave_request(leave_id, company_id, db=db, current_user=current_user)
    statement = (
        select(Event)
        .where(
            Event.company_id == company_id,
            Event.target_entity_type == "leave_request",
            Event.target_entity_id == leave.id,
        )
        .order_by(Event.created_at.desc())
        .limit(limit)
    )
    return serialize_events(db.scalars(statement).all())


@employee_router.get("/{employee_id}/leaves", response_model=list[LeaveRequestRead])
def get_employee_leaves(
    employee_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[LeaveRequest]:
    ensure_company_access(current_user, company_id)
    employee = get_or_404(db, Employee, employee_id, label="Employee")
    ensure_company(employee, company_id, label="Employee")
    if current_user is not None and current_user.role not in MANAGER_ROLES:
        linked_employee = get_linked_employee(db, current_user)
        if linked_employee is None or linked_employee.id != employee_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
    statement = (
        select(LeaveRequest)
        .where(
            LeaveRequest.company_id == company_id,
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.is_active.is_(True),
        )
        .order_by(LeaveRequest.submitted_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())
