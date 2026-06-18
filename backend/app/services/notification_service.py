from uuid import UUID

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.services.event_service import EventService


class NotificationService:
    @staticmethod
    def create_notification(
        db: Session,
        *,
        company_id: UUID,
        recipient_employee_id: UUID,
        title: str,
        message: str,
        notification_type: str,
        related_entity_type: str | None = None,
        related_entity_id: UUID | None = None,
    ) -> Notification:
        notification = Notification(
            company_id=company_id,
            recipient_employee_id=recipient_employee_id,
            title=title,
            message=message,
            notification_type=notification_type,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
        )
        db.add(notification)
        db.flush()
        EventService.record_event(
            db,
            company_id=company_id,
            event_type="notification.sent",
            title=title,
            target_entity_type="notification",
            target_entity_id=notification.id,
            metadata={
                "recipient_employee_id": str(recipient_employee_id),
                "notification_type": notification_type,
                "related_entity_type": related_entity_type,
                "related_entity_id": str(related_entity_id) if related_entity_id else None,
            },
        )
        return notification
