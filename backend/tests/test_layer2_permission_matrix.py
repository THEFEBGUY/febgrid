import unittest
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

from app.models.ai_job import AIJob
from app.models.project import Project
from app.services.ai_job_runner import AIJobRunner
from app.services.ai_service import AIService
from app.services.company_memory_service import CompanyMemoryService
from app.services.company_pulse_service import CompanyPulseService
from app.services.employee_digital_twin_service import EmployeeDigitalTwinService
from app.services.work_dna_service import WorkDNAService


class FakeDB:
    def __init__(self, *, records=None, scalar_values=None, execute_values=None) -> None:
        self.records = records or {}
        self.scalar_values = list(scalar_values or [])
        self.execute_values = list(execute_values or [])

    def get(self, model, value):
        return self.records.get((model, value))

    def scalar(self, _statement):
        if self.scalar_values:
            return self.scalar_values.pop(0)
        return None

    def execute(self, _statement):
        rows = self.execute_values.pop(0) if self.execute_values else []
        return SimpleNamespace(all=lambda: rows)


def user(role: str, company_id):
    return SimpleNamespace(id=uuid4(), company_id=company_id, role=role)


class Layer2PermissionMatrixTests(unittest.TestCase):
    def assert_http_status(self, expected_status: int, func, *args, **kwargs) -> None:
        with self.assertRaises(HTTPException) as raised:
            func(*args, **kwargs)
        self.assertEqual(raised.exception.status_code, expected_status)

    def test_company_pulse_owner_allowed_and_non_admin_blocked(self) -> None:
        company_id = uuid4()
        CompanyPulseService.ensure_owner_admin_company_access(user("company_owner", company_id), company_id)
        CompanyPulseService.ensure_owner_admin_company_access(user("admin", company_id), company_id)

        self.assert_http_status(
            403,
            CompanyPulseService.ensure_owner_admin_company_access,
            user("manager", company_id),
            company_id,
        )
        self.assert_http_status(
            403,
            CompanyPulseService.ensure_owner_admin_company_access,
            user("employee", company_id),
            company_id,
        )
        self.assert_http_status(
            404,
            CompanyPulseService.ensure_owner_admin_company_access,
            user("company_owner", uuid4()),
            company_id,
        )

    def test_work_dna_company_scope_blocks_manager_and_employee(self) -> None:
        company_id = uuid4()
        linked_employee = SimpleNamespace(id=uuid4(), company_id=company_id, is_active=True)

        self.assert_http_status(
            403,
            WorkDNAService.ensure_scope_access,
            FakeDB(scalar_values=[linked_employee]),
            company_id=company_id,
            scope_type="company",
            scope_id=None,
            current_user=user("manager", company_id),
        )
        self.assert_http_status(
            403,
            WorkDNAService.ensure_scope_access,
            FakeDB(scalar_values=[linked_employee]),
            company_id=company_id,
            scope_type="company",
            scope_id=None,
            current_user=user("employee", company_id),
        )

    def test_work_dna_project_scope_allows_member_manager_and_blocks_unrelated_manager(self) -> None:
        company_id = uuid4()
        project_id = uuid4()
        manager = user("manager", company_id)
        manager_employee = SimpleNamespace(id=uuid4(), company_id=company_id, is_active=True)
        project = SimpleNamespace(
            id=project_id,
            company_id=company_id,
            is_active=True,
            name="Allowed Project",
            owner_user_id=None,
            owner_employee_id=None,
        )
        db = FakeDB(
            records={(Project, project_id): project},
            scalar_values=[manager_employee, SimpleNamespace(id=uuid4())],
        )

        scope = WorkDNAService.ensure_scope_access(
            db,
            company_id=company_id,
            scope_type="project",
            scope_id=project_id,
            current_user=manager,
        )

        self.assertEqual(scope["scope_type"], "project")
        self.assertEqual(scope["scope_id"], project_id)

        self.assert_http_status(
            403,
            WorkDNAService.ensure_scope_access,
            FakeDB(records={(Project, project_id): project}, scalar_values=[manager_employee, None]),
            company_id=company_id,
            scope_type="project",
            scope_id=project_id,
            current_user=manager,
        )

    def test_employee_digital_twin_employee_own_allowed_and_other_blocked(self) -> None:
        company_id = uuid4()
        employee_user = user("employee", company_id)
        own_employee = SimpleNamespace(id=uuid4(), company_id=company_id, user_id=employee_user.id, manager_id=None)
        other_employee = SimpleNamespace(id=uuid4(), company_id=company_id, user_id=uuid4(), manager_id=None)

        EmployeeDigitalTwinService.ensure_visible(FakeDB(scalar_values=[own_employee]), current_user=employee_user, employee=own_employee)
        self.assert_http_status(
            404,
            EmployeeDigitalTwinService.ensure_visible,
            FakeDB(scalar_values=[own_employee]),
            current_user=employee_user,
            employee=other_employee,
        )

    def test_employee_digital_twin_manager_direct_report_allowed_unrelated_blocked(self) -> None:
        company_id = uuid4()
        manager_user = user("manager", company_id)
        manager_employee = SimpleNamespace(id=uuid4(), company_id=company_id, user_id=manager_user.id)
        report = SimpleNamespace(id=uuid4(), company_id=company_id, user_id=uuid4(), manager_id=manager_employee.id)
        unrelated = SimpleNamespace(id=uuid4(), company_id=company_id, user_id=uuid4(), manager_id=uuid4())

        EmployeeDigitalTwinService.ensure_visible(FakeDB(scalar_values=[manager_employee]), current_user=manager_user, employee=report)
        self.assert_http_status(
            403,
            EmployeeDigitalTwinService.ensure_visible,
            FakeDB(scalar_values=[manager_employee], execute_values=[[], []]),
            current_user=manager_user,
            employee=unrelated,
        )

    def test_provider_settings_and_queue_controls_are_owner_admin_only(self) -> None:
        company_id = uuid4()

        self.assert_http_status(
            403,
            AIService.provider_status,
            FakeDB(),
            company_id=company_id,
            current_user=user("employee", company_id),
        )
        self.assert_http_status(
            403,
            AIJobRunner().process_next,
            FakeDB(),
            company_id=company_id,
            current_user=user("manager", company_id),
        )

    def test_employee_raw_ai_job_visibility_is_own_job_only_and_company_jobs_blocked(self) -> None:
        company_id = uuid4()
        employee_user = user("employee", company_id)
        own_job = SimpleNamespace(id=uuid4(), company_id=company_id, job_type="work_object_summary_safe", requested_by_user_id=employee_user.id, input_entity_type="work_object")
        other_job = SimpleNamespace(id=uuid4(), company_id=company_id, job_type="work_object_summary_safe", requested_by_user_id=uuid4(), input_entity_type="work_object")
        company_job = SimpleNamespace(id=uuid4(), company_id=company_id, job_type="company_brief_safe", requested_by_user_id=employee_user.id, input_entity_type="company")

        self.assertIs(AIService.get_visible_job(FakeDB(records={(AIJob, own_job.id): own_job}), job_id=own_job.id, company_id=company_id, current_user=employee_user), own_job)
        self.assert_http_status(
            404,
            AIService.get_visible_job,
            FakeDB(records={(AIJob, other_job.id): other_job}),
            job_id=other_job.id,
            company_id=company_id,
            current_user=employee_user,
        )
        self.assert_http_status(403, AIService.ensure_manage_job, employee_user, company_job)

    def test_memory_review_blocks_employee(self) -> None:
        self.assert_http_status(
            403,
            CompanyMemoryService.approve_memory,
            FakeDB(),
            memory_id=uuid4(),
            company_id=uuid4(),
            current_user=user("employee", uuid4()),
        )


if __name__ == "__main__":
    unittest.main()
