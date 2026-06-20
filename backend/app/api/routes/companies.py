from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_optional_current_user
from app.api.utils import get_or_404, update_model
from app.core.permissions import OWNER_ADMIN_ROLES, ensure_company_access, ensure_role
from app.models.company import Company
from app.models.user import User
from app.schemas.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.services.event_service import EventService

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyRead, status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyCreate, db: Session = Depends(db_session)) -> Company:
    company = Company(
        name=payload.name,
        slug=payload.slug,
        industry=payload.industry,
        size=payload.size,
        timezone=payload.timezone,
        description=payload.description,
        settings_json=payload.settings,
    )
    db.add(company)
    db.flush()
    EventService.record_event(
        db,
        company_id=company.id,
        event_type="company.created",
        title=f"{company.name} created",
        target_entity_type="company",
        target_entity_id=company.id,
    )
    db.commit()
    db.refresh(company)
    return company


@router.get("", response_model=list[CompanyRead])
def list_companies(
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    include_inactive: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Company]:
    if current_user is not None:
        statement = select(Company).where(Company.id == current_user.company_id)
        if not include_inactive:
            statement = statement.where(Company.is_active.is_(True))
        company = db.scalar(statement)
        return [company] if company is not None else []

    statement = select(Company).order_by(Company.created_at.desc()).limit(limit).offset(offset)
    if not include_inactive:
        statement = statement.where(Company.is_active.is_(True))
    return list(db.scalars(statement).all())


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Company:
    ensure_company_access(current_user, company_id)
    return get_or_404(db, Company, company_id, label="Company")


@router.put("/{company_id}", response_model=CompanyRead)
def update_company(
    company_id: UUID,
    payload: CompanyUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Company:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    company = get_or_404(db, Company, company_id, label="Company")
    changed = update_model(company, payload, alias_fields={"settings": "settings_json"})
    if changed:
        EventService.record_event(
            db,
            company_id=company.id,
            event_type="company.updated",
            title=f"{company.name} updated",
            target_entity_type="company",
            target_entity_id=company.id,
            metadata={"changed_fields": sorted(changed.keys())},
        )
    db.commit()
    db.refresh(company)
    return company


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_company(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Response:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    company = get_or_404(db, Company, company_id, label="Company")
    company.is_active = False
    EventService.record_event(
        db,
        company_id=company.id,
        event_type="company.deactivated",
        title=f"{company.name} deactivated",
        target_entity_type="company",
        target_entity_id=company.id,
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
