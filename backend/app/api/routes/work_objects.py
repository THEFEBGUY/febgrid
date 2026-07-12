import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user, get_optional_current_user
from app.api.serializers import serialize_events
from app.api.utils import ensure_company, get_or_404
from app.core.permissions import MANAGER_ROLES, ensure_company_access, ensure_role
from app.models.attachment import Attachment
from app.models.company import Company
from app.models.department import Department
from app.models.employee import Employee
from app.models.event import Event
from app.models.project import Project
from app.models.team import Team
from app.models.user import User
from app.models.work_object import WorkObject
from app.schemas.attachment import AttachmentCreate, AttachmentRead
from app.schemas.ai_job import AIJobRead
from app.schemas.event import EventRead
from app.schemas.work_object import (
    WorkObjectAssigneeUpdate,
    WorkObjectComplete,
    WorkObjectCreate,
    WorkObjectOrgUpdate,
    WorkObjectPriorityUpdate,
    WorkObjectProjectUpdate,
    WorkObjectRead,
    WorkObjectStatusUpdate,
    WorkObjectSummary,
    WorkObjectUpdate,
)
from app.services.event_service import EventService
from app.services.file_service import FileService
from app.services.notification_service import NotificationService
from app.services.configuration_service import validate_custom_field_values, validate_work_object_type_key
from app.services.ai_service import ai_service

router = APIRouter(prefix="/work-objects", tags=["work-objects"])

WORK_OBJECT_STATUSES = {"assigned", "in_progress", "under_review", "blocked", "completed", "cancelled"}
WORK_OBJECT_PRIORITIES = {"low", "medium", "high", "critical"}
OPEN_STATUSES = {"assigned", "in_progress", "under_review", "blocked"}


def normalize_choice(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def ensure_work_object_type(db: Session, company_id: UUID, object_type: str) -> str:
    return validate_work_object_type_key(db, company_id, normalize_choice(object_type))


def ensure_work_object_status(status_value: str) -> str:
    normalized = normalize_choice(status_value)
    if normalized not in WORK_OBJECT_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid work object status")
    return normalized


def ensure_work_object_priority(priority: str) -> str:
    normalized = normalize_choice(priority)
    if normalized not in WORK_OBJECT_PRIORITIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid work object priority")
    return normalized


def get_linked_employee(db: Session, current_user: User | None) -> Employee | None:
    if current_user is None:
        return None
    cache_key = f"linked_employee:{current_user.id}"
    if cache_key in db.info:
        return db.info[cache_key]
    employee = db.scalar(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.user_id == current_user.id,
            Employee.is_active.is_(True),
        )
    )
    db.info[cache_key] = employee
    return employee


def actor_employee_id(db: Session, current_user: User | None, fallback_employee_id: UUID | None = None) -> UUID | None:
    linked_employee = get_linked_employee(db, current_user)
    return linked_employee.id if linked_employee else fallback_employee_id


def validate_work_object_refs(
    db: Session,
    *,
    company_id: UUID,
    project_id: UUID | None = None,
    department_id: UUID | None = None,
    team_id: UUID | None = None,
    creator_employee_id: UUID | None = None,
    creator_user_id: UUID | None = None,
    assignee_employee_id: UUID | None = None,
) -> None:
    checks: list[tuple[str, object]] = []
    if project_id is not None:
        checks.append(("Project", select(Project.id).where(Project.id == project_id, Project.company_id == company_id).scalar_subquery()))
    if department_id is not None:
        checks.append(("Department", select(Department.id).where(Department.id == department_id, Department.company_id == company_id).scalar_subquery()))
    if team_id is not None:
        checks.append(("Team", select(Team.id).where(Team.id == team_id, Team.company_id == company_id).scalar_subquery()))
    if creator_employee_id is not None:
        checks.append(("Creator", select(Employee.id).where(Employee.id == creator_employee_id, Employee.company_id == company_id).scalar_subquery()))
    if creator_user_id is not None:
        checks.append(("Creator user", select(User.id).where(User.id == creator_user_id, User.company_id == company_id).scalar_subquery()))
    if assignee_employee_id is not None:
        checks.append(("Assignee", select(Employee.id).where(Employee.id == assignee_employee_id, Employee.company_id == company_id).scalar_subquery()))
    if not checks:
        return
    values = db.execute(select(*(expression for _, expression in checks))).one()
    for index, (label, _) in enumerate(checks):
        if values[index] is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")


