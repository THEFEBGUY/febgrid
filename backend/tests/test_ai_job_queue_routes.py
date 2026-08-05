import unittest
import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.routes.ai_jobs import router
from app.models.common import utc_now
from app.models.event import Event
from app.services.ai_job_runner import AIJobRunner
from app.services.ai_job_worker import AIJobWorker
from app.services.ai_providers import AIProviderError
from app.services.ai_service import AIService
from app.services.notification_service import NotificationService


def queued_job(*, next_attempt_at=None):
    return SimpleNamespace(
        id=uuid4(),
        company_id=uuid4(),
        requested_by_user_id=uuid4(),
        job_type="work_object_summary_safe",
        status="queued",
        attempts=1,
        max_attempts=3,
        next_attempt_at=next_attempt_at,
        metadata_json={},
    )


class StubRunner(AIJobRunner):
    def lock_job(self, db, *, job, current_user, run_mode):
        job.status = "running"

    def execute_locked_job(self, db, *, job, current_user):
        job.status = "succeeded"


class FailureRunner(AIJobRunner):
    def lock_job(self, db, *, job, current_user, run_mode):
        job.status = "running"
        job.attempts += 1

    def execute_locked_job(self, db, *, job, current_user):
        raise AIProviderError("provider_timeout", "The AI provider timed out safely.")


class AIJobQueueRouteTests(unittest.TestCase):
    def test_static_queue_routes_are_registered_before_dynamic_job_route(self) -> None:
        paths = [route.path for route in router.routes]
        self.assertIn("/ai/jobs/process-next", paths)
        self.assertIn("/ai/jobs/recover-stale", paths)
        self.assertLess(paths.index("/ai/jobs/process-next"), paths.index("/ai/jobs/{ai_job_id}"))

    def test_manual_run_can_override_retry_window(self) -> None:
        job = queued_job(next_attempt_at=utc_now() + timedelta(minutes=5))
        user = SimpleNamespace(id=job.requested_by_user_id, company_id=job.company_id, role="company_owner")
        with patch("app.services.ai_service.AIService.ensure_manage_job"):
            result = StubRunner().run_job(SimpleNamespace(), job=job, current_user=user, run_mode="manual")
        self.assertEqual(result.status, "succeeded")

    def test_automatic_run_respects_retry_window(self) -> None:
        job = queued_job(next_attempt_at=utc_now() + timedelta(minutes=5))
        user = SimpleNamespace(id=job.requested_by_user_id, company_id=job.company_id, role="company_owner")
        with patch("app.services.ai_service.AIService.ensure_manage_job"):
            with self.assertRaises(HTTPException) as raised:
                StubRunner().run_job(
                    SimpleNamespace(),
                    job=job,
                    current_user=user,
                    run_mode="system",
                    respect_schedule=True,
                )
        self.assertEqual(raised.exception.status_code, 409)
        self.assertIn("retry window", str(raised.exception.detail))

    def test_legacy_naive_retry_timestamp_is_compared_safely(self) -> None:
        job = queued_job(next_attempt_at=datetime.now().replace(tzinfo=None) + timedelta(minutes=5))
        user = SimpleNamespace(id=job.requested_by_user_id, company_id=job.company_id, role="company_owner")
        with patch("app.services.ai_service.AIService.ensure_manage_job"):
            with self.assertRaises(HTTPException) as raised:
                StubRunner().run_job(
                    SimpleNamespace(),
                    job=job,
                    current_user=user,
                    run_mode="system",
                    respect_schedule=True,
                )
        self.assertEqual(raised.exception.status_code, 409)

    def test_claim_query_uses_skip_locked(self) -> None:
        db = SimpleNamespace(scalar=lambda statement: setattr(db, "statement", statement) or None)
        AIJobRunner().fetch_next_queued_job(db)
        self.assertTrue(db.statement._for_update_arg.skip_locked)

    def test_stale_claim_query_uses_skip_locked(self) -> None:
        db = SimpleNamespace(scalar=lambda statement: setattr(db, "statement", statement) or None)
        AIJobRunner().fetch_one_stale_job(db)
        self.assertTrue(db.statement._for_update_arg.skip_locked)

    def test_empty_queue_is_a_safe_no_op(self) -> None:
        user = SimpleNamespace(id=uuid4(), company_id=uuid4(), role="company_owner")
        runner = AIJobRunner()
        with (
            patch("app.services.ai_job_runner.ensure_company_access"),
            patch("app.services.ai_job_runner.ensure_role"),
            patch.object(runner, "fetch_next_queued_job", return_value=None),
        ):
            self.assertIsNone(runner.process_next(SimpleNamespace(), company_id=user.company_id, current_user=user))

    def test_retryable_timeout_returns_job_to_queue_with_backoff(self) -> None:
        job = queued_job()
        job.metadata_json = {}
        user = SimpleNamespace(id=job.requested_by_user_id, company_id=job.company_id, role="company_owner")
        db = SimpleNamespace(flush=lambda: None)
        with (
            patch("app.services.ai_service.AIService.ensure_manage_job"),
            patch("app.services.ai_service.AIService.record_job_event"),
            patch("app.services.ai_service.AIService.record_summary_event"),
        ):
            result = FailureRunner().run_job(db, job=job, current_user=user, run_mode="system")
        self.assertEqual(result.status, "queued")
        self.assertTrue(result.retryable)
        self.assertEqual(result.error_code, "provider_timeout")
        self.assertIsNotNone(result.next_attempt_at)

    def test_active_summary_job_is_reused_for_same_source_version(self) -> None:
        company_id = uuid4()
        work_object_id = uuid4()
        source_updated_at = utc_now()
        active_job = SimpleNamespace(metadata_json={"source_version": source_updated_at.isoformat()})
        source = SimpleNamespace(id=work_object_id, updated_at=source_updated_at)
        scalar_results = iter([source])
        db = SimpleNamespace(
            scalar=lambda _statement: next(scalar_results),
            scalars=lambda _statement: SimpleNamespace(all=lambda: [active_job]),
            add=lambda _value: self.fail("A duplicate AI job should not be added"),
        )
        company = SimpleNamespace(id=company_id, settings_json={})
        user = SimpleNamespace(id=uuid4(), company_id=company_id, role="company_owner")
        with (
            patch("app.services.ai_service.ensure_company_access"),
            patch("app.services.ai_service.get_or_404", return_value=company),
            patch.object(AIService, "validate_entity_access"),
            patch.object(AIService, "ensure_summary_entity_permission"),
            patch.object(AIService, "company_ai_settings", return_value={"allowed_ai_job_types": ["work_object_summary_safe"]}),
        ):
            result = AIService.create_summary_job(
                db,
                company_id=company_id,
                job_type="work_object_summary_safe",
                input_entity_type="work_object",
                input_entity_id=work_object_id,
                current_user=user,
            )
        self.assertIs(result, active_job)


class AIJobWorkerLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_worker_stops_cleanly(self) -> None:
        with patch(
            "app.services.ai_job_worker.get_settings",
            return_value=SimpleNamespace(ai_job_worker_poll_seconds=0.25, ai_job_lease_seconds=600),
        ):
            worker = AIJobWorker()
        with patch.object(worker, "process_once", return_value=False):
            task = asyncio.create_task(worker.run())
            await asyncio.sleep(0)
            worker.stop()
            await asyncio.wait_for(task, timeout=1)
        self.assertTrue(task.done())


class AIJobNotificationPersistenceTests(unittest.TestCase):
    def test_new_event_is_flushed_before_notification_event_validation(self) -> None:
        company_id = uuid4()
        event = SimpleNamespace(id=uuid4(), company_id=company_id)
        db = SimpleNamespace(flush=Mock(), get=Mock(return_value=event), add=Mock())

        with (
            patch.object(NotificationService, "_validate_employee", return_value=None),
            patch.object(NotificationService, "_validate_user", return_value=SimpleNamespace(email="owner@example.test")),
            patch.object(NotificationService, "get_preferences", return_value={"in_app_enabled": True}),
            patch.object(NotificationService, "in_app_allowed", return_value=True),
            patch.object(NotificationService, "_existing_open_notification", return_value=None),
            patch("app.services.notification_service.EmailService.prepare_notification_delivery", return_value={}),
            patch("app.services.notification_service.EventService.record_event", return_value=event),
        ):
            notification = NotificationService.create_notification(
                db,
                company_id=company_id,
                recipient_user_id=uuid4(),
                event_id=event.id,
                target_entity_type="ai_job",
                target_entity_id=uuid4(),
                notification_type="ai_job.failed",
                title="AI job failed",
                message="The AI job failed safely.",
            )

        self.assertIsNotNone(notification)
        db.flush.assert_called_once()
        db.get.assert_any_call(Event, event.id)


if __name__ == "__main__":
    unittest.main()
