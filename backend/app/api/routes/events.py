from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import db_session, get_current_user, get_optional_current_user
from app.api.serializers import serialize_event, serialize_events
from app.api.utils import ensure_company, get_or_404
from app.core.permissions import OWNER_ADMIN_ROLES, ensure_company_access, ensure_role
from app.models.company import Company
from app.models.employee import Employee
from app.models.event import Event
from app.models.user import User
from app.schemas.event import AuditLogRead, EventCreate, EventRead
from app.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["events"])
timeline_router = APIRouter(tags=["timeline"])
audit_router = APIRouter(prefix="/audit-log", tags=["audit-log"])

AUDIT_EVENT_PREFIXES = (
    "auth.",
    "billing.",
    "company.",
    "company_pulse.",
    "custom_field.",
    "department.",
    "employee.",
    "employee_account.",
    "employee_invite.",
    "employee_profile.",
    "file.",
    "industry_template.",
    "leave.",
    "manual_employee.",
    "notification.",
    "project.",
    "team.",
    "user.",
    "work_object.",
    "work_object_type.",
    "comment.",
    "announcement.",
)


def audit_event_filter():
    return or_(*(Event.event_type.ilike(f"{prefix}%") for prefix in AUDIT_EVENT_PREFIXES))


def ensure_company_timeline_access(current_user: User | None) -> None:
    if current_user is not None and current_user.role == "employee":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Employees cannot access the full company timeline")


def apply_event_filters(
    statement,
    *,
    event_type: str | None = None,
    actor_user_id: UUID | None = None,
    actor_employee_id: UUID | None = None,
    target_entity_type: str | None = None,
    target_entity_id: UUID | None = None,
    related_entity_type: str | None = None,
    related_entity_id: UUID | None = None,
    project_id: UUID | None = None,
    q: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    audit_only: bool = False,
):
    if event_type:
        statement = statement.where(Event.event_type == event_type)
    if actor_user_id:
        statement = statement.where(Event.actor_user_id == actor_user_id)
    if actor_employee_id:
        statement = statement.where(Event.actor_employee_id == actor_employee_id)
    if target_entity_type:
        statement = statement.where(Event.target_entity_type == target_entity_type)
    if target_entity_id:
        statement = statement.where(Event.target_entity_id == target_entity_id)
    if related_entity_type:
        statement = statement.where(Event.related_entity_type == related_entity_type)
    if related_entity_id:
        statement = statement.where(Event.related_entity_id == related_entity_id)
    if project_id:
        statement = statement.where(
            or_(
                (Event.target_entity_type == "project") & (Event.target_entity_id == project_id),
                (Event.related_entity_type == "project") & (Event.related_entity_id == project_id),
            )
        )
    if q:
        term = f"%{q.strip()}%"
        statement = statement.where(or_(Event.title.ilike(term), Event.description.ilike(term), Event.event_type.ilike(term)))
    if date_from:
        statement = statement.where(Event.created_at >= date_from)
    if date_to:
        statement = statement.where(Event.created_at <= date_to)
    if audit_only:
        statement = statement.where(audit_event_filter())
    return statement


def serialize_audit_event(event: Event) -> AuditLogRead:
    actor_user = event.actor_user
    actor_employee = event.actor
    company = event.company
    base = serialize_event(event)
    return AuditLogRead(
        **base.model_dump(),
        actor_name=actor_user.full_name if actor_user else None,
        actor_role=actor_user.role if actor_user else None,
        actor_employee_name=actor_employee.full_name if actor_employee else None,
        target_label=event.target_entity_type,
        company_name=company.name if company else None,
        summary=event.description or event.title,
        is_audit_relevant=True,
    )