def can_view_work_object(db: Session, current_user: User | None, work_object: WorkObject) -> bool:
    if current_user is None or current_user.role in MANAGER_ROLES:
        return True
    if work_object.creator_user_id == current_user.id:
        return True
    linked_employee = get_linked_employee(db, current_user)
    if linked_employee is None:
        return False
    return work_object.assignee_employee_id == linked_employee.id or work_object.creator_employee_id == linked_employee.id


def ensure_work_object_visible(db: Session, current_user: User | None, work_object: WorkObject) -> None:
    if not can_view_work_object(db, current_user, work_object):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work object not found")


def can_update_work_status(db: Session, current_user: User | None, work_object: WorkObject) -> bool:
    if current_user is None or current_user.role in MANAGER_ROLES:
        return True
    linked_employee = get_linked_employee(db, current_user)
    return linked_employee is not None and work_object.assignee_employee_id == linked_employee.id


def record_work_event(
    db: Session,
    *,
    work_object: WorkObject,
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
        company_id=work_object.company_id,
        actor_user_id=current_user.id if current_user is not None else None,
        actor_employee_id=actor_employee_id(db, current_user, fallback_actor_employee_id),
        event_type=event_type,
        title=title,
        description=description,
        target_entity_type="work_object",
        target_entity_id=work_object.id,
        metadata=event_metadata,
    )


def work_notification_recipients(work_object: WorkObject, actor_employee_id_value: UUID | None = None) -> list[UUID]:
    recipients: list[UUID] = []
    for employee_id in [work_object.assignee_employee_id, work_object.creator_employee_id]:
        if employee_id is None or employee_id == actor_employee_id_value or employee_id in recipients:
            continue
        recipients.append(employee_id)
    return recipients


def build_work_object_data(
    payload: WorkObjectCreate | WorkObjectUpdate,
    *,
    db: Session,
    company_id: UUID,
    current_object_type: str = "task",
    validate_missing_custom_fields: bool = False,
) -> dict[str, object]:
    data = payload.model_dump(exclude_unset=True)
    if "metadata" in data:
        data["metadata_json"] = data.pop("metadata")
    object_type = current_object_type
    if "object_type" in data and data["object_type"] is not None:
        data["object_type"] = ensure_work_object_type(db, company_id, str(data["object_type"]))
        object_type = str(data["object_type"])
    if "status" in data and data["status"] is not None:
        data["status"] = ensure_work_object_status(str(data["status"]))
    if "priority" in data and data["priority"] is not None:
        data["priority"] = ensure_work_object_priority(str(data["priority"]))
    if "custom_fields" in data and data["custom_fields"] is not None:
        custom_fields = data["custom_fields"] if isinstance(data["custom_fields"], dict) else {}
        data["custom_fields"] = validate_custom_field_values(db, company_id=company_id, type_key=object_type, values=custom_fields)
    elif validate_missing_custom_fields:
        data["custom_fields"] = validate_custom_field_values(db, company_id=company_id, type_key=object_type, values={})
    if data.get("status") == "completed" and data.get("completed_at") is None:
        data["completed_at"] = datetime.now(timezone.utc)
    return data


def notify_assignment(db: Session, work_object: WorkObject, current_user: User | None, event: Event | None = None) -> None:
    if work_object.assignee_employee_id is None:
        return
    actor_id = actor_employee_id(db, current_user, work_object.creator_employee_id)
    if actor_id == work_object.assignee_employee_id:
        return
    NotificationService.create_notification(
        db,
        company_id=work_object.company_id,
        recipient_employee_id=work_object.assignee_employee_id,
        actor_user_id=current_user.id if current_user is not None else None,
        actor_employee_id=actor_id,
        event_id=event.id if event is not None else None,
        title="Work assigned",
        message=f"{work_object.title} was assigned to you.",
        notification_type="work_object.assigned",
        target_entity_type="work_object",
        target_entity_id=work_object.id,
        priority="normal",
        action_url="#/work-objects",
        metadata={"work_object_id": str(work_object.id)},
    )


