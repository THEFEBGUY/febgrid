from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attachment import Attachment
from app.models.billing import CompanyBillingPlan
from app.models.company import Company
from app.models.department import Department
from app.models.employee import Employee
from app.models.event import Event
from app.models.notification import Notification
from app.models.project import Project
from app.models.team import Team
from app.models.user import User
from app.models.work_object import WorkObject
from app.schemas.billing import BillingUsageRead, UsageWarningRead
from app.services.event_service import EventService


@dataclass(frozen=True)
class PlanDefinition:
    key: str
    name: str
    description: str
    seat_limit: int
    storage_limit_mb: int
    work_object_limit: int
    project_limit: int
    employee_limit: int
    notification_limit: int | None
    file_upload_limit_mb: int
    metadata: dict[str, Any]


PLAN_DEFINITIONS: dict[str, PlanDefinition] = {
    "free": PlanDefinition(
        key="free",
        name="Free",
        description="Local MVP plan for small teams and testing.",
        seat_limit=5,
        storage_limit_mb=100,
        work_object_limit=100,
        project_limit=3,
        employee_limit=5,
        notification_limit=None,
        file_upload_limit_mb=10,
        metadata={"payment_provider": "not_configured"},
    ),
    "starter": PlanDefinition(
        key="starter",
        name="Starter",
        description="Prepared paid-plan tier for early operating teams.",
        seat_limit=25,
        storage_limit_mb=2048,
        work_object_limit=500,
        project_limit=20,
        employee_limit=25,
        notification_limit=None,
        file_upload_limit_mb=25,
        metadata={"payment_provider": "not_configured"},
    ),
    "growth": PlanDefinition(
        key="growth",
        name="Growth",
        description="Prepared paid-plan tier for growing companies.",
        seat_limit=100,
        storage_limit_mb=10240,
        work_object_limit=5000,
        project_limit=100,
        employee_limit=100,
        notification_limit=None,
        file_upload_limit_mb=50,
        metadata={"payment_provider": "not_configured"},
    ),
    "enterprise": PlanDefinition(
        key="enterprise",
        name="Enterprise",
        description="Prepared enterprise tier for future custom contracts.",
        seat_limit=1000,
        storage_limit_mb=102400,
        work_object_limit=100000,
        project_limit=1000,
        employee_limit=1000,
        notification_limit=None,
        file_upload_limit_mb=100,
        metadata={"payment_provider": "not_configured", "custom_contract": True},
    ),
}

