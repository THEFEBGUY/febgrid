from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user, get_optional_current_user
from app.api.utils import get_or_404
from app.core.permissions import OWNER_ADMIN_ROLES, ensure_company_access
from app.models.company import Company
from app.models.employee import Employee
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.models.user import User
from app.schemas.notification import (
    NotificationCreate,
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
    NotificationRead,
    NotificationUnreadCount,
)
from app.services.event_service import EventService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


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


def visible_notification_conditions(db: Session, current_user: User | None) -> list[object]:
    if current_user is None:
        return []
    conditions: list[object] = [Notification.recipient_user_id == current_user.id]
    linked_employee = get_linked_employee(db, current_user)
    if linked_employee is not None:
        conditions.append(Notification.recipient_employee_id == linked_employee.id)
    if current_user.role in OWNER_ADMIN_ROLES:
        conditions.append(and_(Notification.recipient_user_id.is_(None), Notification.recipient_employee_id.is_(None)))
    return conditions


def apply_notification_visibility(statement, db: Session, current_user: User | None):
    conditions = visible_notification_conditions(db, current_user)
    if conditions:
        return statement.where(or_(*conditions))
    return statement


def get_notification_for_user(
    db: Session,
    current_user: User | None,
    *,
    notification_id: UUID,
    company_id: UUID,
    include_dismissed: bool = False,
) -> Notification:
    ensure_company_access(current_user, company_id)
    notification = get_or_404(db, Notification, notification_id, label="Notification")
    if notification.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    if notification.is_dismissed and not include_dismissed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    conditions = visible_notification_conditions(db, current_user)
    if conditions:
        linked_employee = get_linked_employee(db, current_user)
        can_see = notification.recipient_user_id == current_user.id or (
            linked_employee is not None and notification.recipient_employee_id == linked_employee.id
        ) or (
            current_user.role in OWNER_ADMIN_ROLES
            and notification.recipient_user_id is None
            and notification.recipient_employee_id is None
        )
        if not can_see:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return notification


def preference_read_from_defaults(company_id: UUID) -> NotificationPreferenceRead:
    return NotificationPreferenceRead(**NotificationService.default_preferences(company_id=company_id))


def record_notification_action_event(
    db: Session,
    *,
    notification: Notification,
    current_user: User | None,
    event_type: str,
    title: str,
    metadata: dict[str, object] | None = None,
) -> None:
    linked_employee = get_linked_employee(db, current_user)
    EventService.record_event(
        db,
        company_id=notification.company_id,
        actor_user_id=current_user.id if current_user else None,
        actor_employee_id=linked_employee.id if linked_employee is not None else None,
        event_type=event_type,
        title=title,
        target_entity_type="notification",
        target_entity_id=notification.id,
        related_entity_type=notification.target_entity_type,
        related_entity_id=notification.target_entity_id,
        metadata={
            "notification_id": str(notification.id),
            "notification_type": notification.notification_type,
            "priority": notification.priority,
            **(metadata or {}),
        },
    )


