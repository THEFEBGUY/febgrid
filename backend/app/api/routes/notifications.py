from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.api.utils import ensure_company, get_or_404
from app.models.company import Company
from app.models.employee import Employee
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationRead, NotificationReadUpdate
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
def create_notification(payload: NotificationCreate, db: Session = Depends(db_session)) -> Notification:
    get_or_404(db, Company, payload.company_id, label="Company")
    recipient = get_or_404(db, Employee, payload.recipient_employee_id, label="Recipient")
    ensure_company(recipient, payload.company_id, label="Recipient")
    notification = NotificationService.create_notification(
        db,
        company_id=payload.company_id,
        recipient_employee_id=payload.recipient_employee_id,
        title=payload.title,
        message=payload.message,
        notification_type=payload.notification_type,
        related_entity_type=payload.related_entity_type,
        related_entity_id=payload.related_entity_id,
    )
    db.commit()
    db.refresh(notification)
    return notification


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    company_id: UUID,
    recipient_employee_id: UUID | None = None,
    unread_only: bool = False,
    db: Session = Depends(db_session),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Notification]:
    statement = select(Notification).where(Notification.company_id == company_id)
    if recipient_employee_id:
        statement = statement.where(Notification.recipient_employee_id == recipient_employee_id)
    if unread_only:
        statement = statement.where(Notification.is_read.is_(False))
    statement = statement.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: UUID,
    payload: NotificationReadUpdate,
    db: Session = Depends(db_session),
) -> Notification:
    notification = get_or_404(db, Notification, notification_id, label="Notification")
    ensure_company(notification, payload.company_id, label="Notification")
    if notification.recipient_employee_id != payload.recipient_employee_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    notification.is_read = True
    notification.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notification)
    return notification


@router.patch("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(payload: NotificationReadUpdate, db: Session = Depends(db_session)) -> Response:
    recipient = get_or_404(db, Employee, payload.recipient_employee_id, label="Recipient")
    ensure_company(recipient, payload.company_id, label="Recipient")
    db.execute(
        update(Notification)
        .where(
            Notification.company_id == payload.company_id,
            Notification.recipient_employee_id == payload.recipient_employee_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True, read_at=datetime.now(timezone.utc))
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(notification_id: UUID, company_id: UUID, db: Session = Depends(db_session)) -> Response:
    notification = get_or_404(db, Notification, notification_id, label="Notification")
    ensure_company(notification, company_id, label="Notification")
    db.delete(notification)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