def notify_work_change(
    db: Session,
    *,
    work_object: WorkObject,
    current_user: User | None,
    event: Event | None,
    notification_type: str,
    title: str,
    message: str,
    priority: str = "normal",
    fallback_actor_employee_id: UUID | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    actor_id = actor_employee_id(db, current_user, fallback_actor_employee_id)
    recipients = work_notification_recipients(work_object, actor_id)
    if not recipients:
        return
    NotificationService.create_for_employees(
        db,
        company_id=work_object.company_id,
        recipient_employee_ids=recipients,
        actor_user_id=current_user.id if current_user is not None else None,
        actor_employee_id=actor_id,
        event_id=event.id if event is not None else None,
        title=title,
        message=message,
        notification_type=notification_type,
        target_entity_type="work_object",
        target_entity_id=work_object.id,
        priority=priority,
        action_url="#/work-objects",
        metadata={"work_object_id": str(work_object.id), **(metadata or {})},
    )


def parse_metadata_form(metadata: str | None) -> dict[str, Any]:
    if not metadata:
        return {}
    try:
        parsed = json.loads(metadata)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="metadata must be valid JSON") from None
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="metadata must be a JSON object")
    return parsed


def get_work_object_for_user(
    db: Session,
    current_user: User | None,
    *,
    work_object_id: UUID,
    company_id: UUID,
) -> WorkObject:
    ensure_company_access(current_user, company_id)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, company_id, label="Work object")
    ensure_work_object_visible(db, current_user, work_object)
    return work_object


