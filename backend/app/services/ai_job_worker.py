import asyncio
import logging
from contextlib import suppress

from fastapi import HTTPException

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.ai_job import AIJob
from app.models.user import User
from app.services.ai_job_runner import AIJobRunner
from app.services.ai_service import AIService

logger = logging.getLogger(__name__)


class AIJobWorker:
    def __init__(self) -> None:
        settings = get_settings()
        self.poll_seconds = max(0.25, float(settings.ai_job_worker_poll_seconds))
        self.runner = AIJobRunner(stale_after_minutes=max(1, int(settings.ai_job_lease_seconds / 60)))
        self._stop = asyncio.Event()

    def process_once(self) -> bool:
        with SessionLocal() as db:
            stale_job = self.runner.fetch_one_stale_job(db)
            if stale_job is not None:
                requester = db.get(User, stale_job.requested_by_user_id) if stale_job.requested_by_user_id else None
                if requester is None or not requester.is_active:
                    AIService.fail_job(
                        db,
                        job=stale_job,
                        current_user=None,
                        error_code="requester_unavailable",
                        error_message="The stale AI job requester is no longer available.",
                        metadata={},
                    )
                else:
                    self.runner.recover_one_stale_job(db, job=stale_job, current_user=requester)
                db.commit()
                return True
            exhausted_job = self.runner.fetch_exhausted_queued_job(db)
            if exhausted_job is not None:
                requester = db.get(User, exhausted_job.requested_by_user_id) if exhausted_job.requested_by_user_id else None
                AIService.fail_job(
                    db,
                    job=exhausted_job,
                    current_user=requester,
                    error_code="attempt_limit_reached",
                    error_message="The AI job reached its maximum attempt limit.",
                    metadata={},
                )
                db.commit()
                return True
            job = self.runner.fetch_next_queued_job(db)
            if job is None:
                db.rollback()
                return False
            current_user = db.get(User, job.requested_by_user_id) if job.requested_by_user_id else None
            if current_user is None or not current_user.is_active:
                AIService.fail_job(
                    db,
                    job=job,
                    current_user=None,
                    error_code="requester_unavailable",
                    error_message="The AI job requester is no longer available.",
                    metadata={},
                )
                db.commit()
                return True
            try:
                self.runner.run_job(
                    db,
                    job=job,
                    current_user=current_user,
                    run_mode="system",
                    respect_schedule=True,
                )
                db.commit()
            except HTTPException as exc:
                db.rollback()
                job = db.get(AIJob, job.id)
                if job is not None and job.status == "queued":
                    AIService.fail_job(
                        db,
                        job=job,
                        current_user=current_user,
                        error_code="job_validation_error",
                        error_message=str(exc.detail)[:500],
                        metadata={},
                    )
                    db.commit()
            except Exception:
                db.rollback()
                job = db.get(AIJob, job.id)
                if job is not None and job.status in {"queued", "running"}:
                    AIService.fail_job(
                        db,
                        job=job,
                        current_user=current_user,
                        error_code="worker_internal_error",
                        error_message="The AI worker isolated a malformed job safely.",
                        metadata={},
                    )
                    db.commit()
                logger.exception(
                    "AI worker isolated an unexpected job failure for job_id=%s",
                    job.id if job is not None else "unknown",
                )
            return True

    async def run(self) -> None:
        logger.info("AI job worker started")
        while not self._stop.is_set():
            try:
                processed = await asyncio.to_thread(self.process_once)
            except Exception:
                # Keep the worker alive, but retain the original database traceback.
                # Without it a failed queue-claim query is impossible to diagnose.
                logger.exception("AI worker database cycle failed; retrying after the poll interval")
                processed = False
            if processed:
                await asyncio.sleep(0)
                continue
            with suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._stop.wait(), timeout=self.poll_seconds)
        logger.info("AI job worker stopped")

    def stop(self) -> None:
        self._stop.set()
