from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.api.utils import ensure_company, get_or_404, update_model
from app.models.company import Company
from app.models.employee import Employee
from app.models.leave_request import LeaveRequest
from app.schemas.leave_request import LeaveDecision, LeaveRequestCreate, LeaveRequestRead, LeaveRequestUpdate
from app.services.event_service import EventService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/leaves", tags=["leaves"])
employee_router = APIRouter(prefix="/employees", tags=["leaves"])


def validate_leave_refs(db: Session, company_id: UUID, employee_id: UUID, approver_employee_id: UUID | None) -> None:
    employee = get_or_404(db, Employee, employee_id, label="Employee")
    ensure_company(employee, company_id, label="Employee")
    if approver_employee_id:
        approver = get_or_404(db, Employee, approver_employee_id, label="Approver")
        ensure_company(approver, company_id, label="Approver")


@router.post("", response_model=LeaveRequestRead, status_code=status.HTTP_201_CREATED)
def create_leave_request(payload: LeaveRequestCreate, db: Session = Depends(db_session)) -> LeaveRequest:
    get_or_404(db, Company, payload.company_id, label="Company")
    validate_leave_refs(db, payload.company_id, payload.employee_id, payload.approver_employee_id)
    leave = LeaveRequest(**payload.model_dump())
    db.add(leave)
    db.flush()
    EventService.record_event(
        db,
        company_id=leave.company_id,
        actor_employee_id=leave.employee_id,
        event_type="leave.requested",
        title="Leave requested",
        target_entity_type="leave_request",
        target_entity_id=leave.id,
        metadata={
            "start_date": leave.start_date.isoformat(),
            "end_date": leave.end_date.isoformat(),
            "leave_type": leave.leave_type,
        },
    )
    if leave.approver_employee_id:
        NotificationService.create_notification(
            db,
            company_id=leave.company_id,
            recipient_employee_id=leave.approver_employee_id,
            title="Leave approval needed",
            message="A leave request is waiting for your review.",
            notification_type="leave_request_submitted",
            related_entity_type="leave_request",
            related_entity_id=leave.id,
        )
    db.commit()
    db.refresh(leave)
    return leave


