from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.event import Event
from app.models.notification import Notification
from app.models.user import User
from app.services.event_service import EventService

NOTIFICATION_PRIORITIES = {"low", "normal", "high", "urgent"}


def metadata_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def ensure_priority(priority: str) -> str:
    normalized = priority.strip().lower()
    if normalized not in NOTIFICATION_PRIORITIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid notification priority")
    return normalized


class NotificationService:
    @staticmethod
    def _get_employee(db: Session, employee_id: UUID | None) -> Employee | None:
        if employee_id is None:
            return None
        return db.get(Employee, employee_id)

    @staticmethod
    def _get_user(db: Session, user_id: UUID | None) -> User | None:
        if user_id is None:
            return None
        return db.get(User, user_id)

    @classmethod
    def _validate_employee(cls, db: Session, *, company_id: UUID, employee_id: UUID | None, label: str) -> Employee | None:
        employee = cls._get_employee(db, employee_id)
        if employee is None:
            if employee_id is None:
                return None
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
        if employee.company_id != company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
        return employee

    @classmethod
    def _validate_user(cls, db: Session, *, company_id: UUID, user_id: UUID | None, label: str) -> User | None:
        user = cls._get_user(db, user_id)
        if user is None:
            if user_id is None:
                return None
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
        if user.company_id != company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
        return user

    @staticmethod
    def _existing_open_notification(
        db: Session,
        *,
        company_id: UUID,
        recipient_user_id: UUID | None,
        recipient_employee_id: UUID | None,
        notification_type: str,
        target_entity_type: str | None,
        target_entity_id: UUID | None,
    ) -> Notification | None:
        statement = select(Notification).where(
            Notification.company_id == company_id,
            Notification.notification_type == notification_type,
            Notification.target_entity_type == target_entity_type,
            Notification.target_entity_id == target_entity_id,
            Notification.is_read.is_(False),
            Notification.is_dismissed.is_(False),
        )
        if recipient_user_id is not None:
            statement = statement.where(Notification.recipient_user_id == recipient_user_id)
        else:
            statement = statement.where(Notification.recipient_user_id.is_(None))
        if recipient_employee_id is not None:
            statement = statement.where(Notification.recipient_employee_id == recipient_employee_id)
        else:
            statement = statement.where(Notification.recipient_employee_id.is_(None))
        return db.scalar(statement.order_by(Notification.created_at.desc()).limit(1))

    @classmethod
    def create_notification(
        cls,
        db: Session,
        *,
        company_id: UUID,
        title: str,
        message: str,
        notification_type: str,
        recipient_user_id: UUID | None = None,
        recipient_employee_id: UUID | None = None,
        actor_user_id: UUID | None = None,
        actor_employee_id: UUID | None = None,
        event_id: UUID | None = None,
        target_entity_type: str | None = None,
        target_entity_id: UUID | None = None,
        related_entity_type: str | None = None,
        related_entity_id: UUID | None = None,
        priority: str = "normal",
        action_url: str | None = None,
        metadata: dict[str, Any] | None = None,
        dedupe: bool = True,
        company_wide: bool = False,
    ) -> Notification | None:
        if recipient_user_id is None and recipient_employee_id is None and not company_wide:
            return None

        target_entity_type = target_entity_type or related_entity_type
        target_entity_id = target_entity_id or related_entity_id
        notification_priority = ensure_priority(priority)
        recipient_employee = cls._validate_employee(
            db,
            company_id=company_id,
            employee_id=recipient_employee_id,
            label="Recipient",
        )
        if recipient_user_id is None and recipient_employee is not None:
            recipient_user_id = recipient_employee.user_id
        elif (
            recipient_user_id is not None
            and recipient_employee is not None
            and recipient_employee.user_id is not None
            and recipient_employee.user_id != recipient_user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Recipient user does not match recipient employee",
            )
        cls._validate_user(db, company_id=company_id, user_id=recipient_user_id, label="Recipient user")
        cls._validate_employee(db, company_id=company_id, employee_id=actor_employee_id, label="Actor")
        cls._validate_user(db, company_id=company_id, user_id=actor_user_id, label="Actor user")
        if event_id is not None:
            event = db.get(Event, event_id)
            if event is None or event.company_id != company_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        if dedupe:
            existing = cls._existing_open_notification(
                db,
                company_id=company_id,
                recipient_user_id=recipient_user_id,
                recipient_employee_id=recipient_employee_id,
                notification_type=notification_type,
                target_entity_type=target_entity_type,
                target_entity_id=target_entity_id,
            )
            if existing is not None:
                return existing

        notification = Notification(
            company_id=company_id,
            recipient_user_id=recipient_user_id,
            recipient_employee_id=recipient_employee_id,
            actor_user_id=actor_user_id,
            actor_employee_id=actor_employee_id,
            event_id=event_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=notification_priority,
            action_url=action_url,
            metadata_json=metadata_dict(metadata),
            is_read=False,
            is_dismissed=False,
        )
        db.add(notification)
        db.flush()
        sent_event = EventService.record_event(
            db,
            company_id=company_id,
            actor_user_id=actor_user_id,
            actor_employee_id=actor_employee_id,
            event_type="notification.sent",
            title=title,
            target_entity_type="notification",
            target_entity_id=notification.id,
            related_entity_type=target_entity_type,
            related_entity_id=target_entity_id,
            metadata={
                "recipient_user_id": str(recipient_user_id) if recipient_user_id else None,
                "recipient_employee_id": str(recipient_employee_id) if recipient_employee_id else None,
                "notification_type": notification_type,
                "priority": notification_priority,
                "source_event_id": str(event_id) if event_id else None,
                "company_wide": company_wide,
            },
        )
        if notification.event_id is None:
            notification.event_id = sent_event.id
        return notification

    @classmethod
    def create_for_employees(
        cls,
        db: Session,
        *,
        company_id: UUID,
        recipient_employee_ids: list[UUID],
        title: str,
        message: str,
        notification_type: str,
        actor_user_id: UUID | None = None,
        actor_employee_id: UUID | None = None,
        event_id: UUID | None = None,
        target_entity_type: str | None = None,
        target_entity_id: UUID | None = None,
        priority: str = "normal",
        action_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> list[Notification]:
        notifications: list[Notification] = []
        seen: set[UUID] = set()
        for employee_id in recipient_employee_ids:
            if employee_id in seen:
                continue
            seen.add(employee_id)
            notification = cls.create_notification(
                db,
                company_id=company_id,
                recipient_employee_id=employee_id,
                title=title,
                message=message,
                notification_type=notification_type,
                actor_user_id=actor_user_id,
                actor_employee_id=actor_employee_id,
                event_id=event_id,
                target_entity_type=target_entity_type,
                target_entity_id=target_entity_id,
                priority=priority,
                action_url=action_url,
                metadata=metadata,
            )
            if notification is not None:
                notifications.append(notification)
        return notifications
