import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status

from app.core.config import get_settings

TOKEN_TYPE = "access"
TOKEN_ALGORITHM = "HS256"
PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 210_000
ACCESS_TOKEN_EXPIRE_HOURS = 12
_DEV_TOKEN_SECRET = secrets.token_urlsafe(48)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def _token_secret() -> str:
    configured_secret = get_settings().jwt_secret_key
    if configured_secret is not None and configured_secret.get_secret_value():
        return configured_secret.get_secret_value()
    return _DEV_TOKEN_SECRET


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return "$".join(
        [
            PASSWORD_ALGORITHM,
            str(PASSWORD_ITERATIONS),
            _base64url_encode(salt),
            _base64url_encode(digest),
        ],
    )


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False

    try:
        algorithm, iterations, salt, expected_digest = password_hash.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _base64url_decode(salt),
            int(iterations),
        )
        return hmac.compare_digest(_base64url_encode(actual_digest), expected_digest)
    except (TypeError, ValueError):
        return False


def create_access_token(*, user_id: UUID, company_id: UUID, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "company_id": str(company_id),
        "role": role,
        "typ": TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)).timestamp()),
    }
    header = {"alg": TOKEN_ALGORITHM, "typ": "JWT"}
    encoded_header = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(_token_secret().encode("utf-8"), f"{encoded_header}.{encoded_payload}".encode("ascii"), hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_base64url_encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".", 2)
        expected_signature = hmac.new(
            _token_secret().encode("utf-8"),
            f"{encoded_header}.{encoded_payload}".encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(_base64url_encode(expected_signature), encoded_signature):
            raise credentials_error

        payload = json.loads(_base64url_decode(encoded_payload))
        if payload.get("typ") != TOKEN_TYPE or int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            raise credentials_error
        return payload
    except (TypeError, ValueError, json.JSONDecodeError):
        raise credentials_error from None
