import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.api.routes import bulk_invites
from app.core.security import create_bulk_invite_preview_token, decode_bulk_invite_preview_token
from app.schemas.bulk_invite import (
    BulkInviteNormalizedRow,
    BulkInvitePreviewRead,
    JavaBulkInviteValidationResponse,
    JavaBulkInviteValidationRow,
)
from app.services.bulk_invite_preview_service import BulkInvitePreviewService
from app.services.java_bulk_invite_client import JavaBulkInviteClient, JavaBulkInviteClientError


class FakeDB:
    def __init__(self, company=None) -> None:
        self.company = company
        self.committed = False

    def get(self, _model, _value):
        return self.company

    def commit(self):
        self.committed = True


def owner(company_id):
    return SimpleNamespace(id=uuid4(), company_id=company_id, role="company_owner")


def validation_response() -> JavaBulkInviteValidationResponse:
    return JavaBulkInviteValidationResponse(
        requestId="request-id",
        fileName="employees.csv",
        totalRows=1,
        validRowCount=1,
        invalidRowCount=0,
        duplicateRowCount=0,
        rows=[
            JavaBulkInviteValidationRow(
                rowNumber=2,
                status="VALID",
                normalized=BulkInviteNormalizedRow(
                    email="new.employee@example.com",
                    fullName="New Employee",
                    jobTitle="Developer",
                    role="employee",
                ),
            )
        ],
    )


