import json
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.utils import ensure_company, get_or_404
from app.core.ai_config import REAL_AI_PROVIDER_MODES, get_ai_provider_config, normalize_provider_mode
from app.core.permissions import MANAGER_ROLES, OWNER_ADMIN_ROLES, ensure_company_access, ensure_role
from app.models.ai_job import AIJob
from app.models.attachment import Attachment
from app.models.common import utc_now
from app.models.company import Company
from app.models.employee import Employee
from app.models.project import Project
from app.models.user import User
from app.models.work_object import WorkObject
from app.schemas.ai_job import (
    AI_JOB_STATUSES,
    AI_JOB_TYPES,
    MOCK_AI_JOB_TYPES,
    REAL_AI_JOB_TYPES,
    AICapabilitiesRead,
    AICapability,
    AIJobCreate,
    AIProviderStatusRead,
    AISafetySettingsRead,
    AISafetySettingsUpdate,
)
from app.services.ai_providers import AIProviderError, AIProviderRequest, build_ai_provider
from app.services.event_service import EventService
from app.services.notification_service import NotificationService

AI_INPUT_MAX_BYTES = 20_000
COMPANY_AI_SETTINGS_KEY = "ai"
RESERVED_AI_KEYS = {"system_prompt", "raw_prompt", "provider_api_key", "api_key", "secret", "password", "token"}

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
    AICapability(
        job_type="work_object_summary_safe",
        label="Safe work summary",
        description="Run a small text-only work object summary through the configured provider.",
        mock_only=False,
    ),
    AICapability(
        job_type="project_summary_safe",
        label="Safe project summary",
        description="Run a small text-only project summary through the configured provider.",
        mock_only=False,
    ),
    AICapability(
        job_type="company_brief_safe",
        label="Safe company brief",
        description="Run a small count-based company brief through the configured provider.",
        mock_only=False,
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


def safe_text(value: Any, max_chars: int = 1200) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_chars]


def contains_reserved_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in RESERVED_AI_KEYS:
                return True
            if contains_reserved_key(nested):
                return True
    if isinstance(value, list):
        return any(contains_reserved_key(item) for item in value)
    return False


