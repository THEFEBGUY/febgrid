import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.routes import dashboard
from app.api.routes import company_memory
from app.schemas.company_memory import (
    CompanyMemoryActionPayload,
    CompanyMemoryCreate,
    CompanyMemoryFromAIJobPayload,
    MEMORY_STATUSES,
    SOURCE_TYPES,
)
from app.services.company_memory_service import CompanyMemoryService


class DummyDB:
    def __init__(self, scalar_result=None) -> None:
        self.committed = False
        self.refreshed = None
        self.scalar_result = scalar_result
        self.added = None

    def commit(self) -> None:
        self.committed = True

    def refresh(self, value) -> None:
        self.refreshed = value

    def scalar(self, _statement):
        return self.scalar_result

    def add(self, value) -> None:
        self.added = value


class CompanyMemoryRouteTests(unittest.TestCase):
    def test_create_suggested_project_summary_commits_and_preserves_source(self) -> None:
        db = DummyDB()
        user = SimpleNamespace(id=uuid4(), company_id=uuid4(), role="company_owner")
        source_id = uuid4()
        payload = CompanyMemoryCreate(
            company_id=user.company_id,
            title="Project summary memory",
            memory_type="project_context",
            scope_type="project",
            scope_id=source_id,
            source_type="project_summary",
            source_id=source_id,
            content="Project summary content",
            status="suggested",
        )
        memory = SimpleNamespace(id=uuid4(), status="suggested", source_type="project_summary", source_id=source_id)

        with patch.object(company_memory.CompanyMemoryService, "create_memory", return_value=memory) as create_memory:
            result = company_memory.create_company_memory(payload, db=db, current_user=user)

        self.assertIs(result, memory)
        self.assertTrue(db.committed)
        self.assertIs(db.refreshed, memory)
        called_payload = create_memory.call_args.kwargs["payload"]
        self.assertEqual(called_payload.status, "suggested")
        self.assertEqual(called_payload.source_type, "project_summary")
        self.assertEqual(called_payload.source_id, source_id)

    def test_create_suggested_work_dna_commits_and_preserves_source(self) -> None:
        db = DummyDB()
        user = SimpleNamespace(id=uuid4(), company_id=uuid4(), role="company_owner")
        source_id = uuid4()
        payload = CompanyMemoryCreate(
            company_id=user.company_id,
            title="Work DNA insight",
            memory_type="process",
            scope_type="company",
            source_type="work_dna",
            source_id=source_id,
            content="Work DNA content",
            status="suggested",
        )
        memory = SimpleNamespace(id=uuid4(), status="suggested", source_type="work_dna", source_id=source_id)

        with patch.object(company_memory.CompanyMemoryService, "create_memory", return_value=memory):
            result = company_memory.create_company_memory(payload, db=db, current_user=user)

        self.assertIn("work_dna", SOURCE_TYPES)
        self.assertIs(result, memory)
        self.assertTrue(db.committed)
        self.assertIs(db.refreshed, memory)
        self.assertEqual(result.source_type, "work_dna")
        self.assertEqual(result.source_id, source_id)

    def test_create_from_ai_job_commits_project_summary_suggestion(self) -> None:
        db = DummyDB()
        user = SimpleNamespace(id=uuid4(), company_id=uuid4(), role="company_owner")
        payload = CompanyMemoryFromAIJobPayload(company_id=user.company_id, memory_type="project_context")
        memory = SimpleNamespace(id=uuid4(), status="suggested", source_type="project_summary")

        with patch.object(company_memory.CompanyMemoryService, "create_from_ai_job", return_value=memory):
            result = company_memory.create_company_memory_from_ai_job(uuid4(), payload, db=db, current_user=user)

        self.assertIs(result, memory)
        self.assertTrue(db.committed)
        self.assertIs(db.refreshed, memory)

    def test_list_endpoint_uses_suggested_status_filter(self) -> None:
        db = DummyDB()
        user = SimpleNamespace(id=uuid4(), company_id=uuid4(), role="company_owner")

        with patch.object(company_memory.CompanyMemoryService, "list_memories", return_value=[]) as list_memories:
            result = company_memory.list_company_memory(company_id=user.company_id, status="suggested", db=db, current_user=user)

        self.assertEqual(result, [])
        self.assertEqual(list_memories.call_args.kwargs["status_filter"], "suggested")

    def test_memory_status_contract_uses_suggested_not_pending(self) -> None:
        self.assertIn("suggested", MEMORY_STATUSES)
        self.assertNotIn("pending", MEMORY_STATUSES)

    def test_dashboard_summary_counts_suggested_entries_as_pending_suggestions(self) -> None:
        source = inspect.getsource(dashboard.get_dashboard_summary)

        self.assertIn('CompanyMemory.status == "suggested"', source)
        self.assertNotIn('CompanyMemory.status == "pending"', source)

    def test_ai_memory_source_types_are_supported(self) -> None:
        expected_sources = {
            "project_summary",
            "work_object_summary",
            "company_brief",
            "file_summary",
            "document_analysis",
            "image_analysis",
            "audio_transcription",
            "work_dna",
        }

        self.assertTrue(expected_sources.issubset(SOURCE_TYPES))

    def test_list_endpoint_propagates_cross_company_rejection_from_service(self) -> None:
        db = DummyDB()
        user = SimpleNamespace(id=uuid4(), company_id=uuid4(), role="company_owner")
        wrong_company_id = uuid4()
        rejection = HTTPException(status_code=404, detail="Company resource not found")

        with patch.object(company_memory.CompanyMemoryService, "list_memories", side_effect=rejection):
            with self.assertRaises(HTTPException) as raised:
                company_memory.list_company_memory(company_id=wrong_company_id, db=db, current_user=user)

        self.assertEqual(raised.exception.status_code, 404)

    def test_duplicate_suggested_source_returns_existing_memory(self) -> None:
        user = SimpleNamespace(id=uuid4(), company_id=uuid4(), role="company_owner")
        source_id = uuid4()
        existing = SimpleNamespace(
            id=uuid4(),
            company_id=user.company_id,
            status="suggested",
            source_type="work_dna",
            source_id=source_id,
            created_by_user_id=user.id,
        )
        db = DummyDB(scalar_result=existing)
        payload = CompanyMemoryCreate(
            company_id=user.company_id,
            title="Duplicate Work DNA insight",
            memory_type="operational_fact",
            scope_type="company",
            source_type="work_dna",
            source_id=source_id,
            content="Work DNA content",
            status="suggested",
        )

        with patch.object(CompanyMemoryService, "validate_scope_entity") as validate_scope:
            with patch.object(CompanyMemoryService, "validate_source") as validate_source:
                result = CompanyMemoryService.create_memory(db, payload=payload, current_user=user)

        self.assertIs(result, existing)
        self.assertIsNone(db.added)
        validate_scope.assert_called_once()
        validate_source.assert_called_once()

    def test_approve_reject_archive_commit(self) -> None:
        for route_func, payload in [
            (company_memory.approve_company_memory, CompanyMemoryActionPayload(company_id=uuid4())),
            (company_memory.reject_company_memory, CompanyMemoryActionPayload(company_id=uuid4(), note="No")),
            (company_memory.archive_company_memory, CompanyMemoryActionPayload(company_id=uuid4())),
        ]:
            db = DummyDB()
            user = SimpleNamespace(id=uuid4(), company_id=payload.company_id, role="company_owner")
            memory = SimpleNamespace(id=uuid4())
            service_method = {
                company_memory.approve_company_memory: "approve_memory",
                company_memory.reject_company_memory: "reject_memory",
                company_memory.archive_company_memory: "archive_memory",
            }[route_func]

            with patch.object(company_memory.CompanyMemoryService, service_method, return_value=memory):
                route_func(uuid4(), payload, db=db, current_user=user)

            self.assertTrue(db.committed)
            self.assertIs(db.refreshed, memory)


if __name__ == "__main__":
    unittest.main()
