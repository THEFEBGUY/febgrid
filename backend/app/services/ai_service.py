import json
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.utils import ensure_company, get_or_404
from app.core.permissions import MANAGER_ROLES, ensure_company_access, ensure_role
from app.models.ai_job import AIJob
from app.models.attachment import Attachment
from app.models.company import Company
from app.models.employee import Employee
from app.models.project import Project
from app.models.user import User
from app.models.work_object import WorkObject
from app.schemas.ai_job import AI_JOB_STATUSES, AI_JOB_TYPES, AICapabilitiesRead, AICapability, AIJobCreate
from app.services.event_service import EventService
from app.services.notification_service import NotificationService
from app.models.common import utc_now

AI_PROVIDER_KEY = "mock"
AI_PROVIDER_MODE = "mock"
AI_INPUT_MAX_BYTES = 20_000

CAPABILITY_DEFINITIONS = [
    AICapability(
        job_type="work_object_summary_mock",
        label="Work object summary",
        description="Prepare a future-safe mock summary for one work object.",
    ),
    AICapability(
        job_type="project_summary_mock",
        label="Project summary",
        description="Prepare a future-safe mock summary for one project.",
    ),
    AICapability(
        job_type="employee_workload_mock",
        label="Employee workload",
        description="Prepare a future-safe mock workload placeholder for one employee.",
    ),
    AICapability(
        job_type="file_summary_mock",
        label="File summary",
        description="Prepare a future-safe mock file summary without reading or parsing file contents.",
    ),
    AICapability(
        job_type="company_brief_mock",
        label="Company brief",
        description="Prepare a future-safe mock company brief placeholder.",
    ),
]


def metadata_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def linked_employee(db: Session, current_user: User | None) -> Employee | None:
    if current_user is None:
        return None
    return db.scalar(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.user_id == current_user.id,
            Employee.is_active.is_(True),
        )
    )


def safe_payload_size(payload: dict[str, Any]) -> int:
    try:
        return len(json.dumps(payload, default=str).encode("utf-8"))
    except (TypeError, ValueError):
        return AI_INPUT_MAX_BYTES + 1


