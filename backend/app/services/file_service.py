"""File validation and attachment metadata backed by private object storage."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status

from app.models.attachment import Attachment
from app.schemas.attachment import AttachmentCreate
from app.services.storage_service import SupabaseStorageService


@dataclass(frozen=True)
class StoredUpload:
    file_name: str
    original_file_name: str
    content_type: str
    file_size: int
    extension: str
    checksum_sha256: str
    storage_provider: str
    storage_path: str


class FileService:
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
    MAX_AUDIO_FILE_SIZE_BYTES = 15 * 1024 * 1024
    STORAGE_PROVIDER = SupabaseStorageService.PROVIDER
    SAFE_TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log"}
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".webm", ".ogg"}
    ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".doc", ".docx", ".xls", ".xlsx"} | SAFE_TEXT_EXTENSIONS | AUDIO_EXTENSIONS
    SAFE_TEXT_CONTENT_TYPES = {"text/plain", "text/markdown", "text/csv", "application/csv", "application/json", "application/octet-stream"}
    AUDIO_CONTENT_TYPES = {"audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/mp4", "audio/x-m4a", "audio/webm", "audio/ogg", "application/ogg"}
    ALLOWED_CONTENT_TYPES = {
        "image/png", "image/jpeg", "image/webp", "application/pdf", "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    } | (SAFE_TEXT_CONTENT_TYPES - {"application/octet-stream"}) | AUDIO_CONTENT_TYPES

    @staticmethod
    def sanitize_original_filename(filename: str | None) -> str:
        raw_name = Path(filename or "upload").name.strip()
        safe_name = re.sub(r"[^A-Za-z0-9._ -]+", "_", raw_name).strip(" .")
        return safe_name[:255] or "upload"

    @classmethod
    def validate_file_type(cls, original_file_name: str, content_type: str | None) -> str:
        extension = Path(original_file_name).suffix.lower()
        detected_type = content_type or mimetypes.guess_type(original_file_name)[0] or "application/octet-stream"
        if extension in cls.SAFE_TEXT_EXTENSIONS and detected_type in cls.SAFE_TEXT_CONTENT_TYPES:
            return detected_type
        if extension in cls.AUDIO_EXTENSIONS and detected_type in cls.AUDIO_CONTENT_TYPES:
            return detected_type
        if extension not in cls.ALLOWED_EXTENSIONS or detected_type not in cls.ALLOWED_CONTENT_TYPES:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="File type is not allowed for File Upload v1")
        return detected_type

    @classmethod
    def upload_limit_for_extension(cls, extension: str) -> int:
        return cls.MAX_AUDIO_FILE_SIZE_BYTES if extension.lower() in cls.AUDIO_EXTENSIONS else cls.MAX_FILE_SIZE_BYTES

    @classmethod
    def build_storage_path(cls, *, company_id: UUID, linked_entity_type: str, linked_entity_id: UUID, original_file_name: str) -> str:
        entity_segment = {"work_object": "work-objects", "project": "projects"}.get(linked_entity_type)
        if entity_segment is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file attachment target")
        extension = Path(original_file_name).suffix.lower()
        return f"companies/{company_id}/{entity_segment}/{linked_entity_id}/{uuid4()}{extension}"

    @classmethod
    def ensure_company_storage_path(cls, *, company_id: UUID, storage_path: str) -> str:
        safe_path = SupabaseStorageService._safe_path(storage_path)
        if not safe_path.startswith(f"companies/{company_id}/"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return safe_path

    @classmethod
    def save_upload(cls, *, file: UploadFile, company_id: UUID, linked_entity_type: str, linked_entity_id: UUID) -> StoredUpload:
        original_file_name = cls.sanitize_original_filename(file.filename)
        content_type = cls.validate_file_type(original_file_name, file.content_type)
        upload_limit = cls.upload_limit_for_extension(Path(original_file_name).suffix.lower())
        content = file.file.read(upload_limit + 1)
        file.file.seek(0)
        if len(content) > upload_limit:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=f"File is larger than the {upload_limit // (1024 * 1024)} MB upload limit")
        storage_path = cls.build_storage_path(
            company_id=company_id,
            linked_entity_type=linked_entity_type,
            linked_entity_id=linked_entity_id,
            original_file_name=original_file_name,
        )
        SupabaseStorageService.upload(storage_path=storage_path, content=content, content_type=content_type)
        return StoredUpload(
            file_name=storage_path.rsplit("/", 1)[-1],
            original_file_name=original_file_name,
            content_type=content_type,
            file_size=len(content),
            extension=Path(original_file_name).suffix.lower(),
            checksum_sha256=hashlib.sha256(content).hexdigest(),
            storage_provider=cls.STORAGE_PROVIDER,
            storage_path=storage_path,
        )

    @classmethod
    def read_attachment_bytes(cls, attachment: Attachment) -> bytes:
        if attachment.storage_provider != cls.STORAGE_PROVIDER:
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="This legacy file is not available from secure storage")
        storage_path = cls.ensure_company_storage_path(company_id=attachment.company_id, storage_path=attachment.storage_path)
        return SupabaseStorageService.download(storage_path=storage_path)

    @classmethod
    def delete_stored_file(cls, attachment: Attachment) -> None:
        if attachment.storage_provider == cls.STORAGE_PROVIDER:
            storage_path = cls.ensure_company_storage_path(company_id=attachment.company_id, storage_path=attachment.storage_path)
            SupabaseStorageService.delete(storage_path=storage_path)

    @staticmethod
    def build_attachment(payload: AttachmentCreate) -> Attachment:
        return Attachment(
            company_id=payload.company_id, work_object_id=payload.work_object_id, project_id=payload.project_id,
            uploaded_by_user_id=payload.uploaded_by_user_id, uploaded_by_employee_id=payload.uploaded_by_employee_id,
            linked_entity_type=payload.linked_entity_type, linked_entity_id=payload.linked_entity_id,
            file_name=payload.file_name, original_file_name=payload.original_file_name, content_type=payload.content_type,
            file_size=payload.file_size, extension=payload.extension, checksum_sha256=payload.checksum_sha256,
            storage_provider=payload.storage_provider, storage_path=payload.storage_path, public_url=payload.public_url,
            description=payload.description, tags=payload.tags, processing_status=payload.processing_status,
            scan_status=payload.scan_status, ai_processing_status=payload.ai_processing_status,
            metadata_json=payload.metadata, is_active=payload.is_active,
        )
