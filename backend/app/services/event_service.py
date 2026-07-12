from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.event import Event


def metadata_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def uuid_from_metadata(value: Any) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        try:
            return UUID(value)
        except ValueError:
            return None
    return None


class EventService:
    @staticmethod
    def record_event(
        db: Session,
        *,
        company_id: UUID,
        event_type: str,
        title: str,
        actor_user_id: UUID | None = None,
        actor_employee_id: UUID | None = None,
        target_entity_type: str | None = None,
        target_entity_id: UUID | None = None,
        related_entity_type: str | None = None,
        related_entity_id: UUID | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Event:
        event_metadata = metadata_dict(metadata)
        if actor_user_id is None:
            actor_user_id = uuid_from_metadata(event_metadata.get("actor_user_id"))
        event = Event(
            id=uuid4(),
            company_id=company_id,
            actor_user_id=actor_user_id,
            actor_employee_id=actor_employee_id,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            event_type=event_type,
            title=title,
            description=description,
            metadata_json=event_metadata,
        )
        db.add(event)
        return event
