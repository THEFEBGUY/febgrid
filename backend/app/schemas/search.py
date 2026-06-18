from typing import Any

from pydantic import Field

from app.schemas.common import FebGridModel


class SearchResult(FebGridModel):
    type: str
    id: str
    title: str
    subtitle: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(FebGridModel):
    query: str
    results: list[SearchResult]
