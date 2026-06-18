from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.company import HealthRead

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthRead)
def health_check() -> HealthRead:
    settings = get_settings()
    return HealthRead(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
        checked_at=datetime.now(timezone.utc),
    )
