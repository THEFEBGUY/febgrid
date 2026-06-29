from collections.abc import Iterable
from typing import Any

from app.models.event import Event
from app.schemas.event import EventRead


def json_dict_or_empty(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return sanitize_metadata(value)
    return {}


SENSITIVE_KEY_PARTS = ("token", "password", "secret", "action_path", "acceptance_url", "invite_link", "activation_link")


def sanitize_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key).lower()
            if any(part in normalized_key for part in SENSITIVE_KEY_PARTS):
                sanitized[key] = "[redacted]"
            else:
                sanitized[key] = sanitize_metadata(item)
        return sanitized
    if isinstance(value, list):
        return [sanitize_metadata(item) for item in value]
    return value


def serialize_event(event: Event) -> EventRead:
    return EventRead(
        id=event.id,
        company_id=event.company_id,
        actor_user_id=event.actor_user_id,
        actor_employee_id=event.actor_employee_id,
        target_entity_type=event.target_entity_type,
        target_entity_id=event.target_entity_id,
        related_entity_type=event.related_entity_type,
        related_entity_id=event.related_entity_id,
        event_type=event.event_type,
        title=event.title,
        description=event.description,
        metadata=json_dict_or_empty(event.metadata_json),
        created_at=event.created_at,
    )


def serialize_events(events: Iterable[Event]) -> list[EventRead]:
    return [serialize_event(event) for event in events]
