import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException

from app.services.invitation_service import InvitationService
from app.services.supabase_auth_service import SupabaseAuthService


class DeploymentInvitationFoundationTests(unittest.TestCase):
    def test_acceptance_url_uses_local_default_and_public_app_url(self) -> None:
        token = "token-for-deployment-test"
        with patch("app.services.invitation_service.get_settings", return_value=SimpleNamespace(public_app_url="http://localhost:5173")):
            self.assertEqual(InvitationService.acceptance_url(token), f"http://localhost:5173/accept-invite/{token}")
        with patch("app.services.invitation_service.get_settings", return_value=SimpleNamespace(public_app_url="https://febgrid-demo.vercel.app/")):
            self.assertEqual(InvitationService.acceptance_url(token), f"https://febgrid-demo.vercel.app/accept-invite/{token}")

    def test_supabase_identity_requires_id_and_exact_email_shape(self) -> None:
        identity = SupabaseAuthService._identity_from_payload({"id": "supabase-user-1", "email": "Invited@Example.com"})
        self.assertEqual(identity.user_id, "supabase-user-1")
        self.assertEqual(identity.email, "invited@example.com")

        for payload in ({}, {"id": "", "email": "user@example.com"}, {"id": "user", "email": "not-an-email"}):
            with self.assertRaises(HTTPException) as raised:
                SupabaseAuthService._identity_from_payload(payload)
            self.assertEqual(raised.exception.status_code, 401)

    def test_supabase_verifier_requires_server_configuration(self) -> None:
        settings = SimpleNamespace(supabase_url="", supabase_anon_key=None, supabase_auth_timeout_seconds=10)
        with patch("app.services.supabase_auth_service.get_settings", return_value=settings):
            with self.assertRaises(HTTPException) as raised:
                SupabaseAuthService.verify_access_token("a" * 40)
        self.assertEqual(raised.exception.status_code, 503)

    def test_supabase_verifier_never_accepts_a_missing_or_short_token(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            SupabaseAuthService.verify_access_token("")
        self.assertEqual(raised.exception.status_code, 401)

    def test_magic_link_acceptance_uses_only_the_verified_invited_email(self) -> None:
        company_id = uuid4()
        employee_id = uuid4()
        invitation = SimpleNamespace(
            id=uuid4(),
            company_id=company_id,
            employee_id=employee_id,
            invited_email="invited@example.com",
            normalized_email="invited@example.com",
            invited_role="employee",
            invite_source="invite",
            approval_required=False,
            status="pending",
            accepted_at=None,
        )
        employee = SimpleNamespace(
            id=employee_id,
            company_id=company_id,
            full_name="Invited Employee",
            user_id=None,
            email="invited@example.com",
            account_status="pending_activation",
            activation_status="invitation_sent",
            profile_completion_status="prefill_pending",
        )

        class FakeDB:
            def get(self, _model, value):
                return employee if value == employee_id else None

            def scalar(self, _statement):
                return None

            def add(self, _value):
                return None

            def flush(self):
                return None

        with patch.object(InvitationService, "_invitation_by_token", return_value=invitation), patch(
            "app.services.invitation_service.EventService.record_event"
        ):
            accepted_invitation, accepted_employee, user = InvitationService.accept_with_supabase(
                FakeDB(),
                token="t" * 40,
                verified_email="INVITED@example.com",
                supabase_user_id="supabase-user-id",
            )

        self.assertIs(accepted_invitation, invitation)
        self.assertIs(accepted_employee, employee)
        self.assertEqual(user.company_id, company_id)
        self.assertEqual(user.email, "invited@example.com")
        self.assertEqual(user.supabase_user_id, "supabase-user-id")
        self.assertEqual(invitation.status, "accepted")

        invitation.status = "pending"
        employee.user_id = None
        with patch.object(InvitationService, "_invitation_by_token", return_value=invitation):
            with self.assertRaises(HTTPException) as raised:
                InvitationService.accept_with_supabase(
                    FakeDB(),
                    token="t" * 40,
                    verified_email="other@example.com",
                    supabase_user_id="another-user-id",
                )
        self.assertEqual(raised.exception.status_code, 403)
