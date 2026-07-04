import os
import socket
from datetime import timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.api.utils import get_or_404
from app.core.ai_config import REAL_AI_PROVIDER_MODES, get_ai_provider_config
from app.core.permissions import OWNER_ADMIN_ROLES, ensure_company_access, ensure_role
from app.models.ai_job import AIJob
from app.models.common import utc_now
from app.models.company import Company
from app.models.user import User
from app.schemas.ai_job import REAL_AI_JOB_TYPES, AIJobQueueSummaryRead
from app.services.ai_providers import AIProviderError, AIProviderRequest, build_ai_provider

RETRYABLE_ERROR_CODES = {
    "provider_timeout",
    "provider_rate_limited",
    "provider_unavailable",
    "provider_unknown_error",
    "temporary_network_error",
}
TERMINAL_STATUSES = {"succeeded", "failed", "cancelled", "skipped"}
DEFAULT_STALE_LOCK_MINUTES = 10


def runner_identity() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def is_retryable_error(error_code: str) -> bool:
    return error_code in RETRYABLE_ERROR_CODES


def next_retry_time(attempts: int):
    delay = timedelta(minutes=1 if attempts <= 1 else 5)
    return utc_now() + delay


class AIJobRunner:
    def __init__(self, *, locked_by: str | None = None, stale_after_minutes: int = DEFAULT_STALE_LOCK_MINUTES) -> None:
        self.locked_by = locked_by or runner_identity()
        self.stale_after = timedelta(minutes=max(1, stale_after_minutes))

    def queue_summary(self, db: Session, *, company_id: UUID) -> AIJobQueueSummaryRead:
        now = utc_now()
        stale_before = now - self.stale_after
        counts = dict(
            db.execute(
                select(AIJob.status, func.count(AIJob.id))
                .where(AIJob.company_id == company_id)
                .group_by(AIJob.status)
            ).all()
        )
        retryable_failed = db.scalar(
            select(func.count(AIJob.id)).where(
                AIJob.company_id == company_id,
                AIJob.status == "failed",
                AIJob.retryable.is_(True),
                AIJob.attempts < AIJob.max_attempts,
            )
        )
        stale_running = db.scalar(
            select(func.count(AIJob.id)).where(
                AIJob.company_id == company_id,
                AIJob.status == "running",
                or_(AIJob.locked_at <= stale_before, AIJob.started_at <= stale_before),
            )
        )
        return AIJobQueueSummaryRead(
            company_id=company_id,
            queued=int(counts.get("queued", 0)),
            running=int(counts.get("running", 0)),
            succeeded=int(counts.get("succeeded", 0)),
            failed=int(counts.get("failed", 0)),
            cancelled=int(counts.get("cancelled", 0)),
            skipped=int(counts.get("skipped", 0)),
            retryable_failed=int(retryable_failed or 0),
            stale_running=int(stale_running or 0),
        )

    def fetch_next_queued_job(self, db: Session, *, company_id: UUID) -> AIJob | None:
        now = utc_now()
        priority_order = case(
            (AIJob.priority == "urgent", 0),
            (AIJob.priority == "high", 1),
            (AIJob.priority == "normal", 2),
            (AIJob.priority == "low", 3),
            else_=4,
        )
        statement = (
            select(AIJob)
            .where(
                AIJob.company_id == company_id,
                AIJob.status == "queued",
                AIJob.attempts < AIJob.max_attempts,
                or_(AIJob.scheduled_at.is_(None), AIJob.scheduled_at <= now),
                or_(AIJob.next_attempt_at.is_(None), AIJob.next_attempt_at <= now),
            )
            .order_by(priority_order, AIJob.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        return db.scalar(statement)

    def process_next(self, db: Session, *, company_id: UUID, current_user: User) -> AIJob | None:
        ensure_company_access(current_user, company_id)
        ensure_role(current_user, OWNER_ADMIN_ROLES)
        job = self.fetch_next_queued_job(db, company_id=company_id)
        if job is None:
            return None
        return self.run_job(db, job=job, current_user=current_user, run_mode="queued")

    def run_job(self, db: Session, *, job: AIJob, current_user: User, run_mode: str = "manual") -> AIJob:
        from app.services.ai_service import AIService

        AIService.ensure_manage_job(current_user, job)
        if job.status in TERMINAL_STATUSES:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Terminal AI jobs cannot be run")
        if job.status == "running":
            if not self.is_stale(job):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="AI job is already running")
            self.recover_one_stale_job(db, job=job, current_user=current_user)
        if job.status != "queued":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only queued AI jobs can be run")
        if job.attempts >= job.max_attempts:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="AI job has reached its attempt limit")
        if job.next_attempt_at is not None and job.next_attempt_at > utc_now():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="AI job is waiting for its next retry window")

        self.lock_job(db, job=job, current_user=current_user, run_mode=run_mode)
        try:
            self.execute_locked_job(db, job=job, current_user=current_user)
        except AIProviderError as exc:
            self.handle_failure(db, job=job, current_user=current_user, error_code=exc.code, error_message=exc.safe_message, metadata=exc.metadata)
        except Exception:
            self.handle_failure(
                db,
                job=job,
                current_user=current_user,
                error_code="provider_unknown_error",
                error_message="AI job failed safely.",
                metadata={},
            )
        return job

    def lock_job(self, db: Session, *, job: AIJob, current_user: User, run_mode: str) -> None:
        from app.services.ai_service import AIService

        now = utc_now()
        runtime = get_ai_provider_config()
        company = get_or_404(db, Company, job.company_id, label="Company")
        company_settings = AIService.company_ai_settings(company)
        provider_mode = AIService.resolved_provider_mode(job.job_type, company_settings)

        job.status = "running"
        job.locked_at = now
        job.locked_by = self.locked_by
        job.started_at = now
        job.last_attempt_at = now
        job.next_attempt_at = None
        job.attempts += 1
        job.provider_key = AIService.provider_key_for_mode(provider_mode)
        job.provider_mode = provider_mode
        job.timeout_seconds = max(1, min(int(getattr(runtime, "groq_timeout_seconds", 30)), 120))
        job.run_mode = run_mode
        job.retryable = False
        job.error_code = None
        job.error_message = None
        job.metadata_json = AIService.merged_job_metadata(
            job,
            {
                "safety_status": "running",
                "locked_by": self.locked_by,
                "run_mode": run_mode,
            },
        )
        db.flush()
        AIService.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.locked",
            title=f"AI job locked: {job.job_type}",
            description="A queued AI job was locked for one safe runner.",
        )
        AIService.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.started",
            title=f"AI job started: {job.job_type}",
            description="A tenant-safe AI foundation job started.",
        )

    def execute_locked_job(self, db: Session, *, job: AIJob, current_user: User) -> None:
        from app.services.ai_service import AIService

        runtime = get_ai_provider_config()
        company = get_or_404(db, Company, job.company_id, label="Company")
        company_settings = AIService.company_ai_settings(company)
        provider_mode = AIService.resolved_provider_mode(job.job_type, company_settings)

        if not company_settings["ai_enabled"]:
            raise AIProviderError("ai_disabled", "AI is disabled for this company.")
        if job.job_type not in company_settings["allowed_ai_job_types"]:
            raise AIProviderError("job_type_not_allowed", "AI job type is not allowed for this company.")
        if provider_mode in REAL_AI_PROVIDER_MODES:
            if job.job_type not in REAL_AI_JOB_TYPES:
                raise AIProviderError("job_type_not_allowed", "Real provider execution is limited to safe text-only job types.")
            if not runtime.external_processing_enabled or not company_settings["external_ai_processing_allowed"]:
                raise AIProviderError("external_processing_disabled", "External AI processing is disabled for this company.")

        entity_context = AIService.build_safe_context(db, job)
        messages = AIService.build_messages(job, entity_context, runtime.groq_max_input_chars)
        provider = build_ai_provider(provider_mode, runtime)
        result = provider.generate(
            AIProviderRequest(
                job_type=job.job_type,
                input_entity_type=job.input_entity_type,
                input_entity_id=str(job.input_entity_id) if job.input_entity_id else None,
                input_payload=job.input_payload if isinstance(job.input_payload, dict) else {},
                entity_context=entity_context,
                messages=messages,
                max_input_chars=runtime.groq_max_input_chars,
            )
        )
        output_payload = dict(job.output_payload) if isinstance(job.output_payload, dict) else {}
        output_payload.update(result.output_payload if isinstance(result.output_payload, dict) else {})
        output_payload.setdefault("provider_key", result.provider_key)
        output_payload.setdefault("provider_mode", result.provider_mode)
        output_payload.setdefault("model_name", result.model_name)
        output_payload.setdefault("generated_at", utc_now().isoformat())
        output_payload.setdefault("is_mock", not result.external_processing_used)
        job.output_payload = output_payload
        job.provider_key = result.provider_key
        job.provider_mode = result.provider_mode
        job.status = "succeeded"
        job.completed_at = utc_now()
        job.failed_at = None
        job.error_code = None
        job.error_message = None
        job.retryable = False
        self.clear_lock(job)
        job.metadata_json = AIService.merged_job_metadata(
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
                "provider_metadata": result.metadata if isinstance(result.metadata, dict) else {},
                "retryable": False,
            },
        )
        db.flush()
        succeeded_event = AIService.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.succeeded",
            title=f"AI job succeeded: {job.job_type}",
            description="A tenant-safe AI foundation job completed successfully.",
        )
        AIService.notify_requester(db, job=job, event_id=succeeded_event.id, success=True)

    def handle_failure(
        self,
        db: Session,
        *,
        job: AIJob,
        current_user: User,
        error_code: str,
        error_message: str,
        metadata: dict,
    ) -> None:
        from app.services.ai_service import AIService

        retryable = is_retryable_error(error_code)
        job.error_code = error_code
        job.retryable = retryable
        if retryable and job.attempts < job.max_attempts:
            job.status = "queued"
            job.next_attempt_at = next_retry_time(job.attempts)
            job.error_message = error_message[:1000]
            self.clear_lock(job)
            job.metadata_json = AIService.merged_job_metadata(
                job,
                {
                    "error_code": error_code,
                    "error_message": error_message[:500],
                    "retryable": True,
                    "next_attempt_at": job.next_attempt_at.isoformat() if job.next_attempt_at else None,
                    "safety_status": "retry_scheduled",
                    "provider_metadata": metadata if isinstance(metadata, dict) else {},
                },
            )
            db.flush()
            AIService.record_job_event(
                db,
                job=job,
                current_user=current_user,
                event_type="ai_job.retry_scheduled",
                title=f"AI job retry scheduled: {job.job_type}",
                description=error_message[:500],
            )
            return

        AIService.fail_job(
            db,
            job=job,
            current_user=current_user,
            error_code=error_code,
            error_message=error_message,
            metadata=metadata,
        )

    def retry_failed_job(self, db: Session, *, job: AIJob, current_user: User) -> AIJob:
        from app.services.ai_service import AIService

        AIService.ensure_manage_job(current_user, job)
        if job.status != "failed" or not job.retryable:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only failed retryable AI jobs can be retried")
        if job.attempts >= job.max_attempts:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="AI job has reached its attempt limit")
        job.status = "queued"
        job.failed_at = None
        job.next_attempt_at = utc_now()
        job.error_message = None
        self.clear_lock(job)
        job.metadata_json = AIService.merged_job_metadata(job, {"safety_status": "retried", "retryable": True})
        db.flush()
        AIService.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.retried",
            title=f"AI job retried: {job.job_type}",
            description="A failed retryable AI job was moved back to the queue.",
        )
        return job

    def cancel_job(self, db: Session, *, job: AIJob, current_user: User, reason: str | None = None) -> AIJob:
        from app.services.ai_service import AIService

        AIService.ensure_manage_job(current_user, job)
        if job.status in TERMINAL_STATUSES:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Terminal AI jobs cannot be cancelled")
        job.status = "cancelled"
        job.cancelled_at = utc_now()
        job.cancelled_by_user_id = current_user.id
        job.cancellation_reason = (reason or "Cancelled by user")[:1000]
        job.error_code = "cancelled"
        job.retryable = False
        self.clear_lock(job)
        job.metadata_json = AIService.merged_job_metadata(
            job,
            {"safety_status": "cancelled", "external_processing_used": False, "cancellation_reason": job.cancellation_reason},
        )
        db.flush()
        event = AIService.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.cancelled",
            title=f"AI job cancelled: {job.job_type}",
            description="A tenant-safe AI foundation job was cancelled.",
        )
        AIService.notify_requester(db, job=job, event_id=event.id, success=False, cancelled=True)
        return job

    def recover_stale_jobs(self, db: Session, *, company_id: UUID, current_user: User) -> int:
        ensure_company_access(current_user, company_id)
        ensure_role(current_user, OWNER_ADMIN_ROLES)
        stale_before = utc_now() - self.stale_after
        jobs = list(
            db.scalars(
                select(AIJob)
                .where(
                    AIJob.company_id == company_id,
                    AIJob.status == "running",
                    or_(AIJob.locked_at <= stale_before, AIJob.started_at <= stale_before),
                )
                .with_for_update(skip_locked=True)
            ).all()
        )
        for job in jobs:
            self.recover_one_stale_job(db, job=job, current_user=current_user)
        return len(jobs)

    def recover_one_stale_job(self, db: Session, *, job: AIJob, current_user: User) -> None:
        from app.services.ai_service import AIService

        if job.status != "running" or not self.is_stale(job):
            return
        retryable = job.attempts < job.max_attempts
        if retryable:
            job.status = "queued"
            job.next_attempt_at = utc_now()
            job.retryable = True
            job.error_code = "stale_lock_recovered"
            job.error_message = "AI job was recovered from a stale runner lock."
            safety_status = "stale_recovered_to_queue"
        else:
            job.status = "failed"
            job.failed_at = utc_now()
            job.retryable = False
            job.error_code = "stale_lock_failed"
            job.error_message = "AI job failed after stale runner recovery."
            safety_status = "stale_recovered_failed"
        self.clear_lock(job)
        job.metadata_json = AIService.merged_job_metadata(
            job,
            {
                "error_code": job.error_code,
                "error_message": job.error_message,
                "retryable": job.retryable,
                "safety_status": safety_status,
            },
        )
        db.flush()
        event = AIService.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.recovered_stale",
            title=f"AI job recovered: {job.job_type}",
            description=job.error_message or "AI job recovered from a stale lock.",
        )
        if job.status == "failed":
            AIService.notify_requester(db, job=job, event_id=event.id, success=False)

    def is_stale(self, job: AIJob) -> bool:
        threshold = utc_now() - self.stale_after
        return bool((job.locked_at and job.locked_at <= threshold) or (job.started_at and job.started_at <= threshold))

    @staticmethod
    def clear_lock(job: AIJob) -> None:
        job.locked_at = None
        job.locked_by = None
