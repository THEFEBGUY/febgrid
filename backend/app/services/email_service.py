from typing import Any

from app.models.employee import Employee
from app.models.notification_preference import NotificationPreference
from app.models.user import User


class EmailService:
    """Phase 2 email-alert placeholder.

    Real SMTP/API provider delivery is intentionally not implemented yet. The
    notification system can still prepare delivery metadata so future email
    work has a stable shape without pretending a message was sent.
    """

    @staticmethod
    def recipient_email(user: User | None, employee: Employee | None) -> str | None:
        if user is not None and user.email:
            return user.email
        if employee is not None and employee.email:
            return employee.email
        return None

    @classmethod
    def prepare_notification_delivery(
        cls,
        *,
        notification_type: str,
        title: str,
        recipient_user: User | None = None,
        recipient_employee: Employee | None = None,
        preferences: NotificationPreference | None = None,
        company_wide: bool = False,
    ) -> dict[str, Any]:
        recipient_email = cls.recipient_email(recipient_user, recipient_employee)
        if company_wide:
            status = "skipped"
            skipped_reason = "company_wide_email_not_supported_in_phase_2_step_2"
        elif preferences is None or not preferences.email_enabled:
            status = "skipped"
            skipped_reason = "email_preferences_disabled"
        elif recipient_email is None:
            status = "skipped"
            skipped_reason = "recipient_email_missing"
        else:
            status = "pending"
            skipped_reason = "real_email_provider_not_configured"

        return {
            "channel": "email",
            "status": status,
            "recipient_email": recipient_email,
            "template": "notification_alert",
            "notification_type": notification_type,
            "subject": title,
            "skipped_reason": skipped_reason,
        }

    @staticmethod
    def prepare_employee_onboarding_delivery(
        *,
        template: str,
        recipient_email: str,
        company_name: str | None,
        action_path: str,
    ) -> dict[str, Any]:
        """Prepare invite/activation email metadata without sending email.

        The raw action path is returned only to the caller response for local
        development. Persisted metadata records that a link was prepared without
        storing the token-bearing URL.
        """

        subject_company = company_name or "FebGrid"
        return {
            "channel": "email",
            "status": "pending",
            "recipient_email": recipient_email,
            "template": template,
            "subject": f"{subject_company} FebGrid onboarding",
            "skipped_reason": "real_email_provider_not_configured",
            "action_path_prepared": bool(action_path),
        }
