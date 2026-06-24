from typing import Any

from pydantic import Field

from app.schemas.common import FebGridModel


class SearchResult(FebGridModel):
    type: str
    id: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    related_entity_type: str | None = None
    related_entity_id: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    href: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(FebGridModel):
    query: str
    company_id: str
    total: int
    groups: dict[str, list[SearchResult]] = Field(default_factory=dict)
    results: list[SearchResult]
