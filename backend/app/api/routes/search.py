from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.schemas.search import SearchResponse
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(
    company_id: UUID,
    q: str = Query(min_length=1),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(db_session),
) -> SearchResponse:
    return SearchService.search(db, company_id=company_id, query=q, limit=limit)