class AIService:
    provider = AI_PROVIDER_KEY
    provider_mode = AI_PROVIDER_MODE

    @staticmethod
    def ensure_job_type(job_type: str) -> str:
        if job_type not in AI_JOB_TYPES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid AI job type")
        return job_type

    @staticmethod
    def ensure_status(status_value: str) -> str:
        if status_value not in AI_JOB_STATUSES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid AI job status")
        return status_value

    @staticmethod
    def actor_employee_id(db: Session, current_user: User | None) -> UUID | None:
        employee = linked_employee(db, current_user)
        return employee.id if employee else None

    @staticmethod
    def ensure_payload_safe(payload: dict[str, Any]) -> None:
        if safe_payload_size(payload) > AI_INPUT_MAX_BYTES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="AI input payload is too large")
        reserved_keys = {"system_prompt", "raw_prompt", "provider_api_key", "api_key", "secret", "password", "token"}
        blocked = sorted(key for key in payload if key.lower() in reserved_keys)
        if blocked:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="AI input payload contains unsupported prompt or secret fields",
            )

    @classmethod
    def validate_entity_access(
        cls,
        db: Session,
        *,
        company_id: UUID,
        input_entity_type: str | None,
        input_entity_id: UUID | None,
    ) -> None:
        if input_entity_type is None and input_entity_id is None:
            return
        if input_entity_type is None or input_entity_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="input_entity_type and input_entity_id must be provided together",
            )

        if input_entity_type == "company":
            company = get_or_404(db, Company, input_entity_id, label="Company")
            if company.id != company_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
            return
        if input_entity_type == "work_object":
            work_object = get_or_404(db, WorkObject, input_entity_id, label="Work object")
            ensure_company(work_object, company_id, label="Work object")
            return
        if input_entity_type == "project":
            project = get_or_404(db, Project, input_entity_id, label="Project")
            ensure_company(project, company_id, label="Project")
            return
        if input_entity_type == "employee":
            employee = get_or_404(db, Employee, input_entity_id, label="Employee")
            ensure_company(employee, company_id, label="Employee")
            return
        if input_entity_type in {"attachment", "file"}:
            attachment = get_or_404(db, Attachment, input_entity_id, label="File")
            ensure_company(attachment, company_id, label="File")
            if attachment.is_deleted or not attachment.is_active:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
            return

        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported AI input entity type")

    @classmethod
    def create_job(cls, db: Session, *, payload: AIJobCreate, current_user: User) -> AIJob:
        ensure_company_access(current_user, payload.company_id)
        ensure_role(current_user, MANAGER_ROLES)
        get_or_404(db, Company, payload.company_id, label="Company")
        cls.ensure_job_type(payload.job_type)
        cls.ensure_payload_safe(payload.input_payload)
        cls.ensure_payload_safe(payload.metadata)
        cls.validate_entity_access(
            db,
            company_id=payload.company_id,
            input_entity_type=payload.input_entity_type,
            input_entity_id=payload.input_entity_id,
        )

        requester_employee = linked_employee(db, current_user)
        job = AIJob(
            company_id=payload.company_id,
            requested_by_user_id=current_user.id,
            requested_by_employee_id=requester_employee.id if requester_employee else None,
            job_type=payload.job_type,
            status="queued",
            priority=payload.priority,
            input_entity_type=payload.input_entity_type,
            input_entity_id=payload.input_entity_id,
            input_payload=metadata_dict(payload.input_payload),
            output_payload={},
            provider_key=AI_PROVIDER_KEY,
            provider_mode=AI_PROVIDER_MODE,
            max_attempts=payload.max_attempts,
            scheduled_at=payload.scheduled_at,
            metadata_json=metadata_dict(payload.metadata),
            related_entity_type=payload.input_entity_type,
            related_entity_id=payload.input_entity_id,
        )
        db.add(job)
        db.flush()
        cls.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.created",
            title=f"Mock AI job queued: {job.job_type}",
            description="A mock AI foundation job was created.",
        )
        return job

    @classmethod
    def visible_statement(cls, company_id: UUID, current_user: User):
        ensure_company_access(current_user, company_id)
        statement = select(AIJob).where(AIJob.company_id == company_id)
        if current_user.role not in MANAGER_ROLES:
            statement = statement.where(AIJob.requested_by_user_id == current_user.id)
        return statement

    @classmethod
    def get_visible_job(cls, db: Session, *, job_id: UUID, company_id: UUID, current_user: User) -> AIJob:
        job = db.get(AIJob, job_id)
        if job is None or job.company_id != company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI job not found")
        if current_user.role not in MANAGER_ROLES and job.requested_by_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI job not found")
        return job

    @classmethod
    def ensure_manage_job(cls, current_user: User, job: AIJob) -> None:
        ensure_company_access(current_user, job.company_id)
        if current_user.role in MANAGER_ROLES:
            return
        if job.requested_by_user_id == current_user.id and job.input_entity_type != "company":
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission for this action")

    @classmethod
    def run_job(cls, db: Session, *, job: AIJob, current_user: User) -> AIJob:
        cls.ensure_manage_job(current_user, job)
        if job.status != "queued":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only queued AI jobs can be run")
        if job.attempts >= job.max_attempts:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="AI job has reached its attempt limit")

        now = utc_now()
        job.status = "running"
        job.started_at = now
        job.attempts += 1
        db.flush()
        cls.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.started",
            title=f"Mock AI job started: {job.job_type}",
            description="A mock AI foundation job started.",
        )

        try:
            job.output_payload = cls.mock_provider(job)
            job.status = "succeeded"
            job.completed_at = utc_now()
            job.error_message = None
            db.flush()
            succeeded_event = cls.record_job_event(
                db,
                job=job,
                current_user=current_user,
                event_type="ai_job.succeeded",
                title=f"Mock AI job succeeded: {job.job_type}",
                description="A mock AI foundation job completed successfully.",
            )
            cls.notify_requester(db, job=job, event_id=succeeded_event.id, success=True)
        except Exception as exc:
            job.status = "failed"
            job.failed_at = utc_now()
            job.error_message = str(exc)[:1000]
            db.flush()
            failed_event = cls.record_job_event(
                db,
                job=job,
                current_user=current_user,
                event_type="ai_job.failed",
                title=f"Mock AI job failed: {job.job_type}",
                description="A mock AI foundation job failed safely.",
            )
            cls.notify_requester(db, job=job, event_id=failed_event.id, success=False)
        return job

    @classmethod
    def cancel_job(cls, db: Session, *, job: AIJob, current_user: User) -> AIJob:
        cls.ensure_manage_job(current_user, job)
        if job.status not in {"queued", "running"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only queued or running AI jobs can be cancelled")
        job.status = "cancelled"
        job.cancelled_at = utc_now()
        db.flush()
        cls.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.cancelled",
            title=f"Mock AI job cancelled: {job.job_type}",
            description="A mock AI foundation job was cancelled.",
        )
        return job

    @classmethod
    def mock_provider(cls, job: AIJob) -> dict[str, Any]:
        entity = job.input_entity_type or "company"
        # Future provider implementations must build prompts from whitelisted templates
        # and never accept arbitrary user-supplied system prompts.
        return {
            "summary": f"Mock AI summary for {entity}. Real provider not connected.",
            "confidence": None,
            "provider": AI_PROVIDER_KEY,
            "provider_mode": AI_PROVIDER_MODE,
            "generated": False,
            "mock": True,
            "job_type": job.job_type,
            "input_entity_type": job.input_entity_type,
            "input_entity_id": str(job.input_entity_id) if job.input_entity_id else None,
            "input_payload_keys": sorted(job.input_payload.keys()) if isinstance(job.input_payload, dict) else [],
        }

    @classmethod
    def record_job_event(
        cls,
        db: Session,
        *,
        job: AIJob,
        current_user: User | None,
        event_type: str,
        title: str,
        description: str,
    ):
        return EventService.record_event(
            db,
            company_id=job.company_id,
            actor_user_id=current_user.id if current_user is not None else job.requested_by_user_id,
            actor_employee_id=cls.actor_employee_id(db, current_user) if current_user is not None else job.requested_by_employee_id,
            event_type=event_type,
            title=title,
            description=description,
            target_entity_type="ai_job",
            target_entity_id=job.id,
            related_entity_type=job.input_entity_type,
            related_entity_id=job.input_entity_id,
            metadata={
                "job_type": job.job_type,
                "status": job.status,
                "priority": job.priority,
                "provider_key": job.provider_key,
                "provider_mode": job.provider_mode,
                "attempts": job.attempts,
                "input_entity_type": job.input_entity_type,
                "input_entity_id": str(job.input_entity_id) if job.input_entity_id else None,
            },
        )

    @classmethod
    def notify_requester(cls, db: Session, *, job: AIJob, event_id: UUID, success: bool) -> None:
        title = "Mock AI job completed" if success else "Mock AI job failed"
        message = f"{job.job_type} {'completed with mock output' if success else 'failed safely'}."
        NotificationService.create_notification(
            db,
            company_id=job.company_id,
            recipient_user_id=job.requested_by_user_id,
            recipient_employee_id=job.requested_by_employee_id,
            event_id=event_id,
            target_entity_type="ai_job",
            target_entity_id=job.id,
            notification_type="ai_job.succeeded" if success else "ai_job.failed",
            title=title,
            message=message,
            priority="normal" if success else "high",
            action_url="#/settings",
            metadata={"job_type": job.job_type, "mock": True, "status": job.status},
        )

    @classmethod
    def capabilities(cls, *, company_id: UUID) -> AICapabilitiesRead:
        return AICapabilitiesRead(
            company_id=company_id,
            provider_key=AI_PROVIDER_KEY,
            provider_mode=AI_PROVIDER_MODE,
            real_ai_connected=False,
            external_calls_enabled=False,
            capabilities=CAPABILITY_DEFINITIONS,
            message="Mock AI foundation only. Real AI providers are not connected.",
        )


ai_service = AIService()
