from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import OWNER_ADMIN_ROLES
from app.models.employee import Employee
from app.models.event import Event
from app.models.notification import Notification
from app.models.notification_preference import NotificationPreference
from app.models.user import User
from app.services.email_service import EmailService
from app.services.event_service import EventService

NOTIFICATION_PRIORITIES = {"low", "normal", "high", "urgent"}
PREFERENCE_FIELDS = {
    "in_app_enabled",
    "email_enabled",
    "mentions_enabled",
    "assignments_enabled",
    "leave_decisions_enabled",
    "project_updates_enabled",
    "announcements_enabled",
}


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
    def preference_flag_for_type(notification_type: str) -> str | None:
        if notification_type in {"communication.mentioned", "comment.mentioned"}:
            return "mentions_enabled"
        if notification_type.startswith("comment."):
            return "mentions_enabled"
        if notification_type.startswith("work_object."):
            return "assignments_enabled"
        if notification_type.startswith("leave."):
            return "leave_decisions_enabled"
        if notification_type.startswith("project."):
            return "project_updates_enabled"
        if notification_type.startswith("announcement."):
            return "announcements_enabled"
        return None

    @staticmethod
    def default_preferences(
        *,
        company_id: UUID,
        user_id: UUID | None = None,
        employee_id: UUID | None = None,
    ) -> dict[str, Any]:
        return {
            "company_id": company_id,
            "user_id": user_id,
            "employee_id": employee_id,
            "in_app_enabled": True,
            "email_enabled": False,
            "mentions_enabled": True,
            "assignments_enabled": True,
            "leave_decisions_enabled": True,
            "project_updates_enabled": True,
            "announcements_enabled": True,
        }

    @classmethod
    def get_preferences(
        cls,
        db: Session,
        *,
        company_id: UUID,
        user_id: UUID | None = None,
        employee_id: UUID | None = None,
    ) -> NotificationPreference | None:
        if user_id is not None:
            preference = db.scalar(
                select(NotificationPreference).where(
                    NotificationPreference.company_id == company_id,
                    NotificationPreference.user_id == user_id,
                )
            )
            if preference is not None:
                return preference
        if employee_id is not None:
            return db.scalar(
                select(NotificationPreference).where(
                    NotificationPreference.company_id == company_id,
                    NotificationPreference.employee_id == employee_id,
                )
            )
        return None

    @classmethod
    def upsert_preferences(
        cls,
        db: Session,
        *,
        company_id: UUID,
        user_id: UUID | None,
        employee_id: UUID | None,
        updates: dict[str, bool | None],
    ) -> NotificationPreference:
        preference = cls.get_preferences(db, company_id=company_id, user_id=user_id, employee_id=employee_id)
        if preference is None:
            preference = NotificationPreference(**cls.default_preferences(company_id=company_id, user_id=user_id, employee_id=employee_id))
            db.add(preference)
            db.flush()
        for field, value in updates.items():
            if field in PREFERENCE_FIELDS and value is not None:
                setattr(preference, field, value)
        db.flush()
        return preference

    @classmethod
    def in_app_allowed(
        cls,
        *,
        preferences: NotificationPreference | None,
        notification_type: str,
        company_wide: bool,
    ) -> bool:
        if preferences is None or company_wide:
            return True
        if not preferences.in_app_enabled:
            return False
        preference_flag = cls.preference_flag_for_type(notification_type)
        if preference_flag is None:
            return True
        return bool(getattr(preferences, preference_flag, True))

    @staticmethod
    def owner_admin_user_ids(
        db: Session,
        *,
        company_id: UUID,
        exclude_user_ids: set[UUID] | None = None,
    ) -> list[UUID]:
        exclude_user_ids = exclude_user_ids or set()
        users = db.scalars(
            select(User).where(
                User.company_id == company_id,
                User.role.in_(OWNER_ADMIN_ROLES),
                User.is_active.is_(True),
            )
        ).all()
        return [user.id for user in users if user.id not in exclude_user_ids]

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
        recipient_user = cls._validate_user(db, company_id=company_id, user_id=recipient_user_id, label="Recipient user")
        cls._validate_employee(db, company_id=company_id, employee_id=actor_employee_id, label="Actor")
        cls._validate_user(db, company_id=company_id, user_id=actor_user_id, label="Actor user")
        if event_id is not None:
            # EventService intentionally only adds events to the unit of work.
            # Sessions run with autoflush disabled, so make a just-created event
            # visible before validating the notification's event reference.
            db.flush()
            event = db.get(Event, event_id)
            if event is None or event.company_id != company_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        preferences = cls.get_preferences(
            db,
            company_id=company_id,
            user_id=recipient_user_id,
            employee_id=recipient_employee_id,
        )
        if not cls.in_app_allowed(preferences=preferences, notification_type=notification_type, company_wide=company_wide):
            return None

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

        metadata_payload = dict(metadata_dict(metadata))
        existing_delivery = metadata_payload.get("delivery")
        delivery_metadata = dict(existing_delivery) if isinstance(existing_delivery, dict) else {}
        delivery_metadata["in_app"] = {"channel": "in_app", "status": "pending"}
        delivery_metadata["email"] = EmailService.prepare_notification_delivery(
            notification_type=notification_type,
            title=title,
            recipient_user=recipient_user,
            recipient_employee=recipient_employee,
            preferences=preferences,
            company_wide=company_wide,
        )
        metadata_payload["delivery"] = delivery_metadata

        notification = Notification(
            id=uuid4(),
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
            metadata_json=metadata_payload,
            is_read=False,
            is_dismissed=False,
        )
        db.add(notification)
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
                "email_delivery": delivery_metadata["email"],
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
        exclude_employee_ids: set[UUID] | None = None,
        exclude_user_ids: set[UUID] | None = None,
    ) -> list[Notification]:
        notifications: list[Notification] = []
        seen: set[UUID] = set()
        exclude_employee_ids = exclude_employee_ids or set()
        exclude_user_ids = exclude_user_ids or set()
        for employee_id in recipient_employee_ids:
            if employee_id in seen or employee_id in exclude_employee_ids:
                continue
            seen.add(employee_id)
            employee = cls._validate_employee(db, company_id=company_id, employee_id=employee_id, label="Recipient")
            if employee is not None and employee.user_id is not None and employee.user_id in exclude_user_ids:
                continue
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

    @classmethod
    def create_for_users(
        cls,
        db: Session,
        *,
        company_id: UUID,
        recipient_user_ids: list[UUID],
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
        exclude_user_ids: set[UUID] | None = None,
    ) -> list[Notification]:
        notifications: list[Notification] = []
        seen: set[UUID] = set()
        exclude_user_ids = exclude_user_ids or set()
        for user_id in recipient_user_ids:
            if user_id in seen or user_id in exclude_user_ids:
                continue
            seen.add(user_id)
            notification = cls.create_notification(
                db,
                company_id=company_id,
                recipient_user_id=user_id,
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

    @classmethod
    def create_for_owner_admins(
        cls,
        db: Session,
        *,
        company_id: UUID,
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
        exclude_user_ids: set[UUID] | None = None,
    ) -> list[Notification]:
        user_ids = cls.owner_admin_user_ids(db, company_id=company_id, exclude_user_ids=exclude_user_ids)
        return cls.create_for_users(
            db,
            company_id=company_id,
            recipient_user_ids=user_ids,
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
            exclude_user_ids=exclude_user_ids,
        )