@router.get("", response_model=list[LeaveRequestRead])
def list_leave_requests(
    company_id: UUID,
    db: Session = Depends(db_session),
    status_filter: str | None = Query(default=None, alias="status"),
    employee_id: UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[LeaveRequest]:
    statement = select(LeaveRequest).where(LeaveRequest.company_id == company_id)
    if status_filter:
        statement = statement.where(LeaveRequest.status == status_filter)
    if employee_id:
        statement = statement.where(LeaveRequest.employee_id == employee_id)
    statement = statement.order_by(LeaveRequest.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@router.get("/{leave_id}", response_model=LeaveRequestRead)
def get_leave_request(leave_id: UUID, company_id: UUID, db: Session = Depends(db_session)) -> LeaveRequest:
    leave = get_or_404(db, LeaveRequest, leave_id, label="Leave request")
    ensure_company(leave, company_id, label="Leave request")
    return leave


@router.put("/{leave_id}", response_model=LeaveRequestRead)
def update_leave_request(
    leave_id: UUID,
    company_id: UUID,
    payload: LeaveRequestUpdate,
    db: Session = Depends(db_session),
) -> LeaveRequest:
    leave = get_or_404(db, LeaveRequest, leave_id, label="Leave request")
    ensure_company(leave, company_id, label="Leave request")
    if payload.approver_employee_id:
        approver = get_or_404(db, Employee, payload.approver_employee_id, label="Approver")
        ensure_company(approver, company_id, label="Approver")
    changed = update_model(leave, payload)
    if leave.end_date < leave.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be on or after start_date",
        )
    if changed:
        EventService.record_event(
            db,
            company_id=company_id,
            actor_employee_id=leave.employee_id,
            event_type="leave.updated",
            title="Leave request updated",
            target_entity_type="leave_request",
            target_entity_id=leave.id,
            metadata={"changed_fields": sorted(changed.keys())},
        )
    db.commit()
    db.refresh(leave)
    return leave


@router.delete("/{leave_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_leave_request(
    leave_id: UUID,
    company_id: UUID,
    actor_employee_id: UUID | None = None,
    db: Session = Depends(db_session),
) -> Response:
    leave = get_or_404(db, LeaveRequest, leave_id, label="Leave request")
    ensure_company(leave, company_id, label="Leave request")
    leave.status = "cancelled"
    EventService.record_event(
        db,
        company_id=company_id,
        actor_employee_id=actor_employee_id or leave.employee_id,
        event_type="leave.cancelled",
        title="Leave request cancelled",
        target_entity_type="leave_request",
        target_entity_id=leave.id,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{leave_id}/approve", response_model=LeaveRequestRead)
def approve_leave_request(
    leave_id: UUID,
    payload: LeaveDecision,
    db: Session = Depends(db_session),
) -> LeaveRequest:
    leave = get_or_404(db, LeaveRequest, leave_id, label="Leave request")
    ensure_company(leave, payload.company_id, label="Leave request")
    approver = get_or_404(db, Employee, payload.approver_employee_id, label="Approver")
    ensure_company(approver, payload.company_id, label="Approver")
    leave.status = "approved"
    leave.approver_employee_id = payload.approver_employee_id
    leave.decision_note = payload.decision_note
    EventService.record_event(
        db,
        company_id=payload.company_id,
        actor_employee_id=payload.approver_employee_id,
        event_type="leave.approved",
        title="Leave request approved",
        target_entity_type="leave_request",
        target_entity_id=leave.id,
    )
    NotificationService.create_notification(
        db,
        company_id=payload.company_id,
        recipient_employee_id=leave.employee_id,
        title="Leave approved",
        message="Your leave request was approved.",
        notification_type="leave_request_approved",
        related_entity_type="leave_request",
        related_entity_id=leave.id,
    )
    db.commit()
    db.refresh(leave)
    return leave


@router.post("/{leave_id}/reject", response_model=LeaveRequestRead)
def reject_leave_request(
    leave_id: UUID,
    payload: LeaveDecision,
    db: Session = Depends(db_session),
) -> LeaveRequest:
    leave = get_or_404(db, LeaveRequest, leave_id, label="Leave request")
    ensure_company(leave, payload.company_id, label="Leave request")
    approver = get_or_404(db, Employee, payload.approver_employee_id, label="Approver")
    ensure_company(approver, payload.company_id, label="Approver")
    leave.status = "rejected"
    leave.approver_employee_id = payload.approver_employee_id
    leave.decision_note = payload.decision_note
    EventService.record_event(
        db,
        company_id=payload.company_id,
        actor_employee_id=payload.approver_employee_id,
        event_type="leave.rejected",
        title="Leave request rejected",
        target_entity_type="leave_request",
        target_entity_id=leave.id,
    )
    NotificationService.create_notification(
        db,
        company_id=payload.company_id,
        recipient_employee_id=leave.employee_id,
        title="Leave rejected",
        message="Your leave request was rejected.",
        notification_type="leave_request_rejected",
        related_entity_type="leave_request",
        related_entity_id=leave.id,
    )
    db.commit()
    db.refresh(leave)
    return leave


@employee_router.get("/{employee_id}/leaves", response_model=list[LeaveRequestRead])
def get_employee_leaves(
    employee_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[LeaveRequest]:
    employee = get_or_404(db, Employee, employee_id, label="Employee")
    ensure_company(employee, company_id, label="Employee")
    statement = (
        select(LeaveRequest)
        .where(LeaveRequest.company_id == company_id, LeaveRequest.employee_id == employee_id)
        .order_by(LeaveRequest.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())
