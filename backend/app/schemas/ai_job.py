from typing import Any
from uuid import UUID

from pydantic import Field

from app.schemas.common import FebGridModel, Timestamped


class AIJobBase(FebGridModel):
    company_id: UUID
    requested_by_employee_id: UUID | None = None
    job_type: str = Field(min_length=1, max_length=100)
    input_payload: dict[str, Any] = Field(default_factory=dict)
    related_entity_type: str | None = Field(default=None, max_length=80)
    related_entity_id: UUID | None = None


class AIJobCreate(AIJobBase):
    pass


class AIJobRead(AIJobBase, Timestamped):
    id: UUID
    status: str
    output_payload: dict[str, Any]
    error_message: str | None