class AIService:
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
    def ensure_payload_safe(payload: dict[str, Any], *, max_bytes: int = AI_INPUT_MAX_BYTES) -> None:
        if safe_payload_size(payload) > max_bytes:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="AI input payload is too large")
        if contains_reserved_key(payload):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="AI input payload contains unsupported prompt or secret fields",
            )

    @classmethod
    def company_ai_settings(cls, company: Company) -> dict[str, Any]:
        settings = metadata_dict(company.settings_json)
        raw_ai = metadata_dict(settings.get(COMPANY_AI_SETTINGS_KEY))
        runtime = get_ai_provider_config()
        allowed_types = raw_ai.get("allowed_ai_job_types")
        if not isinstance(allowed_types, list):
            allowed_types = sorted(AI_JOB_TYPES)
        normalized_allowed = sorted({str(item).strip() for item in allowed_types if str(item).strip() in AI_JOB_TYPES})
        return {
            "ai_enabled": bool(raw_ai.get("ai_enabled", True)),
            "external_ai_processing_allowed": bool(raw_ai.get("external_ai_processing_allowed", False)),
            "default_provider_mode": normalize_provider_mode(raw_ai.get("default_provider_mode") or runtime.provider_mode),
            "allowed_ai_job_types": normalized_allowed or sorted(AI_JOB_TYPES),
            "max_monthly_ai_jobs": raw_ai.get("max_monthly_ai_jobs") if isinstance(raw_ai.get("max_monthly_ai_jobs"), int) else None,
            "metadata": metadata_dict(raw_ai.get("metadata")),
        }

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

    @staticmethod
    def validate_job_entity_pair(job_type: str, input_entity_type: str | None) -> None:
        expected = {
            "work_object_summary_safe": "work_object",
            "project_summary_safe": "project",
            "company_brief_safe": "company",
        }
        if job_type in expected and input_entity_type != expected[job_type]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{job_type} requires input_entity_type={expected[job_type]}",
            )

    @classmethod
    def resolved_provider_mode(cls, job_type: str, company_settings: dict[str, Any]) -> str:
        if job_type in MOCK_AI_JOB_TYPES:
            return "mock"
        return normalize_provider_mode(company_settings.get("default_provider_mode"))

    @classmethod
    def provider_key_for_mode(cls, provider_mode: str) -> str:
        if provider_mode == "groq":
            return "groq"
        if provider_mode == "mock":
            return "mock"
        return provider_mode

    @classmethod
    def create_job(cls, db: Session, *, payload: AIJobCreate, current_user: User) -> AIJob:
        ensure_company_access(current_user, payload.company_id)
        ensure_role(current_user, MANAGER_ROLES)
        company = get_or_404(db, Company, payload.company_id, label="Company")
        cls.ensure_job_type(payload.job_type)
        cls.ensure_payload_safe(payload.input_payload)
        cls.ensure_payload_safe(payload.metadata)
        cls.validate_job_entity_pair(payload.job_type, payload.input_entity_type)
        cls.validate_entity_access(
            db,
            company_id=payload.company_id,
            input_entity_type=payload.input_entity_type,
            input_entity_id=payload.input_entity_id,
        )

        company_settings = cls.company_ai_settings(company)
        if payload.job_type not in company_settings["allowed_ai_job_types"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AI job type is not allowed for this company")
        provider_mode = cls.resolved_provider_mode(payload.job_type, company_settings)
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
            provider_key=cls.provider_key_for_mode(provider_mode),
            provider_mode=provider_mode,
            max_attempts=payload.max_attempts,
            scheduled_at=payload.scheduled_at,
            metadata_json={
                **metadata_dict(payload.metadata),
                "provider_mode_requested": provider_mode,
                "external_processing_used": False,
                "safety_status": "queued",
            },
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
            title=f"AI job queued: {job.job_type}",
            description="A tenant-safe AI foundation job was created.",
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
    def build_safe_context(cls, db: Session, job: AIJob) -> dict[str, Any]:
        if job.input_entity_type == "work_object" and job.input_entity_id:
            work_object = get_or_404(db, WorkObject, job.input_entity_id, label="Work object")
            ensure_company(work_object, job.company_id, label="Work object")
            return {
                "type": "work_object",
                "title": safe_text(work_object.title),
                "description": safe_text(work_object.description, 1600),
                "status": safe_text(work_object.status),
                "priority": safe_text(work_object.priority),
                "object_type": safe_text(work_object.object_type),
                "due_date": work_object.due_date.isoformat() if work_object.due_date else None,
            }
        if job.input_entity_type == "project" and job.input_entity_id:
            project = get_or_404(db, Project, job.input_entity_id, label="Project")
            ensure_company(project, job.company_id, label="Project")
            return {
                "type": "project",
                "name": safe_text(project.name),
                "description": safe_text(project.description, 1600),
                "status": safe_text(project.status),
                "priority": safe_text(project.priority),
                "progress_percent": project.progress_percent,
                "risk_level": safe_text(project.risk_level),
                "due_date": project.due_date.isoformat() if project.due_date else None,
            }
        if job.input_entity_type == "company":
            company = get_or_404(db, Company, job.company_id, label="Company")
            return {
                "type": "company",
                "name": safe_text(company.name),
                "industry": safe_text(company.industry),
                "size": safe_text(company.size),
                "employees": db.scalar(select(func.count(Employee.id)).where(Employee.company_id == job.company_id, Employee.is_active.is_(True))) or 0,
                "projects": db.scalar(select(func.count(Project.id)).where(Project.company_id == job.company_id, Project.is_active.is_(True))) or 0,
                "work_objects": db.scalar(
                    select(func.count(WorkObject.id)).where(WorkObject.company_id == job.company_id, WorkObject.is_active.is_(True))
                )
                or 0,
            }
        return {"type": job.input_entity_type or "company"}

    @staticmethod
    def build_messages(job: AIJob, entity_context: dict[str, Any], max_input_chars: int) -> list[dict[str, str]]:
        user_payload = {
            "job_type": job.job_type,
            "entity_context": entity_context,
            "input_payload": metadata_dict(job.input_payload),
            "output_contract": {
                "summary": "short plain-language operational summary",
                "key_points": ["up to 5 concise bullets"],
                "risks": ["up to 3 concise risks"],
                "next_actions": ["up to 3 practical next steps"],
                "confidence": None,
            },
        }
        serialized = json.dumps(user_payload, default=str)[:max_input_chars]
        return [
            {
                "role": "system",
                "content": (
                    "You are FebGrid's safety-constrained business operating system assistant. "
                    "Use only the provided structured context. Do not infer secrets. Do not request or reveal tokens, "
                    "passwords, API keys, file paths, or credentials. Return compact JSON only."
                ),
            },
            {"role": "user", "content": serialized},
        ]

    @classmethod
    def run_job(cls, db: Session, *, job: AIJob, current_user: User) -> AIJob:
        cls.ensure_manage_job(current_user, job)
        if job.status != "queued":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only queued AI jobs can be run")
        if job.attempts >= job.max_attempts:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="AI job has reached its attempt limit")

        runtime = get_ai_provider_config()
        company = get_or_404(db, Company, job.company_id, label="Company")
        company_settings = cls.company_ai_settings(company)
        provider_mode = cls.resolved_provider_mode(job.job_type, company_settings)

        now = utc_now()
        job.status = "running"
        job.started_at = now
        job.attempts += 1
        job.provider_key = cls.provider_key_for_mode(provider_mode)
        job.provider_mode = provider_mode
        db.flush()
        cls.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.started",
            title=f"AI job started: {job.job_type}",
            description="A tenant-safe AI foundation job started.",
        )

        try:
            if not company_settings["ai_enabled"]:
                raise AIProviderError("ai_disabled", "AI is disabled for this company.")
            if job.job_type not in company_settings["allowed_ai_job_types"]:
                raise AIProviderError("job_type_not_allowed", "AI job type is not allowed for this company.")
            if provider_mode in REAL_AI_PROVIDER_MODES:
                if job.job_type not in REAL_AI_JOB_TYPES:
                    raise AIProviderError("job_type_not_allowed", "Real provider execution is limited to safe text-only job types.")
                if not runtime.external_processing_enabled or not company_settings["external_ai_processing_allowed"]:
                    raise AIProviderError("external_processing_disabled", "External AI processing is disabled for this company.")
            entity_context = cls.build_safe_context(db, job)
            messages = cls.build_messages(job, entity_context, runtime.groq_max_input_chars)
            provider = build_ai_provider(provider_mode, runtime)
            result = provider.generate(
                AIProviderRequest(
                    job_type=job.job_type,
                    input_entity_type=job.input_entity_type,
                    input_entity_id=str(job.input_entity_id) if job.input_entity_id else None,
                    input_payload=metadata_dict(job.input_payload),
                    entity_context=entity_context,
                    messages=messages,
                    max_input_chars=runtime.groq_max_input_chars,
                )
            )
            job.output_payload = metadata_dict(result.output_payload)
            job.provider_key = result.provider_key
            job.provider_mode = result.provider_mode
            job.status = "succeeded"
            job.completed_at = utc_now()
            job.error_message = None
            job.metadata_json = cls.merged_job_metadata(
                job,
                {
                    "provider_key": result.provider_key,
                    "provider_mode": result.provider_mode,
                    "model_name": result.model_name,
                    "latency_ms": result.latency_ms,
                    "input_token_estimate": result.input_token_estimate,
                    "output_token_estimate": result.output_token_estimate,
                    "safety_status": result.safety_status,
                    "external_processing_used": result.external_processing_used,
                    "provider_metadata": metadata_dict(result.metadata),
                },
            )
            db.flush()
            succeeded_event = cls.record_job_event(
                db,
                job=job,
                current_user=current_user,
                event_type="ai_job.succeeded",
                title=f"AI job succeeded: {job.job_type}",
                description="A tenant-safe AI foundation job completed successfully.",
            )
            cls.notify_requester(db, job=job, event_id=succeeded_event.id, success=True)
        except AIProviderError as exc:
            cls.fail_job(db, job=job, current_user=current_user, error_code=exc.code, error_message=exc.safe_message, metadata=exc.metadata)
        except Exception:
            cls.fail_job(
                db,
                job=job,
                current_user=current_user,
                error_code="provider_unknown_error",
                error_message="AI job failed safely.",
                metadata={},
            )
        return job

    @classmethod
    def fail_job(
        cls,
        db: Session,
        *,
        job: AIJob,
        current_user: User,
        error_code: str,
        error_message: str,
        metadata: dict[str, Any],
    ) -> None:
        job.status = "failed"
        job.failed_at = utc_now()
        job.error_message = error_message[:1000]
        job.metadata_json = cls.merged_job_metadata(
            job,
            {
                "error_code": error_code,
                "error_message": error_message[:500],
                "safety_status": "failed_safely",
                "external_processing_used": False,
                "provider_metadata": metadata_dict(metadata),
            },
        )
        db.flush()
        failed_event = cls.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.failed",
            title=f"AI job failed: {job.job_type}",
            description=error_message[:500],
        )
        cls.notify_requester(db, job=job, event_id=failed_event.id, success=False)

    @staticmethod
    def merged_job_metadata(job: AIJob, updates: dict[str, Any]) -> dict[str, Any]:
        current = metadata_dict(job.metadata_json)
        return {**current, **{key: value for key, value in updates.items() if value is not None}}

    @classmethod
    def cancel_job(cls, db: Session, *, job: AIJob, current_user: User) -> AIJob:
        cls.ensure_manage_job(current_user, job)
        if job.status not in {"queued", "running"}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only queued or running AI jobs can be cancelled")
        job.status = "cancelled"
        job.cancelled_at = utc_now()
        job.metadata_json = cls.merged_job_metadata(job, {"safety_status": "cancelled", "external_processing_used": False})
        db.flush()
        cls.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.cancelled",
            title=f"AI job cancelled: {job.job_type}",
            description="A tenant-safe AI foundation job was cancelled.",
        )
        return job

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
        metadata = metadata_dict(job.metadata_json)
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
                "model_name": metadata.get("model_name"),
                "safety_status": metadata.get("safety_status"),
                "external_processing_used": bool(metadata.get("external_processing_used", False)),
                "error_code": metadata.get("error_code"),
                "attempts": job.attempts,
                "input_entity_type": job.input_entity_type,
                "input_entity_id": str(job.input_entity_id) if job.input_entity_id else None,
            },
        )

    @classmethod
    def notify_requester(cls, db: Session, *, job: AIJob, event_id: UUID, success: bool) -> None:
        title = "AI job completed" if success else "AI job failed"
        message = f"{job.job_type} {'completed' if success else 'failed safely'}."
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
            metadata={"job_type": job.job_type, "provider_mode": job.provider_mode, "status": job.status},
        )

    @classmethod
    def capabilities(cls, db: Session, *, company_id: UUID, current_user: User) -> AICapabilitiesRead:
        status_read = cls.provider_status(db, company_id=company_id, current_user=current_user, require_admin=False)
        return AICapabilitiesRead(
            company_id=company_id,
            provider_key=status_read.provider_key,
            provider_mode=status_read.provider_mode,
            real_ai_connected=status_read.real_ai_connected,
            external_calls_enabled=status_read.external_processing_enabled and status_read.external_processing_allowed,
            capabilities=CAPABILITY_DEFINITIONS,
            message=status_read.message,
        )

    @classmethod
    def safety_settings(cls, db: Session, *, company_id: UUID, current_user: User) -> AISafetySettingsRead:
        ensure_company_access(current_user, company_id)
        ensure_role(current_user, OWNER_ADMIN_ROLES)
        company = get_or_404(db, Company, company_id, label="Company")
        settings = cls.company_ai_settings(company)
        return AISafetySettingsRead(company_id=company_id, **settings)

    @classmethod
    def update_safety_settings(
        cls,
        db: Session,
        *,
        company_id: UUID,
        payload: AISafetySettingsUpdate,
        current_user: User,
    ) -> AISafetySettingsRead:
        ensure_company_access(current_user, company_id)
        ensure_role(current_user, OWNER_ADMIN_ROLES)
        company = get_or_404(db, Company, company_id, label="Company")
        current_settings = cls.company_ai_settings(company)
        settings_json = dict(metadata_dict(company.settings_json))
        updated = dict(metadata_dict(settings_json.get(COMPANY_AI_SETTINGS_KEY)))
        if payload.ai_enabled is not None:
            updated["ai_enabled"] = payload.ai_enabled
        if payload.external_ai_processing_allowed is not None:
            updated["external_ai_processing_allowed"] = payload.external_ai_processing_allowed
        if payload.default_provider_mode is not None:
            updated["default_provider_mode"] = normalize_provider_mode(payload.default_provider_mode)
        if payload.allowed_ai_job_types is not None:
            updated["allowed_ai_job_types"] = sorted({item for item in payload.allowed_ai_job_types if item in AI_JOB_TYPES})
        if payload.max_monthly_ai_jobs is not None:
            updated["max_monthly_ai_jobs"] = payload.max_monthly_ai_jobs
        if payload.metadata is not None:
            cls.ensure_payload_safe(payload.metadata)
            updated["metadata"] = metadata_dict(payload.metadata)

        settings_json[COMPANY_AI_SETTINGS_KEY] = updated
        company.settings_json = settings_json
        db.flush()

        next_settings = cls.company_ai_settings(company)
        cls.record_settings_event(db, company_id=company_id, current_user=current_user, old=current_settings, new=next_settings)
        return AISafetySettingsRead(company_id=company_id, **next_settings)

    @classmethod
    def record_settings_event(
        cls,
        db: Session,
        *,
        company_id: UUID,
        current_user: User,
        old: dict[str, Any],
        new: dict[str, Any],
    ) -> None:
        EventService.record_event(
            db,
            company_id=company_id,
            actor_user_id=current_user.id,
            actor_employee_id=cls.actor_employee_id(db, current_user),
            event_type="ai_settings.updated",
            title="AI safety settings updated",
            description="AI provider and external processing safety settings were updated.",
            target_entity_type="company",
            target_entity_id=company_id,
            metadata={
                "ai_enabled": new.get("ai_enabled"),
                "external_ai_processing_allowed": new.get("external_ai_processing_allowed"),
                "default_provider_mode": new.get("default_provider_mode"),
                "allowed_job_types_count": len(new.get("allowed_ai_job_types", [])),
            },
        )
        if old.get("external_ai_processing_allowed") != new.get("external_ai_processing_allowed"):
            event_type = "ai_external_processing.enabled" if new.get("external_ai_processing_allowed") else "ai_external_processing.disabled"
            event = EventService.record_event(
                db,
                company_id=company_id,
                actor_user_id=current_user.id,
                actor_employee_id=cls.actor_employee_id(db, current_user),
                event_type=event_type,
                title="External AI processing updated",
                description="External AI processing was explicitly toggled by an owner/admin.",
                target_entity_type="company",
                target_entity_id=company_id,
                metadata={"enabled": bool(new.get("external_ai_processing_allowed"))},
            )
            NotificationService.create_notification(
                db,
                company_id=company_id,
                recipient_user_id=current_user.id,
                event_id=event.id,
                target_entity_type="company",
                target_entity_id=company_id,
                notification_type=event_type,
                title="External AI processing updated",
                message="Your AI external-processing safety setting was updated.",
                priority="high" if new.get("external_ai_processing_allowed") else "normal",
                action_url="#/settings",
                metadata={"enabled": bool(new.get("external_ai_processing_allowed"))},
            )

    @classmethod
    def provider_status(
        cls,
        db: Session,
        *,
        company_id: UUID,
        current_user: User,
        require_admin: bool = True,
    ) -> AIProviderStatusRead:
        ensure_company_access(current_user, company_id)
        if require_admin:
            ensure_role(current_user, OWNER_ADMIN_ROLES)
        company = get_or_404(db, Company, company_id, label="Company")
        company_settings = cls.company_ai_settings(company)
        runtime = get_ai_provider_config()
        provider_mode = normalize_provider_mode(company_settings.get("default_provider_mode") or runtime.provider_mode)
        configured = provider_mode in {"mock", "disabled"} or (provider_mode == "groq" and runtime.groq_configured)
        model_name = runtime.groq_model if provider_mode == "groq" else ("mock-deterministic" if provider_mode == "mock" else None)
        external_enabled = runtime.external_processing_enabled
        external_allowed = bool(company_settings["external_ai_processing_allowed"])
        real_connected = (
            provider_mode == "groq"
            and runtime.groq_configured
            and external_enabled
            and external_allowed
            and bool(company_settings["ai_enabled"])
        )
        if provider_mode == "groq" and not runtime.groq_configured:
            message = "Groq is selected but not configured. Add GROQ_API_KEY locally; the key is never exposed by the API."
        elif provider_mode == "groq" and not external_allowed:
            message = "Groq is configured as the real provider, but company external AI processing is off."
        elif provider_mode == "groq" and not external_enabled:
            message = "Groq is configured, but global external AI processing is off."
        elif provider_mode == "mock":
            message = "Mock AI provider is active. Real external AI calls are not made."
        elif provider_mode == "disabled":
            message = "AI provider mode is disabled."
        else:
            message = "Future provider mode is reserved and not implemented yet."
        return AIProviderStatusRead(
            company_id=company_id,
            provider_key=cls.provider_key_for_mode(provider_mode),
            provider_mode=provider_mode,
            configured=configured,
            model_name=model_name,
            external_processing_enabled=external_enabled,
            external_processing_allowed=external_allowed,
            ai_enabled=bool(company_settings["ai_enabled"]),
            real_ai_connected=real_connected,
            supported_real_job_types=sorted(REAL_AI_JOB_TYPES),
            supported_mock_job_types=sorted(MOCK_AI_JOB_TYPES),
            message=message,
        )


ai_service = AIService()
