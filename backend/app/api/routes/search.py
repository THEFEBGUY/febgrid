from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_optional_current_user
from app.core.permissions import ensure_company_access
from app.models.user import User
from app.schemas.search import SearchResponse
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
def search(
    company_id: UUID,
    q: str | None = Query(default=None, max_length=200),
    types: str | None = Query(default=None, description="Comma-separated result groups to include."),
    limit: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> SearchResponse:
    ensure_company_access(current_user, company_id)
    requested_types = [item.strip() for item in types.split(",")] if types else None
    return SearchService.search(
        db,
        company_id=company_id,
        query=q,
        types=requested_types,
        limit=limit,
        current_user=current_user,
    )
