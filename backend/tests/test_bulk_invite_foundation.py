import unittest
from contextlib import nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import httpx
from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers

from app.api.routes import bulk_invites
from app.core.security import create_bulk_invite_preview_token, decode_bulk_invite_preview_token
from app.schemas.bulk_invite import (
    BulkInviteConfirmRequest,
    BulkInviteNormalizedRow,
    BulkInvitePreviewRead,
    BulkInvitePreviewRow,
    JavaBulkInviteValidationResponse,
    JavaBulkInviteValidationRow,
)
from app.services.bulk_invite_confirmation_service import BulkInviteConfirmationService
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


class ConfirmationDB(FakeDB):
    def __init__(self) -> None:
        super().__init__()
        self.operation = None
        self.added = []

    def scalar(self, _statement):
        return self.operation

    def add(self, value):
        if getattr(value, "id", None) is None:
            value.id = uuid4()
        self.added.append(value)
        if value.__class__.__name__ == "BulkInviteOperation":
            self.operation = value

    def flush(self):
        return None

    def begin_nested(self):
        return nullcontext()


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


def preview_row() -> BulkInvitePreviewRow:
    return BulkInvitePreviewRow(
        row_number=2,
        status="VALID",
        normalized=BulkInviteNormalizedRow(
            email="new.employee@example.com",
            fullName="New Employee",
            jobTitle="Developer",
            role="employee",
        ),
    )


def confirmation_request(company_id, user_id, rows: list[BulkInvitePreviewRow]) -> BulkInviteConfirmRequest:
    return BulkInviteConfirmRequest(
        preview_token=create_bulk_invite_preview_token(
            company_id=company_id,
            user_id=user_id,
            normalized_rows_hash=BulkInvitePreviewService.normalized_rows_hash(rows),
        ),
        idempotency_key="bulk-confirmation-key-0001",
        file_name="employees.csv",
        approval_required=False,
        rows=rows,
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

    def test_java_client_timeout_returns_safe_unavailable_error(self) -> None:
        settings = SimpleNamespace(
            java_bulk_invite_base_url="http://validator.internal",
            java_bulk_invite_service_key=SimpleNamespace(get_secret_value=lambda: "test-only-key"),
            java_bulk_invite_timeout_seconds=20,
        )
        with patch("app.services.java_bulk_invite_client.httpx.Client") as client_class:
            client_class.return_value.__enter__.return_value.post.side_effect = httpx.TimeoutException("timeout")
            with self.assertRaises(JavaBulkInviteClientError) as raised:
                JavaBulkInviteClient(settings).validate_csv(
                    file_name="employees.csv", content=b"email,full_name,job_title,role\n", request_id=uuid4()
                )
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

        with self.assertRaises(HTTPException) as raised:
            bulk_invites.download_bulk_invite_template(
                company_id=company_id,
                db=db,
                current_user=SimpleNamespace(id=uuid4(), company_id=company_id, role="manager"),
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
        self.assertTrue(upload.file.closed)

    def test_single_invitation_service_remains_the_only_creation_path(self) -> None:
        import inspect
        from app.services import bulk_invite_preview_service

        source = inspect.getsource(bulk_invite_preview_service)
        self.assertNotIn("create_invitation(", source)
        self.assertNotIn("EmployeeInvitation(", source)

    def test_confirmation_uses_existing_invitation_service_and_replays_idempotently(self) -> None:
        company_id = uuid4()
        actor = owner(company_id)
        rows = [preview_row()]
        payload = confirmation_request(company_id, actor.id, rows)
        db = ConfirmationDB()
        context = {"employees": {}, "managers": {}, "employee_codes": {}, "departments": {}, "teams": {}, "invitations": {}}
        invitation = SimpleNamespace(id=uuid4(), employee_id=uuid4())
        with patch.object(BulkInvitePreviewService, "_load_context", return_value=context):
            with patch("app.services.bulk_invite_confirmation_service.InvitationService.create_invitation", return_value=(invitation, "/join/dev", {})) as create:
                with patch("app.services.bulk_invite_confirmation_service.EventService.record_event"):
                    result = BulkInviteConfirmationService.confirm(
                        db, company_id=company_id, actor_user=actor, payload=payload
                    )
        self.assertEqual(result.invited_rows, 1)
        self.assertEqual(result.rows[0].status, "INVITED")
        self.assertNotIn("acceptance_url", result.rows[0].model_dump())
        create.assert_called_once()
        self.assertIsNotNone(db.operation)
        self.assertEqual(db.operation.status, "completed")

        with patch("app.services.bulk_invite_confirmation_service.InvitationService.create_invitation") as create:
            replay = BulkInviteConfirmationService.confirm(db, company_id=company_id, actor_user=actor, payload=payload)
        self.assertTrue(replay.idempotent_replay)
        self.assertEqual(replay.invited_rows, 1)
        create.assert_not_called()

    def test_confirmation_rejects_preview_for_another_company_before_creation(self) -> None:
        company_id = uuid4()
        actor = owner(company_id)
        payload = confirmation_request(uuid4(), actor.id, [preview_row()])
        with self.assertRaises(HTTPException) as raised:
            BulkInviteConfirmationService.confirm(
                ConfirmationDB(), company_id=company_id, actor_user=actor, payload=payload
            )
        self.assertEqual(raised.exception.status_code, 409)

    def test_confirmation_keeps_valid_rows_when_another_row_fails_validation(self) -> None:
        company_id = uuid4()
        actor = owner(company_id)
        invalid = preview_row().model_copy(update={"row_number": 3, "status": "INVALID"})
        rows = [preview_row(), invalid]
        db = ConfirmationDB()
        context = {"employees": {}, "managers": {}, "employee_codes": {}, "departments": {}, "teams": {}, "invitations": {}}
        invitation = SimpleNamespace(id=uuid4(), employee_id=uuid4())
        with patch.object(BulkInvitePreviewService, "_load_context", return_value=context):
            with patch("app.services.bulk_invite_confirmation_service.InvitationService.create_invitation", return_value=(invitation, "/join/dev", {})):
                with patch("app.services.bulk_invite_confirmation_service.EventService.record_event"):
                    result = BulkInviteConfirmationService.confirm(
                        db,
                        company_id=company_id,
                        actor_user=actor,
                        payload=confirmation_request(company_id, actor.id, rows),
                    )
        self.assertEqual(result.status, "partially_failed")
        self.assertEqual(result.invited_rows, 1)
        self.assertEqual(result.failed_rows, 1)
        self.assertEqual([row.status for row in result.rows], ["INVITED", "FAILED_VALIDATION"])