@router.post("", response_model=EventRead)
def create_event(
    payload: EventCreate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> EventRead:
    ensure_company_access(current_user, payload.company_id)
    get_or_404(db, Company, payload.company_id, label="Company")
    event = EventService.record_event(
        db,
        company_id=payload.company_id,
        actor_user_id=payload.actor_user_id or (current_user.id if current_user is not None else None),
        actor_employee_id=payload.actor_employee_id,
        target_entity_type=payload.target_entity_type,
        target_entity_id=payload.target_entity_id,
        related_entity_type=payload.related_entity_type,
        related_entity_id=payload.related_entity_id,
        event_type=payload.event_type,
        title=payload.title,
        description=payload.description,
        metadata=payload.metadata,
    )
    db.commit()
    db.refresh(event)
    return serialize_event(event)


@router.get("", response_model=list[EventRead])
def list_events(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    event_type: str | None = None,
    actor_user_id: UUID | None = None,
    actor_employee_id: UUID | None = None,
    target_entity_type: str | None = None,
    target_entity_id: UUID | None = None,
    related_entity_type: str | None = None,
    related_entity_id: UUID | None = None,
    project_id: UUID | None = None,
    q: str | None = Query(default=None, max_length=200),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    audit_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[EventRead]:
    ensure_company_access(current_user, company_id)
    ensure_company_timeline_access(current_user)
    statement = select(Event).where(Event.company_id == company_id)
    statement = apply_event_filters(
        statement,
        event_type=event_type,
        actor_user_id=actor_user_id,
        actor_employee_id=actor_employee_id,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        project_id=project_id,
        q=q,
        date_from=date_from,
        date_to=date_to,
        audit_only=audit_only,
    )
    statement = statement.order_by(Event.created_at.desc()).limit(limit).offset(offset)
    return serialize_events(db.scalars(statement).all())


@router.get("/recent", response_model=list[EventRead])
def list_recent_events(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    limit: int = Query(default=10, ge=1, le=50),
) -> list[EventRead]:
    ensure_company_access(current_user, company_id)
    ensure_company_timeline_access(current_user)
    statement = select(Event).where(Event.company_id == company_id).order_by(Event.created_at.desc()).limit(limit)
    return serialize_events(db.scalars(statement).all())


@router.get("/{event_id}", response_model=EventRead)
def get_event(
    event_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> EventRead:
    ensure_company_access(current_user, company_id)
    ensure_company_timeline_access(current_user)
    event = get_or_404(db, Event, event_id, label="Event")
    ensure_company(event, company_id, label="Event")
    return serialize_event(event)


@timeline_router.get("/timeline", response_model=list[EventRead])
def universal_timeline(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    event_type: str | None = None,
    actor_user_id: UUID | None = None,
    actor_employee_id: UUID | None = None,
    target_entity_type: str | None = None,
    target_entity_id: UUID | None = None,
    related_entity_type: str | None = None,
    related_entity_id: UUID | None = None,
    project_id: UUID | None = None,
    q: str | None = Query(default=None, max_length=200),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    audit_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    before_created_at: datetime | None = None,
    before_id: UUID | None = None,
) -> list[EventRead]:
    ensure_company_access(current_user, company_id)
    ensure_company_timeline_access(current_user)
    statement = select(Event).where(Event.company_id == company_id)
    statement = apply_event_filters(
        statement,
        event_type=event_type,
        actor_user_id=actor_user_id,
        actor_employee_id=actor_employee_id,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        project_id=project_id,
        q=q,
        date_from=date_from,
        date_to=date_to,
        audit_only=audit_only,
    )
    if before_created_at is not None:
        if before_id is not None:
            statement = statement.where(
                or_(
                    Event.created_at < before_created_at,
                    and_(Event.created_at == before_created_at, Event.id < before_id),
                )
            )
        else:
            statement = statement.where(Event.created_at < before_created_at)
    statement = statement.order_by(Event.created_at.desc(), Event.id.desc()).limit(limit).offset(offset)
    return serialize_events(db.scalars(statement).all())


@audit_router.get("", response_model=list[AuditLogRead])
def audit_log(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
    action: str | None = Query(default=None, max_length=120),
    event_type: str | None = None,
    actor_user_id: UUID | None = None,
    actor_employee_id: UUID | None = None,
    target_entity_type: str | None = None,
    target_entity_id: UUID | None = None,
    related_entity_type: str | None = None,
    related_entity_id: UUID | None = None,
    q: str | None = Query(default=None, max_length=200),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
) -> list[AuditLogRead]:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    event_type = event_type or action
    statement = (
        select(Event)
        .options(joinedload(Event.actor_user), joinedload(Event.actor), joinedload(Event.company))
        .where(Event.company_id == company_id)
    )
    statement = apply_event_filters(
        statement,
        event_type=event_type,
        actor_user_id=actor_user_id,
        actor_employee_id=actor_employee_id,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
        q=q,
        date_from=date_from,
        date_to=date_to,
        audit_only=True,
    )
    statement = statement.order_by(Event.created_at.desc(), Event.id.desc()).limit(limit).offset(offset)
    return [serialize_audit_event(event) for event in db.scalars(statement).all()]


@audit_router.get("/{event_id}", response_model=AuditLogRead)
def get_audit_log_entry(
    event_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AuditLogRead:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    event = get_or_404(db, Event, event_id, label="Audit log entry")
    ensure_company(event, company_id, label="Audit log entry")
    statement = apply_event_filters(
        select(Event)
        .options(joinedload(Event.actor_user), joinedload(Event.actor), joinedload(Event.company))
        .where(Event.id == event.id),
        audit_only=True,
    )
    audit_event = db.scalar(statement)
    if audit_event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit log entry not found")
    return serialize_audit_event(audit_event)
