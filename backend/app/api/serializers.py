from collections.abc import Iterable
from typing import Any

from app.models.event import Event
from app.schemas.event import EventRead


def json_dict_or_empty(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def serialize_event(event: Event) -> EventRead:
    return EventRead(
        id=event.id,
        company_id=event.company_id,
        actor_employee_id=event.actor_employee_id,
        target_entity_type=event.target_entity_type,
        target_entity_id=event.target_entity_id,
        event_type=event.event_type,
        title=event.title,
        description=event.description,
        metadata=json_dict_or_empty(event.metadata_json),
        created_at=event.created_at,
    )


def serialize_events(events: Iterable[Event]) -> list[EventRead]:
    return [serialize_event(event) for event in events]
