from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.api.utils import get_or_404
from app.core.permissions import OWNER_ADMIN_ROLES, ensure_company_access, ensure_role
from app.models.company import Company
from app.models.user import User
from app.schemas.billing import BillingSummaryRead, BillingUsageRead, CompanyBillingPlanRead, CompanyPlanUpdate, PlanDefinitionRead
from app.services.billing_service import BillingService, utc_now

router = APIRouter(prefix="/billing", tags=["billing"])


def get_company_for_billing(db: Session, company_id: UUID, current_user: User) -> Company:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    return get_or_404(db, Company, company_id, label="Company")


def plan_definition_read(plan) -> PlanDefinitionRead:
    return PlanDefinitionRead(
        key=plan.key,
        name=plan.name,
        description=plan.description,
        seat_limit=plan.seat_limit,
        storage_limit_mb=plan.storage_limit_mb,
        work_object_limit=plan.work_object_limit,
        project_limit=plan.project_limit,
        employee_limit=plan.employee_limit,
        notification_limit=plan.notification_limit,
        file_upload_limit_mb=plan.file_upload_limit_mb,
        metadata=plan.metadata,
    )


@router.get("/plans", response_model=list[PlanDefinitionRead])
def list_plans(current_user: User = Depends(get_current_user)) -> list[PlanDefinitionRead]:
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    return [plan_definition_read(plan) for plan in BillingService.plan_definitions()]


@router.get("/usage", response_model=BillingUsageRead)
def billing_usage(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> BillingUsageRead:
    get_company_for_billing(db, company_id, current_user)
    return BillingService.usage(db, company_id)


@router.get("/summary", response_model=BillingSummaryRead)
def billing_summary(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> BillingSummaryRead:
    company = get_company_for_billing(db, company_id, current_user)
    plan = BillingService.ensure_company_plan(db, company)
    usage = BillingService.usage(db, company.id)
    summary = BillingSummaryRead(
        company_id=company.id,
        company_name=company.name,
        generated_at=utc_now(),
        plan=CompanyBillingPlanRead.model_validate(plan),
        usage=usage,
        warnings=BillingService.warnings(plan, usage),
    )
    db.commit()
    return summary


@router.put("/company-plan", response_model=CompanyBillingPlanRead)
def update_company_plan(
    company_id: UUID,
    payload: CompanyPlanUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> CompanyBillingPlanRead:
    company = get_company_for_billing(db, company_id, current_user)
    plan = BillingService.ensure_company_plan(db, company)
    updates = payload.model_dump(exclude_unset=True)
    updated_plan = BillingService.update_company_plan(db, plan=plan, actor_user=current_user, updates=updates)
    db.commit()
    db.refresh(updated_plan)
    return CompanyBillingPlanRead.model_validate(updated_plan)
