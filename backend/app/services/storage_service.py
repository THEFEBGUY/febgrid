"""Private Supabase Storage access for FebGrid file attachments.

The application keeps object paths in PostgreSQL and uses its backend-only
service-role credential to access the private ``work-files`` bucket. Browser
clients never receive that credential or an unauthorised bucket URL.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings


@dataclass(frozen=True)
class StoredObject:
    path: str
    content_type: str
    size: int


class SupabaseStorageService:
    """Small reusable server-side client for the configured private bucket."""

    PROVIDER: Final[str] = "supabase"

    @classmethod
    def _configuration(cls) -> tuple[str, str, str, float]:
        settings = get_settings()
        base_url = settings.supabase_url.strip().rstrip("/")
        service_role_key = settings.supabase_service_role_key.get_secret_value() if settings.supabase_service_role_key else ""
        bucket = settings.supabase_storage_bucket.strip()
        if not base_url or not service_role_key or not bucket:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Private file storage is not configured for this deployment",
            )
        return base_url, service_role_key, bucket, float(settings.supabase_storage_timeout_seconds)

    @staticmethod
    def _safe_path(storage_path: str) -> str:
        path = storage_path.strip().lstrip("/")
        parts = path.split("/")
        if not path or "\\" in path or any(not part or part in {".", ".."} for part in parts):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return path

    @classmethod
    def _headers(cls, service_role_key: str, content_type: str | None = None) -> dict[str, str]:
        headers = {
            "authorization": f"Bearer {service_role_key}",
            "apikey": service_role_key,
        }
        if content_type:
            headers["content-type"] = content_type
        return headers

    @classmethod
    def upload(cls, *, storage_path: str, content: bytes, content_type: str) -> StoredObject:
        base_url, service_role_key, bucket, timeout_seconds = cls._configuration()
        path = cls._safe_path(storage_path)
        url = f"{base_url}/storage/v1/object/{bucket}/{path}"
        try:
            response = httpx.post(
                url,
                content=content,
                headers={**cls._headers(service_role_key, content_type), "x-upsert": "false"},
                timeout=timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File storage timed out. Please try again.") from exc
        except httpx.RequestError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File storage is temporarily unavailable") from exc
        if response.status_code not in {200, 201}:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File could not be stored securely. Please try again.")
        return StoredObject(path=path, content_type=content_type, size=len(content))

    @classmethod
    def download(cls, *, storage_path: str) -> bytes:
        base_url, service_role_key, bucket, timeout_seconds = cls._configuration()
        path = cls._safe_path(storage_path)
        try:
            response = httpx.get(
                f"{base_url}/storage/v1/object/{bucket}/{path}",
                headers=cls._headers(service_role_key),
                timeout=timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File storage timed out. Please try again.") from exc
        except httpx.RequestError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File storage is temporarily unavailable") from exc
        if response.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        if response.status_code != status.HTTP_200_OK:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File storage is temporarily unavailable")
        return response.content

    @classmethod
    def delete(cls, *, storage_path: str) -> None:
        base_url, service_role_key, bucket, timeout_seconds = cls._configuration()
        path = cls._safe_path(storage_path)
        try:
            response = httpx.request(
                "DELETE",
                f"{base_url}/storage/v1/object/{bucket}",
                headers=cls._headers(service_role_key, "application/json"),
                json={"prefixes": [path]},
                timeout=timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File storage timed out. Please try again.") from exc
        except httpx.RequestError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File storage is temporarily unavailable") from exc
        if response.status_code not in {200, 204, 404}:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="File could not be removed from secure storage")
