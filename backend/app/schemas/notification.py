from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import FebGridModel


class NotificationBase(FebGridModel):
    company_id: UUID
    recipient_employee_id: UUID
    title: str = Field(min_length=1, max_length=180)
    message: str = Field(min_length=1)
    notification_type: str = Field(min_length=1, max_length=80)
    related_entity_type: str | None = Field(default=None, max_length=80)
    related_entity_id: UUID | None = None


class NotificationCreate(NotificationBase):
    pass


class NotificationRead(NotificationBase):
    id: UUID
    is_read: bool
    created_at: datetime
    read_at: datetime | None


class NotificationReadUpdate(FebGridModel):
    company_id: UUID
    recipient_employee_id: UUID
