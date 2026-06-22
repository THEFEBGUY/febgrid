from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_optional_current_user
from app.api.serializers import serialize_event, serialize_events
from app.api.utils import ensure_company, get_or_404
from app.core.permissions import ensure_company_access
from app.models.company import Company
from app.models.event import Event
from app.models.user import User
from app.schemas.event import EventCreate, EventRead
from app.services.event_service import EventService

router = APIRouter(prefix="/events", tags=["events"])
timeline_router = APIRouter(tags=["timeline"])


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
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[EventRead]:
    ensure_company_access(current_user, company_id)
    statement = select(Event).where(Event.company_id == company_id)
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
    event = get_or_404(db, Event, event_id, label="Event")
    ensure_company(event, company_id, label="Event")
    return serialize_event(event)


@timeline_router.get("/timeline", response_model=list[EventRead])
def universal_timeline(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    event_type: str | None = None,
    target_entity_type: str | None = None,
    target_entity_id: UUID | None = None,
    related_entity_type: str | None = None,
    related_entity_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
) -> list[EventRead]:
    ensure_company_access(current_user, company_id)
    statement = select(Event).where(Event.company_id == company_id)
    if event_type:
        statement = statement.where(Event.event_type == event_type)
    if target_entity_type:
        statement = statement.where(Event.target_entity_type == target_entity_type)
    if target_entity_id:
        statement = statement.where(Event.target_entity_id == target_entity_id)
    if related_entity_type:
        statement = statement.where(Event.related_entity_type == related_entity_type)
    if related_entity_id:
        statement = statement.where(Event.related_entity_id == related_entity_id)
    statement = statement.order_by(Event.created_at.desc()).limit(limit).offset(offset)
    return serialize_events(db.scalars(statement).all())