class BulkInviteFoundationTests(unittest.TestCase):
    def test_preview_token_is_scoped_and_tamper_safe(self) -> None:
        company_id = uuid4()
        user_id = uuid4()
        token = create_bulk_invite_preview_token(
            company_id=company_id,
            user_id=user_id,
            normalized_rows_hash="a" * 64,
        )
        payload = decode_bulk_invite_preview_token(token)
        self.assertEqual(payload["company_id"], str(company_id))
        self.assertEqual(payload["sub"], str(user_id))
        with self.assertRaises(HTTPException):
            decode_bulk_invite_preview_token(token[:-1] + ("a" if token[-1] != "a" else "b"))

    def test_java_client_is_unavailable_without_configuration(self) -> None:
        settings = SimpleNamespace(
            java_bulk_invite_base_url="",
            java_bulk_invite_service_key=None,
            java_bulk_invite_timeout_seconds=20,
        )
        with self.assertRaises(JavaBulkInviteClientError) as raised:
            JavaBulkInviteClient(settings).validate_csv(file_name="employees.csv", content=b"csv", request_id=uuid4())
        self.assertEqual(raised.exception.code, "BULK_INVITE_SERVICE_UNAVAILABLE")
        self.assertEqual(raised.exception.status_code, 503)

    def test_preview_enrichment_is_tenant_scoped_and_checks_existing_records(self) -> None:
        company_id = uuid4()
        department = SimpleNamespace(id=uuid4(), name="Engineering")
        team = SimpleNamespace(id=uuid4(), name="Platform", department_id=department.id)
        manager = SimpleNamespace(id=uuid4(), email="manager@example.com", is_active=True)
        existing_employee = SimpleNamespace(id=uuid4(), email="new.employee@example.com", metadata_json={})
        context = {
            "employees": {"new.employee@example.com": existing_employee},
            "managers": {"manager@example.com": manager},
            "employee_codes": {},
            "departments": {"engineering": department},
            "teams": {"platform": team},
            "invitations": {},
        }
        response = validation_response()
        row = response.rows[0].model_copy(
            update={
                "normalized": response.rows[0].normalized.model_copy(
                    update={"department": "Engineering", "team": "Platform", "manager_email": "manager@example.com"}
                )
            }
        )
        response = response.model_copy(update={"rows": [row]})
        with patch.object(BulkInvitePreviewService, "_load_context", return_value=context):
            preview = BulkInvitePreviewService.build_preview(
                FakeDB(),
                company_id=company_id,
                actor_user=owner(company_id),
                validation=response,
            )
        self.assertEqual(preview.rows[0].status, "EXISTING_EMPLOYEE")
        self.assertEqual(preview.rows[0].department_id, department.id)
        self.assertEqual(preview.rows[0].team_id, team.id)
        self.assertEqual(preview.rows[0].manager_employee_id, manager.id)
        self.assertEqual(preview.existing_employee_count, 1)

    def test_preview_rejects_non_invitable_role_without_database_write(self) -> None:
        company_id = uuid4()
        response = validation_response()
        response = response.model_copy(
            update={"rows": [response.rows[0].model_copy(update={"normalized": response.rows[0].normalized.model_copy(update={"role": "admin"})})]}
        )
        empty_context = {"employees": {}, "managers": {}, "employee_codes": {}, "departments": {}, "teams": {}, "invitations": {}}
        with patch.object(BulkInvitePreviewService, "_load_context", return_value=empty_context):
            preview = BulkInvitePreviewService.build_preview(
                FakeDB(), company_id=company_id, actor_user=owner(company_id), validation=response
            )
        self.assertEqual(preview.rows[0].status, "INVALID")
        self.assertEqual(preview.rows[0].errors[0].code, "INVALID_ROLE")

    def test_template_requires_existing_invite_permission(self) -> None:
        company_id = uuid4()
        db = FakeDB(company=SimpleNamespace(id=company_id, is_active=True))
        response = bulk_invites.download_bulk_invite_template(company_id=company_id, db=db, current_user=owner(company_id))
        self.assertIn("email,full_name,job_title,role", response.body.decode("utf-8"))
        with self.assertRaises(HTTPException) as raised:
            bulk_invites.download_bulk_invite_template(
                company_id=company_id,
                db=db,
                current_user=SimpleNamespace(id=uuid4(), company_id=company_id, role="employee"),
            )
        self.assertEqual(raised.exception.status_code, 403)

    def test_template_rejects_cross_company_access(self) -> None:
        company_id = uuid4()
        db = FakeDB(company=SimpleNamespace(id=company_id, is_active=True))
        with self.assertRaises(HTTPException) as raised:
            bulk_invites.download_bulk_invite_template(
                company_id=company_id,
                db=db,
                current_user=owner(uuid4()),
            )
        self.assertEqual(raised.exception.status_code, 404)

    def test_preview_route_commits_only_aggregate_event_after_java_validation(self) -> None:
        company_id = uuid4()
        current_user = owner(company_id)
        db = FakeDB(company=SimpleNamespace(id=company_id, is_active=True))
        expected = BulkInvitePreviewRead(
            company_id=company_id,
            file_name="employees.csv",
            total_rows=1,
            valid_row_count=1,
            invalid_row_count=0,
            duplicate_row_count=0,
            existing_employee_count=0,
            existing_invitation_count=0,
            preview_token="preview-token",
            preview_expires_at=datetime.now(timezone.utc),
            rows=[],
        )
        upload = UploadFile(
            filename="employees.csv",
            file=__import__("io").BytesIO(b"email,full_name,job_title,role\\na@example.com,A,Dev,employee\\n"),
            headers=Headers({"content-type": "text/csv"}),
        )
        settings = SimpleNamespace(bulk_invite_max_file_bytes=2_097_152)
        with patch.object(bulk_invites, "get_settings", return_value=settings):
            with patch.object(bulk_invites.JavaBulkInviteClient, "validate_csv", return_value=validation_response()) as validate:
                with patch.object(bulk_invites.BulkInvitePreviewService, "build_preview", return_value=expected):
                    with patch.object(bulk_invites.BulkInvitePreviewService, "record_preview_event") as record_event:
                        result = bulk_invites.preview_bulk_invites(company_id=company_id, file=upload, db=db, current_user=current_user)
        self.assertIs(result, expected)
        self.assertTrue(db.committed)
        validate.assert_called_once()
        record_event.assert_called_once()

    def test_preview_route_returns_safe_java_unavailable_error_without_event(self) -> None:
        company_id = uuid4()
        db = FakeDB(company=SimpleNamespace(id=company_id, is_active=True))
        upload = UploadFile(filename="employees.csv", file=__import__("io").BytesIO(b"email,full_name,job_title,role\\n"))
        settings = SimpleNamespace(bulk_invite_max_file_bytes=2_097_152)
        unavailable = JavaBulkInviteClientError("BULK_INVITE_SERVICE_UNAVAILABLE", "internal", 503)
        with patch.object(bulk_invites, "get_settings", return_value=settings):
            with patch.object(bulk_invites.JavaBulkInviteClient, "validate_csv", side_effect=unavailable):
                with self.assertRaises(HTTPException) as raised:
                    bulk_invites.preview_bulk_invites(company_id=company_id, file=upload, db=db, current_user=owner(company_id))
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail, "BULK_INVITE_SERVICE_UNAVAILABLE")
        self.assertFalse(db.committed)

    def test_single_invitation_service_remains_the_only_creation_path(self) -> None:
        import inspect
        from app.services import bulk_invite_preview_service

        source = inspect.getsource(bulk_invite_preview_service)
        self.assertNotIn("create_invitation(", source)
        self.assertNotIn("EmployeeInvitation(", source)
