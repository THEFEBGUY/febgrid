from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.event import Event


class EventService:
    @staticmethod
    def record_event(
        db: Session,
        *,
        company_id: UUID,
        event_type: str,
        title: str,
        actor_employee_id: UUID | None = None,
        target_entity_type: str | None = None,
        target_entity_id: UUID | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Event:
        event = Event(
            company_id=company_id,
            actor_employee_id=actor_employee_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            event_type=event_type,
            title=title,
            description=description,
            metadata_json=metadata or {},
        )
        db.add(event)
        db.flush()
        return event
