from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import httpx
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.schemas.bulk_invite import JavaBulkInviteValidationResponse


SAFE_JAVA_VALIDATION_CODES = {
    "BULK_INVITE_FILE_REQUIRED",
    "BULK_INVITE_FILE_TOO_LARGE",
    "BULK_INVITE_UNSUPPORTED_FILE",
    "BULK_INVITE_MISSING_HEADERS",
    "BULK_INVITE_TOO_MANY_ROWS",
    "BULK_INVITE_MALFORMED_CSV",
}


@dataclass(frozen=True)
class JavaBulkInviteClientError(Exception):
    code: str
    message: str
    status_code: int


class JavaBulkInviteClient:
    """Small internal client for the Java-only CSV validation service.

    This client intentionally transports a CSV only. It never sends a FebGrid
    session, user token, company database credentials, invitation token, or
    authorization decision to Java.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def validate_csv(
        self,
        *,
        file_name: str,
        content: bytes,
        request_id: UUID,
    ) -> JavaBulkInviteValidationResponse:
        base_url = self.settings.java_bulk_invite_base_url.rstrip("/")
        service_key = self.settings.java_bulk_invite_service_key
        key_value = service_key.get_secret_value() if service_key is not None else ""
        if not base_url or not key_value:
            raise JavaBulkInviteClientError(
                code="BULK_INVITE_SERVICE_UNAVAILABLE",
                message="Bulk invite validation service is unavailable. Try again later.",
                status_code=503,
            )

        timeout_seconds = max(1, min(self.settings.java_bulk_invite_timeout_seconds, 60))
        timeout = httpx.Timeout(timeout_seconds, connect=min(3, timeout_seconds), read=timeout_seconds, write=timeout_seconds)
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    f"{base_url}/internal/v1/bulk-invites/validate",
                    headers={
                        "X-FebGrid-Service-Key": key_value,
                        "X-Request-ID": str(request_id),
                    },
                    files={"file": (file_name, content, "text/csv")},
                )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPError):
            raise JavaBulkInviteClientError(
                code="BULK_INVITE_SERVICE_UNAVAILABLE",
                message="Bulk invite validation service is unavailable. Try again later.",
                status_code=503,
            ) from None

        if response.status_code >= 400:
            payload = self._safe_json(response)
            code = payload.get("code") if isinstance(payload.get("code"), str) else ""
            if code in SAFE_JAVA_VALIDATION_CODES:
                raise JavaBulkInviteClientError(code=code, message="CSV validation failed.", status_code=422)
            raise JavaBulkInviteClientError(
                code="BULK_INVITE_SERVICE_UNAVAILABLE",
                message="Bulk invite validation service is unavailable. Try again later.",
                status_code=503,
            )

        try:
            return JavaBulkInviteValidationResponse.model_validate(response.json())
        except (ValueError, ValidationError):
            raise JavaBulkInviteClientError(
                code="BULK_INVITE_SERVICE_UNAVAILABLE",
                message="Bulk invite validation service returned an invalid response.",
                status_code=503,
            ) from None

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict[str, object]:
        try:
            payload = response.json()
        except ValueError:
            return {}
        return payload if isinstance(payload, dict) else {}
