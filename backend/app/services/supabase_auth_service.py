"""Small server-side verifier for Supabase Auth access tokens.

The browser receives only the Supabase anon key. FebGrid validates the returned
access token with Supabase Auth before using its email to accept an invitation.
No Supabase secret, token, or response body is logged or persisted here.
"""

from dataclasses import dataclass

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.core.performance import measure_external


@dataclass(frozen=True)
class SupabaseIdentity:
    user_id: str
    email: str


class SupabaseAuthService:
    @staticmethod
    def _configuration() -> tuple[str, str, float]:
        settings = get_settings()
        api_key = settings.supabase_anon_key.get_secret_value() if settings.supabase_anon_key else ""
        base_url = settings.supabase_url.strip().rstrip("/")
        if not base_url or not api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Supabase magic-link authentication is not configured for this deployment",
            )
        return base_url, api_key, float(settings.supabase_auth_timeout_seconds)

    @classmethod
    def verify_access_token(cls, access_token: str) -> SupabaseIdentity:
        if not access_token or len(access_token) > 8_192:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Supabase authentication session")

        base_url, api_key, timeout = cls._configuration()
        try:
            with measure_external("supabase_auth"):
                response = httpx.get(
                    f"{base_url}/auth/v1/user",
                    headers={"apikey": api_key, "Authorization": f"Bearer {access_token}"},
                    timeout=timeout,
                )
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase authentication is temporarily unavailable") from exc
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase authentication is temporarily unavailable") from exc

        if response.status_code in {401, 403}:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Supabase authentication session is invalid or expired")
        if response.status_code >= 400:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase authentication is temporarily unavailable")

        try:
            payload = response.json()
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase authentication returned an invalid response") from exc
        return cls._identity_from_payload(payload)

    @staticmethod
    def _identity_from_payload(payload: object) -> SupabaseIdentity:
        if not isinstance(payload, dict):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Supabase authentication session is invalid")
        user_id = payload.get("id")
        email = payload.get("email")
        if not isinstance(user_id, str) or not user_id.strip() or not isinstance(email, str) or "@" not in email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Supabase authentication session is invalid")
        return SupabaseIdentity(user_id=user_id.strip(), email=email.strip().lower())