@router.get("/preferences", response_model=NotificationPreferenceRead)
def get_notification_preferences(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> NotificationPreference | NotificationPreferenceRead:
    ensure_company_access(current_user, company_id)
    if current_user is None:
        return preference_read_from_defaults(company_id)
    linked_employee = get_linked_employee(db, current_user)
    preference = NotificationService.get_preferences(
        db,
        company_id=company_id,
        user_id=current_user.id,
        employee_id=linked_employee.id if linked_employee is not None else None,
    )
    return preference or NotificationPreferenceRead(
        **NotificationService.default_preferences(
            company_id=company_id,
            user_id=current_user.id,
            employee_id=linked_employee.id if linked_employee is not None else None,
        )
    )


@router.put("/preferences", response_model=NotificationPreferenceRead)
def update_notification_preferences(
    company_id: UUID,
    payload: NotificationPreferenceUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> NotificationPreference:
    ensure_company_access(current_user, company_id)
    linked_employee = get_linked_employee(db, current_user)
    updates = payload.model_dump(exclude_unset=True)
    preference = NotificationService.upsert_preferences(
        db,
        company_id=company_id,
        user_id=current_user.id,
        employee_id=linked_employee.id if linked_employee is not None else None,
        updates=updates,
    )
    EventService.record_event(
        db,
        company_id=company_id,
        actor_user_id=current_user.id,
        actor_employee_id=linked_employee.id if linked_employee is not None else None,
        event_type="notification.preference_updated",
        title="Notification preferences updated",
        target_entity_type="notification_preference",
        target_entity_id=preference.id,
        metadata={"changed_fields": sorted(updates.keys())},
    )
    db.commit()
    db.refresh(preference)
    return preference


@router.post("", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
def create_notification(
    payload: NotificationCreate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Notification:
    ensure_company_access(current_user, payload.company_id)
    get_or_404(db, Company, payload.company_id, label="Company")
    if payload.company_wide and current_user is not None and current_user.role not in OWNER_ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission for this action")
    notification = NotificationService.create_notification(
        db,
        company_id=payload.company_id,
        recipient_user_id=payload.recipient_user_id,
        recipient_employee_id=payload.recipient_employee_id,
        actor_user_id=payload.actor_user_id or (current_user.id if current_user is not None else None),
        actor_employee_id=payload.actor_employee_id,
        event_id=payload.event_id,
        target_entity_type=payload.target_entity_type,
        target_entity_id=payload.target_entity_id,
        title=payload.title,
        message=payload.message,
        notification_type=payload.notification_type,
        priority=payload.priority,
        action_url=payload.action_url,
        metadata=payload.metadata,
        company_wide=payload.company_wide,
    )
    if notification is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Notification recipient is required")
    db.commit()
    db.refresh(notification)
    return notification


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    company_id: UUID,
    recipient_user_id: UUID | None = None,
    recipient_employee_id: UUID | None = None,
    unread_only: bool = False,
    include_dismissed: bool = False,
    notification_type: str | None = None,
    priority: str | None = None,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Notification]:
    ensure_company_access(current_user, company_id)
    statement = select(Notification).where(Notification.company_id == company_id)
    statement = apply_notification_visibility(statement, db, current_user)
    if recipient_user_id:
        statement = statement.where(Notification.recipient_user_id == recipient_user_id)
    if recipient_employee_id:
        statement = statement.where(Notification.recipient_employee_id == recipient_employee_id)
    if unread_only:
        statement = statement.where(Notification.is_read.is_(False))
    if not include_dismissed:
        statement = statement.where(Notification.is_dismissed.is_(False))
    if notification_type:
        statement = statement.where(Notification.notification_type == notification_type)
    if priority:
        statement = statement.where(Notification.priority == priority.strip().lower())
    statement = statement.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@router.get("/unread-count", response_model=NotificationUnreadCount)
def get_unread_count(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> NotificationUnreadCount:
    ensure_company_access(current_user, company_id)
    statement = select(func.count(Notification.id)).where(
        Notification.company_id == company_id,
        Notification.is_read.is_(False),
        Notification.is_dismissed.is_(False),
    )
    statement = apply_notification_visibility(statement, db, current_user)
    return NotificationUnreadCount(company_id=company_id, unread_count=int(db.scalar(statement) or 0))


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Notification:
    notification = get_notification_for_user(db, current_user, notification_id=notification_id, company_id=company_id)
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        record_notification_action_event(
            db,
            notification=notification,
            current_user=current_user,
            event_type="notification.read",
            title="Notification marked read",
        )
    db.commit()
    db.refresh(notification)
    return notification


@router.patch("/{notification_id}/unread", response_model=NotificationRead)
def mark_notification_unread(
    notification_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Notification:
    notification = get_notification_for_user(db, current_user, notification_id=notification_id, company_id=company_id)
    if notification.is_read:
        notification.is_read = False
        notification.read_at = None
        record_notification_action_event(
            db,
            notification=notification,
            current_user=current_user,
            event_type="notification.unread",
            title="Notification marked unread",
        )
    db.commit()
    db.refresh(notification)
    return notification


@router.patch("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Response:
    ensure_company_access(current_user, company_id)
    statement = select(Notification).where(
        Notification.company_id == company_id,
        Notification.is_read.is_(False),
        Notification.is_dismissed.is_(False),
    )
    statement = apply_notification_visibility(statement, db, current_user)
    now = datetime.now(timezone.utc)
    notifications = list(db.scalars(statement).all())
    for notification in notifications:
        notification.is_read = True
        notification.read_at = now
    if notifications:
        linked_employee = get_linked_employee(db, current_user)
        EventService.record_event(
            db,
            company_id=company_id,
            actor_user_id=current_user.id if current_user else None,
            actor_employee_id=linked_employee.id if linked_employee is not None else None,
            event_type="notification.read_all",
            title="Notifications marked read",
            target_entity_type="notification",
            metadata={"count": len(notifications)},
        )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{notification_id}/dismiss", response_model=NotificationRead)
def dismiss_notification(
    notification_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Notification:
    notification = get_notification_for_user(db, current_user, notification_id=notification_id, company_id=company_id)
    if not notification.is_dismissed:
        notification.is_dismissed = True
        notification.dismissed_at = datetime.now(timezone.utc)
        record_notification_action_event(
            db,
            notification=notification,
            current_user=current_user,
            event_type="notification.dismissed",
            title="Notification dismissed",
        )
    db.commit()
    db.refresh(notification)
    return notification


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Response:
    notification = get_notification_for_user(db, current_user, notification_id=notification_id, company_id=company_id)
    if not notification.is_dismissed:
        notification.is_dismissed = True
        notification.dismissed_at = datetime.now(timezone.utc)
        record_notification_action_event(
            db,
            notification=notification,
            current_user=current_user,
            event_type="notification.dismissed",
            title="Notification dismissed",
        )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