VALID_BILLING_STATUSES = {"trialing", "active", "past_due", "cancelled", "suspended", "free"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def metadata_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


class BillingService:
    @staticmethod
    def plan_definitions() -> list[PlanDefinition]:
        return list(PLAN_DEFINITIONS.values())

    @staticmethod
    def plan_definition(plan_key: str) -> PlanDefinition:
        plan = PLAN_DEFINITIONS.get(plan_key)
        if plan is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid plan key")
        return plan

    @classmethod
    def ensure_company_plan(cls, db: Session, company: Company) -> CompanyBillingPlan:
        plan = db.scalar(select(CompanyBillingPlan).where(CompanyBillingPlan.company_id == company.id))
        if plan is not None:
            return plan
        definition = cls.plan_definition("free")
        now = utc_now()
        plan = CompanyBillingPlan(
            company_id=company.id,
            plan_key=definition.key,
            billing_status="free",
            trial_start_at=None,
            trial_ends_at=None,
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            seat_limit=definition.seat_limit,
            storage_limit_mb=definition.storage_limit_mb,
            work_object_limit=definition.work_object_limit,
            project_limit=definition.project_limit,
            employee_limit=definition.employee_limit,
            notification_limit=definition.notification_limit,
            file_upload_limit_mb=definition.file_upload_limit_mb,
            is_trial=False,
            is_active=True,
            metadata_json={"source": "default_free_plan", **definition.metadata},
        )
        db.add(plan)
        db.flush()
        return plan

    @staticmethod
    def usage(db: Session, company_id: UUID) -> BillingUsageRead:
        active_employees = db.scalar(
            select(func.count()).select_from(Employee).where(Employee.company_id == company_id, Employee.is_active.is_(True))
        ) or 0
        active_projects = db.scalar(
            select(func.count()).select_from(Project).where(Project.company_id == company_id, Project.is_active.is_(True))
        ) or 0
        active_work_objects = db.scalar(
            select(func.count()).select_from(WorkObject).where(WorkObject.company_id == company_id, WorkObject.is_active.is_(True))
        ) or 0
        uploaded_file_count = db.scalar(
            select(func.count()).select_from(Attachment).where(Attachment.company_id == company_id, Attachment.is_active.is_(True))
        ) or 0
        storage_bytes = db.scalar(
            select(func.coalesce(func.sum(Attachment.file_size), 0)).where(
                Attachment.company_id == company_id,
                Attachment.is_active.is_(True),
            )
        ) or 0
        active_departments = db.scalar(
            select(func.count()).select_from(Department).where(Department.company_id == company_id, Department.is_active.is_(True))
        ) or 0
        active_teams = db.scalar(select(func.count()).select_from(Team).where(Team.company_id == company_id, Team.is_active.is_(True))) or 0
        notifications_count = db.scalar(select(func.count()).select_from(Notification).where(Notification.company_id == company_id)) or 0
        month_start = utc_now() - timedelta(days=30)
        monthly_events_count = db.scalar(
            select(func.count()).select_from(Event).where(Event.company_id == company_id, Event.created_at >= month_start)
        ) or 0
        return BillingUsageRead(
            company_id=company_id,
            active_employees=int(active_employees),
            active_projects=int(active_projects),
            active_work_objects=int(active_work_objects),
            uploaded_file_count=int(uploaded_file_count),
            storage_used_mb=round(float(storage_bytes) / (1024 * 1024), 2),
            active_departments=int(active_departments),
            active_teams=int(active_teams),
            notifications_count=int(notifications_count),
            monthly_events_count=int(monthly_events_count),
        )

    @staticmethod
    def warnings(plan: CompanyBillingPlan, usage: BillingUsageRead) -> list[UsageWarningRead]:
        checks = [
            ("employee_limit", usage.active_employees, plan.employee_limit, "active employees"),
            ("project_limit", usage.active_projects, plan.project_limit, "active projects"),
            ("work_object_limit", usage.active_work_objects, plan.work_object_limit, "active work objects"),
            ("storage_limit", usage.storage_used_mb, plan.storage_limit_mb, "storage usage"),
        ]
        warnings: list[UsageWarningRead] = []
        for code_prefix, current, limit, label in checks:
            if limit <= 0:
                continue
            ratio = float(current) / float(limit)
            if ratio >= 1:
                warnings.append(
                    UsageWarningRead(
                        code=f"{code_prefix}_reached",
                        message=f"{label.title()} is at or above the prepared plan limit.",
                        current=float(current),
                        limit=float(limit),
                        severity="critical",
                    )
                )
            elif ratio >= 0.8:
                warnings.append(
                    UsageWarningRead(
                        code=f"{code_prefix}_near",
                        message=f"{label.title()} is nearing the prepared plan limit.",
                        current=float(current),
                        limit=float(limit),
                        severity="warning",
                    )
                )
        return warnings

    @classmethod
    def update_company_plan(
        cls,
        db: Session,
        *,
        plan: CompanyBillingPlan,
        actor_user: User,
        updates: dict[str, Any],
    ) -> CompanyBillingPlan:
        if "metadata" in updates:
            updates["metadata_json"] = updates.pop("metadata") or {}
        if "plan_key" in updates and updates["plan_key"] is not None:
            definition = cls.plan_definition(str(updates["plan_key"]))
            for field in [
                "seat_limit",
                "storage_limit_mb",
                "work_object_limit",
                "project_limit",
                "employee_limit",
                "notification_limit",
                "file_upload_limit_mb",
            ]:
                updates.setdefault(field, getattr(definition, field))
            if updates.get("billing_status") is None:
                updates["billing_status"] = "free" if definition.key == "free" else "active"
        if "billing_status" in updates and updates["billing_status"] is not None and updates["billing_status"] not in VALID_BILLING_STATUSES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid billing status")

        before = {
            "plan_key": plan.plan_key,
            "billing_status": plan.billing_status,
            "seat_limit": plan.seat_limit,
            "storage_limit_mb": plan.storage_limit_mb,
            "work_object_limit": plan.work_object_limit,
            "project_limit": plan.project_limit,
            "employee_limit": plan.employee_limit,
            "file_upload_limit_mb": plan.file_upload_limit_mb,
        }
        changed: dict[str, Any] = {}
        for field, value in updates.items():
            if value is None and field not in {"trial_start_at", "trial_ends_at", "current_period_start", "current_period_end", "notification_limit"}:
                continue
            if not hasattr(plan, field):
                continue
            if getattr(plan, field) != value:
                setattr(plan, field, value)
                changed[field] = value
        if changed:
            EventService.record_event(
                db,
                company_id=plan.company_id,
                actor_user_id=actor_user.id,
                event_type="billing.plan_changed",
                title="Billing plan changed",
                description="Local/dev billing preparation plan was updated.",
                target_entity_type="billing_plan",
                target_entity_id=plan.id,
                metadata={"before": before, "after": {key: getattr(plan, key) for key in before}, "changed_fields": sorted(changed)},
            )
        return plan