@router.post("", response_model=WorkObjectRead, status_code=status.HTTP_201_CREATED)
def create_work_object(
    payload: WorkObjectCreate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObject:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, MANAGER_ROLES)
    get_or_404(db, Company, payload.company_id, label="Company")
    creator_employee_id = payload.creator_employee_id
    creator_user_id = payload.creator_user_id
    if current_user is not None and creator_user_id is None:
        creator_user_id = current_user.id
    linked_employee = get_linked_employee(db, current_user)
    if linked_employee is not None and creator_employee_id is None:
        creator_employee_id = linked_employee.id
    validate_work_object_refs(
        db,
        company_id=payload.company_id,
        project_id=payload.project_id,
        department_id=payload.department_id,
        team_id=payload.team_id,
        creator_employee_id=creator_employee_id,
        creator_user_id=creator_user_id,
        assignee_employee_id=payload.assignee_employee_id,
    )
    work_data = build_work_object_data(
        payload,
        db=db,
        company_id=payload.company_id,
        current_object_type=payload.object_type,
        validate_missing_custom_fields=True,
    )
    work_data["creator_employee_id"] = creator_employee_id
    work_data["creator_user_id"] = creator_user_id
    work_object = WorkObject(id=uuid4(), **work_data)
    db.add(work_object)
    record_work_event(
        db,
        work_object=work_object,
        current_user=current_user,
        event_type="work_object.created",
        title=f"{work_object.title} created",
        description="Work object was created.",
        metadata={
            "object_type": work_object.object_type,
            "status": work_object.status,
            "priority": work_object.priority,
            "project_id": str(work_object.project_id) if work_object.project_id else None,
            "assignee_employee_id": str(work_object.assignee_employee_id) if work_object.assignee_employee_id else None,
        },
        fallback_actor_employee_id=work_object.creator_employee_id,
    )
    if work_object.assignee_employee_id:
        assignment_event = record_work_event(
            db,
            work_object=work_object,
            current_user=current_user,
            event_type="work_object.assigned",
            title=f"{work_object.title} assigned",
            description="Work object was assigned.",
            metadata={"assignee_employee_id": str(work_object.assignee_employee_id)},
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
        notify_assignment(db, work_object, current_user, assignment_event)
    db.commit()
    return work_object


@router.get("/summary", response_model=WorkObjectSummary)
def get_work_object_summary(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObjectSummary:
    ensure_company_access(current_user, company_id)
    statement = select(WorkObject).where(WorkObject.company_id == company_id, WorkObject.is_active.is_(True))
    if current_user is not None and current_user.role not in MANAGER_ROLES:
        linked_employee = get_linked_employee(db, current_user)
        visibility_conditions = [WorkObject.creator_user_id == current_user.id]
        if linked_employee is not None:
            visibility_conditions.extend(
                [
                    WorkObject.assignee_employee_id == linked_employee.id,
                    WorkObject.creator_employee_id == linked_employee.id,
                ]
            )
        statement = statement.where(or_(*visibility_conditions))
    work_objects = list(db.scalars(statement).all())
    now = datetime.now(timezone.utc)
    soon = now + timedelta(days=7)
    open_work_objects = [item for item in work_objects if item.status in OPEN_STATUSES]
    due_soon = 0
    overdue = 0
    for item in open_work_objects:
        if item.due_date is None:
            continue
        due_at = ensure_aware_utc(item.due_date)
        if now <= due_at <= soon:
            due_soon += 1
        elif due_at < now:
            overdue += 1

    return WorkObjectSummary(
        company_id=company_id,
        total=len(work_objects),
        open=len(open_work_objects),
        blocked=sum(1 for item in work_objects if item.status == "blocked"),
        completed=sum(1 for item in work_objects if item.status == "completed"),
        due_soon=due_soon,
        overdue=overdue,
    )


@router.get("", response_model=list[WorkObjectRead])
def list_work_objects(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    status_filter: str | None = Query(default=None, alias="status"),
    project_id: UUID | None = None,
    department_id: UUID | None = None,
    team_id: UUID | None = None,
    assignee_employee_id: UUID | None = None,
    assigned_to_employee_id: UUID | None = None,
    object_type: str | None = None,
    include_inactive: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[WorkObject]:
    ensure_company_access(current_user, company_id)
    statement = select(WorkObject).where(WorkObject.company_id == company_id)
    if not include_inactive:
        statement = statement.where(WorkObject.is_active.is_(True))
    if status_filter:
        statement = statement.where(WorkObject.status == ensure_work_object_status(status_filter))
    if project_id:
        statement = statement.where(WorkObject.project_id == project_id)
    if department_id:
        statement = statement.where(WorkObject.department_id == department_id)
    if team_id:
        statement = statement.where(WorkObject.team_id == team_id)
    assignee_filter = assignee_employee_id or assigned_to_employee_id
    if assignee_filter:
        statement = statement.where(WorkObject.assignee_employee_id == assignee_filter)
    if object_type:
        statement = statement.where(WorkObject.object_type == ensure_work_object_type(db, company_id, object_type))
    if current_user is not None and current_user.role not in MANAGER_ROLES:
        linked_employee = get_linked_employee(db, current_user)
        visibility_conditions = [WorkObject.creator_user_id == current_user.id]
        if linked_employee is not None:
            visibility_conditions.extend(
                [
                    WorkObject.assignee_employee_id == linked_employee.id,
                    WorkObject.creator_employee_id == linked_employee.id,
                ]
            )
        statement = statement.where(or_(*visibility_conditions))
    statement = statement.order_by(WorkObject.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@router.get("/{work_object_id}", response_model=WorkObjectRead)
def get_work_object(
    work_object_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObject:
    return get_work_object_for_user(db, current_user, work_object_id=work_object_id, company_id=company_id)


@router.put("/{work_object_id}", response_model=WorkObjectRead)
def update_work_object(
    work_object_id: UUID,
    company_id: UUID,
    payload: WorkObjectUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObject:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, MANAGER_ROLES)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, company_id, label="Work object")
    validate_work_object_refs(
        db,
        company_id=company_id,
        project_id=payload.project_id,
        department_id=payload.department_id,
        team_id=payload.team_id,
        creator_employee_id=payload.creator_employee_id,
        creator_user_id=payload.creator_user_id,
        assignee_employee_id=payload.assignee_employee_id,
    )
    previous_assignee = work_object.assignee_employee_id
    previous_status = work_object.status
    previous_priority = work_object.priority
    previous_project = work_object.project_id
    work_data = build_work_object_data(
        payload,
        db=db,
        company_id=company_id,
        current_object_type=work_object.object_type,
    )
    for field, value in work_data.items():
        setattr(work_object, field, value)
    if work_data:
        changed_fields = sorted("metadata" if field == "metadata_json" else field for field in work_data)
        record_work_event(
            db,
            work_object=work_object,
            current_user=current_user,
            event_type="work_object.updated",
            title=f"{work_object.title} updated",
            description="Work object was updated.",
            metadata={"changed_fields": changed_fields},
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
    if previous_assignee != work_object.assignee_employee_id:
        assignment_event = record_work_event(
            db,
            work_object=work_object,
            current_user=current_user,
            event_type="work_object.assigned",
            title=f"{work_object.title} assigned",
            description="Work object assignee was changed.",
            metadata={
                "from": str(previous_assignee) if previous_assignee else None,
                "to": str(work_object.assignee_employee_id) if work_object.assignee_employee_id else None,
            },
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
        notify_assignment(db, work_object, current_user, assignment_event)
    if previous_status != work_object.status:
        status_event = record_work_event(
            db,
            work_object=work_object,
            current_user=current_user,
            event_type="work_object.status_changed",
            title=f"{work_object.title} status changed",
            description="Work object status was changed.",
            metadata={"from": previous_status, "to": work_object.status},
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
        if work_object.status != "completed":
            notify_work_change(
                db,
                work_object=work_object,
                current_user=current_user,
                event=status_event,
                notification_type="work_object.status_changed",
                title=f"{work_object.title} status changed",
                message=f"Status changed from {previous_status} to {work_object.status}.",
                metadata={"from": previous_status, "to": work_object.status},
                fallback_actor_employee_id=work_object.creator_employee_id,
            )
    if previous_priority != work_object.priority:
        priority_event = record_work_event(
            db,
            work_object=work_object,
            current_user=current_user,
            event_type="work_object.priority_changed",
            title=f"{work_object.title} priority changed",
            description="Work object priority was changed.",
            metadata={"from": previous_priority, "to": work_object.priority},
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
        if work_object.priority in {"high", "critical"}:
            notify_work_change(
                db,
                work_object=work_object,
                current_user=current_user,
                event=priority_event,
                notification_type="work_object.priority_changed",
                title=f"{work_object.title} priority changed",
                message=f"Priority changed from {previous_priority} to {work_object.priority}.",
                priority="high" if work_object.priority == "high" else "urgent",
                metadata={"from": previous_priority, "to": work_object.priority},
                fallback_actor_employee_id=work_object.creator_employee_id,
            )
    if previous_project != work_object.project_id:
        record_work_event(
            db,
            work_object=work_object,
            current_user=current_user,
            event_type="work_object.project_changed",
            title=f"{work_object.title} project changed",
            description="Work object project link was changed.",
            metadata={
                "from": str(previous_project) if previous_project else None,
                "to": str(work_object.project_id) if work_object.project_id else None,
            },
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
    if previous_status != "completed" and work_object.status == "completed":
        completed_event = record_work_event(
            db,
            work_object=work_object,
            current_user=current_user,
            event_type="work_object.completed",
            title=f"{work_object.title} completed",
            description="Work object was completed.",
            metadata={"completed_at": work_object.completed_at.isoformat() if work_object.completed_at else None},
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
        notify_work_change(
            db,
            work_object=work_object,
            current_user=current_user,
            event=completed_event,
            notification_type="work_object.completed",
            title=f"{work_object.title} completed",
            message="Work object was completed.",
            priority="normal",
            metadata={"completed_at": work_object.completed_at.isoformat() if work_object.completed_at else None},
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
    db.commit()
    return work_object


@router.delete("/{work_object_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_work_object(
    work_object_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Response:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, MANAGER_ROLES)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, company_id, label="Work object")
    work_object.is_active = False
    record_work_event(
        db,
        work_object=work_object,
        current_user=current_user,
        event_type="work_object.archived",
        title=f"{work_object.title} archived",
        description="Work object was archived.",
        metadata={"status": work_object.status},
        fallback_actor_employee_id=work_object.creator_employee_id,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{work_object_id}/assignee", response_model=WorkObjectRead)
def assign_work_object(
    work_object_id: UUID,
    payload: WorkObjectAssigneeUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObject:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, MANAGER_ROLES)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, payload.company_id, label="Work object")
    validate_work_object_refs(db, company_id=payload.company_id, assignee_employee_id=payload.assignee_employee_id)
    previous_assignee = work_object.assignee_employee_id
    previous_status = work_object.status
    work_object.assignee_employee_id = payload.assignee_employee_id
    if work_object.status == "cancelled" and payload.assignee_employee_id is not None:
        work_object.status = "assigned"
    if previous_assignee != work_object.assignee_employee_id:
        assignment_event = record_work_event(
            db,
            work_object=work_object,
            current_user=current_user,
            event_type="work_object.assigned",
            title=f"{work_object.title} assigned",
            description="Work object assignee was changed.",
            metadata={
                "from": str(previous_assignee) if previous_assignee else None,
                "to": str(work_object.assignee_employee_id) if work_object.assignee_employee_id else None,
            },
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
        notify_assignment(db, work_object, current_user, assignment_event)
    if previous_status != work_object.status:
        status_event = record_work_event(
            db,
            work_object=work_object,
            current_user=current_user,
            event_type="work_object.status_changed",
            title=f"{work_object.title} status changed",
            description="Work object status was changed.",
            metadata={"from": previous_status, "to": work_object.status},
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
        notify_work_change(
            db,
            work_object=work_object,
            current_user=current_user,
            event=status_event,
            notification_type="work_object.status_changed",
            title=f"{work_object.title} status changed",
            message=f"Status changed from {previous_status} to {work_object.status}.",
            metadata={"from": previous_status, "to": work_object.status},
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
    db.commit()
    return work_object


@router.patch("/{work_object_id}/status", response_model=WorkObjectRead)
def update_work_object_status(
    work_object_id: UUID,
    payload: WorkObjectStatusUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObject:
    ensure_company_access(current_user, payload.company_id)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, payload.company_id, label="Work object")
    if not can_update_work_status(db, current_user, work_object):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission for this action")
    previous_status = work_object.status
    work_object.status = ensure_work_object_status(payload.status)
    if work_object.status == "completed" and work_object.completed_at is None:
        work_object.completed_at = datetime.now(timezone.utc)
    if previous_status != work_object.status:
        status_event = record_work_event(
            db,
            work_object=work_object,
            current_user=current_user,
            event_type="work_object.status_changed",
            title=f"{work_object.title} status changed",
            description="Work object status was changed.",
            metadata={"from": previous_status, "to": work_object.status},
            fallback_actor_employee_id=payload.actor_employee_id or work_object.creator_employee_id,
        )
        if work_object.status != "completed":
            notify_work_change(
                db,
                work_object=work_object,
                current_user=current_user,
                event=status_event,
                notification_type="work_object.status_changed",
                title=f"{work_object.title} status changed",
                message=f"Status changed from {previous_status} to {work_object.status}.",
                metadata={"from": previous_status, "to": work_object.status},
                fallback_actor_employee_id=payload.actor_employee_id or work_object.creator_employee_id,
            )
    if previous_status != "completed" and work_object.status == "completed":
        completed_event = record_work_event(
            db,
            work_object=work_object,
            current_user=current_user,
            event_type="work_object.completed",
            title=f"{work_object.title} completed",
            description="Work object was completed.",
            metadata={"completed_at": work_object.completed_at.isoformat() if work_object.completed_at else None},
            fallback_actor_employee_id=payload.actor_employee_id or work_object.creator_employee_id,
        )
        notify_work_change(
            db,
            work_object=work_object,
            current_user=current_user,
            event=completed_event,
            notification_type="work_object.completed",
            title=f"{work_object.title} completed",
            message="Work object was completed.",
            metadata={"completed_at": work_object.completed_at.isoformat() if work_object.completed_at else None},
            fallback_actor_employee_id=payload.actor_employee_id or work_object.creator_employee_id,
        )
    db.commit()
    return work_object


@router.patch("/{work_object_id}/priority", response_model=WorkObjectRead)
def update_work_object_priority(
    work_object_id: UUID,
    payload: WorkObjectPriorityUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObject:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, MANAGER_ROLES)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, payload.company_id, label="Work object")
    previous_priority = work_object.priority
    work_object.priority = ensure_work_object_priority(payload.priority)
    if previous_priority != work_object.priority:
        priority_event = record_work_event(
            db,
            work_object=work_object,
            current_user=current_user,
            event_type="work_object.priority_changed",
            title=f"{work_object.title} priority changed",
            description="Work object priority was changed.",
            metadata={"from": previous_priority, "to": work_object.priority},
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
        if work_object.priority in {"high", "critical"}:
            notify_work_change(
                db,
                work_object=work_object,
                current_user=current_user,
                event=priority_event,
                notification_type="work_object.priority_changed",
                title=f"{work_object.title} priority changed",
                message=f"Priority changed from {previous_priority} to {work_object.priority}.",
                priority="high" if work_object.priority == "high" else "urgent",
                metadata={"from": previous_priority, "to": work_object.priority},
                fallback_actor_employee_id=work_object.creator_employee_id,
            )
    db.commit()
    return work_object


@router.patch("/{work_object_id}/project", response_model=WorkObjectRead)
def update_work_object_project(
    work_object_id: UUID,
    payload: WorkObjectProjectUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObject:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, MANAGER_ROLES)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, payload.company_id, label="Work object")
    validate_work_object_refs(db, company_id=payload.company_id, project_id=payload.project_id)
    previous_project = work_object.project_id
    work_object.project_id = payload.project_id
    if previous_project != work_object.project_id:
        record_work_event(
            db,
            work_object=work_object,
            current_user=current_user,
            event_type="work_object.project_changed",
            title=f"{work_object.title} project changed",
            description="Work object project link was changed.",
            metadata={
                "from": str(previous_project) if previous_project else None,
                "to": str(work_object.project_id) if work_object.project_id else None,
            },
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
    db.commit()
    return work_object


@router.patch("/{work_object_id}/org", response_model=WorkObjectRead)
def update_work_object_org(
    work_object_id: UUID,
    payload: WorkObjectOrgUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObject:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, MANAGER_ROLES)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, payload.company_id, label="Work object")
    validate_work_object_refs(db, company_id=payload.company_id, department_id=payload.department_id, team_id=payload.team_id)
    previous_department = work_object.department_id
    previous_team = work_object.team_id
    work_object.department_id = payload.department_id
    work_object.team_id = payload.team_id
    if previous_department != work_object.department_id or previous_team != work_object.team_id:
        record_work_event(
            db,
            work_object=work_object,
            current_user=current_user,
            event_type="work_object.updated",
            title=f"{work_object.title} updated",
            description="Work object department or team link was changed.",
            metadata={
                "department_from": str(previous_department) if previous_department else None,
                "department_to": str(work_object.department_id) if work_object.department_id else None,
                "team_from": str(previous_team) if previous_team else None,
                "team_to": str(work_object.team_id) if work_object.team_id else None,
            },
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
    db.commit()
    return work_object


@router.post("/{work_object_id}/complete", response_model=WorkObjectRead)
def complete_work_object(
    work_object_id: UUID,
    payload: WorkObjectComplete,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> WorkObject:
    ensure_company_access(current_user, payload.company_id)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, payload.company_id, label="Work object")
    if not can_update_work_status(db, current_user, work_object):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission for this action")
    previous_status = work_object.status
    if previous_status != "completed":
        work_object.status = "completed"
        work_object.completed_at = datetime.now(timezone.utc)
        status_event = record_work_event(
            db,
            work_object=work_object,
            current_user=current_user,
            event_type="work_object.status_changed",
            title=f"{work_object.title} status changed",
            description="Work object status was changed.",
            metadata={"from": previous_status, "to": work_object.status},
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
        completed_event = record_work_event(
            db,
            work_object=work_object,
            current_user=current_user,
            event_type="work_object.completed",
            title=f"{work_object.title} completed",
            description="Work object was completed.",
            metadata={"completed_at": work_object.completed_at.isoformat()},
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
        notify_work_change(
            db,
            work_object=work_object,
            current_user=current_user,
            event=status_event,
            notification_type="work_object.status_changed",
            title=f"{work_object.title} status changed",
            message=f"Status changed from {previous_status} to {work_object.status}.",
            metadata={"from": previous_status, "to": work_object.status},
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
        notify_work_change(
            db,
            work_object=work_object,
            current_user=current_user,
            event=completed_event,
            notification_type="work_object.completed",
            title=f"{work_object.title} completed",
            message="Work object was completed.",
            metadata={"completed_at": work_object.completed_at.isoformat()},
            fallback_actor_employee_id=work_object.creator_employee_id,
        )
    db.commit()
    return work_object


@router.post("/{work_object_id}/ai-summary", response_model=AIJobRead)
def generate_work_object_ai_summary(
    work_object_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJobRead:
    work_object = get_work_object_for_user(db, current_user, work_object_id=work_object_id, company_id=company_id)
    job = ai_service.generate_summary(
        db,
        company_id=company_id,
        job_type="work_object_summary_safe",
        input_entity_type="work_object",
        input_entity_id=work_object.id,
        current_user=current_user,
    )
    db.commit()
    db.refresh(job)
    return job


@router.get("/{work_object_id}/ai-summary/latest", response_model=AIJobRead | None)
def get_latest_work_object_ai_summary(
    work_object_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJobRead | None:
    work_object = get_work_object_for_user(db, current_user, work_object_id=work_object_id, company_id=company_id)
    return ai_service.latest_summary_job(
        db,
        company_id=company_id,
        job_type="work_object_summary_safe",
        input_entity_type="work_object",
        input_entity_id=work_object.id,
        current_user=current_user,
    )


@router.get("/{work_object_id}/timeline", response_model=list[EventRead])
def get_work_object_timeline(
    work_object_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[EventRead]:
    work_object = get_work_object_for_user(db, current_user, work_object_id=work_object_id, company_id=company_id)
    statement = (
        select(Event)
        .where(
            Event.company_id == company_id,
            Event.target_entity_type == "work_object",
            Event.target_entity_id == work_object.id,
        )
        .order_by(Event.created_at.desc())
        .limit(limit)
    )
    return serialize_events(db.scalars(statement).all())


@router.post("/{work_object_id}/attachments", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
def add_work_object_attachment(
    work_object_id: UUID,
    company_id: UUID = Form(...),
    file: UploadFile = File(...),
    uploaded_by_employee_id: UUID | None = Form(default=None),
    description: str | None = Form(default=None),
    metadata: str | None = Form(default=None),
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Attachment:
    ensure_company_access(current_user, company_id)
    work_object = get_work_object_for_user(db, current_user, work_object_id=work_object_id, company_id=company_id)
    if uploaded_by_employee_id is None:
        linked_employee = get_linked_employee(db, current_user)
        uploaded_by_employee_id = linked_employee.id if linked_employee is not None else None
    if uploaded_by_employee_id is not None:
        uploader = get_or_404(db, Employee, uploaded_by_employee_id, label="Uploader")
        ensure_company(uploader, company_id, label="Uploader")
    stored_file = FileService.save_upload(file=file, company_id=company_id, work_object_id=work_object_id)
    attachment_payload = AttachmentCreate(
        company_id=company_id,
        work_object_id=work_object_id,
        project_id=work_object.project_id,
        uploaded_by_user_id=current_user.id if current_user is not None else None,
        uploaded_by_employee_id=uploaded_by_employee_id,
        linked_entity_type="work_object",
        linked_entity_id=work_object_id,
        file_name=stored_file.file_name,
        original_file_name=stored_file.original_file_name,
        content_type=stored_file.content_type,
        file_size=stored_file.file_size,
        extension=stored_file.extension,
        checksum_sha256=stored_file.checksum_sha256,
        storage_provider=stored_file.storage_provider,
        storage_path=stored_file.storage_path,
        public_url=None,
        description=description.strip() if description else None,
        tags=[],
        processing_status="uploaded",
        scan_status="not_scanned",
        metadata=parse_metadata_form(metadata),
        ai_processing_status="pending",
        is_active=True,
    )
    attachment = FileService.build_attachment(attachment_payload)
    db.add(attachment)
    db.flush()
    actor_id = actor_employee_id(db, current_user, uploaded_by_employee_id)
    file_event = EventService.record_event(
        db,
        company_id=company_id,
        actor_user_id=current_user.id if current_user is not None else None,
        actor_employee_id=actor_id,
        event_type="file.uploaded",
        title=f"{attachment.original_file_name} uploaded",
        description="File was uploaded to a work object.",
        target_entity_type="attachment",
        target_entity_id=attachment.id,
        related_entity_type="work_object",
        related_entity_id=work_object_id,
        metadata={
            "actor_user_id": str(current_user.id) if current_user else None,
            "work_object_id": str(work_object_id),
            "project_id": str(work_object.project_id) if work_object.project_id else None,
            "content_type": attachment.content_type,
            "file_size": attachment.file_size,
        },
    )
    recipients = work_notification_recipients(work_object, actor_id)
    if recipients:
        NotificationService.create_for_employees(
            db,
            company_id=company_id,
            recipient_employee_ids=recipients,
            actor_user_id=current_user.id if current_user is not None else None,
            actor_employee_id=actor_id,
            event_id=file_event.id,
            title=f"{attachment.original_file_name} uploaded",
            message=f"A file was uploaded to {work_object.title}.",
            notification_type="file.uploaded",
            target_entity_type="attachment",
            target_entity_id=attachment.id,
            priority="normal",
            action_url="#/work-objects",
            metadata={
                "work_object_id": str(work_object_id),
                "attachment_id": str(attachment.id),
                "file_size": attachment.file_size,
                "content_type": attachment.content_type,
            },
        )
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/{work_object_id}/attachments", response_model=list[AttachmentRead])
def list_work_object_attachments(
    work_object_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Attachment]:
    ensure_company_access(current_user, company_id)
    work_object = get_or_404(db, WorkObject, work_object_id, label="Work object")
    ensure_company(work_object, company_id, label="Work object")
    ensure_work_object_visible(db, current_user, work_object)
    statement = (
        select(Attachment)
        .where(
            Attachment.company_id == company_id,
            Attachment.linked_entity_type == "work_object",
            Attachment.linked_entity_id == work_object_id,
            Attachment.is_active.is_(True),
            Attachment.is_deleted.is_(False),
        )
        .order_by(Attachment.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())
