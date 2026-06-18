from typing import Any, TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session


ModelT = TypeVar("ModelT")


def get_or_404(db: Session, model: type[ModelT], entity_id: UUID, *, label: str) -> ModelT:
    entity = db.get(model, entity_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
    return entity


def ensure_company(entity: Any, company_id: UUID, *, label: str) -> None:
    if getattr(entity, "company_id", None) != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")


def update_model(entity: Any, payload: Any, *, alias_fields: dict[str, str] | None = None) -> dict[str, Any]:
    data = payload.model_dump(exclude_unset=True)
    aliases = alias_fields or {}
    for public_name, model_name in aliases.items():
        if public_name in data:
            data[model_name] = data.pop(public_name)
    for field, value in data.items():
        setattr(entity, field, value)
    return data
