import hashlib
import mimetypes
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status

from app.models.attachment import Attachment
from app.schemas.attachment import AttachmentCreate


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
    STORAGE_PROVIDER = "local"
    STORAGE_ROOT = Path(__file__).resolve().parents[2] / "storage" / "uploads"
    ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".csv", ".doc", ".docx", ".xls", ".xlsx"}
    ALLOWED_CONTENT_TYPES = {
        "image/png",
        "image/jpeg",
        "image/webp",
        "application/pdf",
        "text/csv",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }

    @staticmethod
    def sanitize_original_filename(filename: str | None) -> str:
        raw_name = Path(filename or "upload").name.strip()
        safe_name = re.sub(r"[^A-Za-z0-9._ -]+", "_", raw_name).strip(" .")
        return safe_name[:255] or "upload"

    @classmethod
    def validate_file_type(cls, original_file_name: str, content_type: str | None) -> str:
        extension = Path(original_file_name).suffix.lower()
        detected_type = content_type or mimetypes.guess_type(original_file_name)[0] or "application/octet-stream"
        if extension not in cls.ALLOWED_EXTENSIONS or detected_type not in cls.ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="File type is not allowed for File Upload v1",
            )
        return detected_type

    @classmethod
    def build_storage_path(cls, *, company_id: UUID, work_object_id: UUID, original_file_name: str) -> tuple[str, Path]:
        extension = Path(original_file_name).suffix.lower()
        stored_name = f"{uuid4()}{extension}"
        relative_path = Path("uploads") / str(company_id) / "work-objects" / str(work_object_id) / stored_name
        absolute_path = (cls.STORAGE_ROOT.parent / relative_path).resolve()
        root = cls.STORAGE_ROOT.resolve()
        if not absolute_path.is_relative_to(root):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage path")
        return relative_path.as_posix(), absolute_path

    @classmethod
    def resolve_storage_path(cls, storage_path: str) -> Path:
        relative_path = Path(storage_path)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        absolute_path = (cls.STORAGE_ROOT.parent / relative_path).resolve()
        root = cls.STORAGE_ROOT.resolve()
        if not absolute_path.is_relative_to(root):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return absolute_path

    @classmethod
    def save_upload(cls, *, file: UploadFile, company_id: UUID, work_object_id: UUID) -> StoredUpload:
        original_file_name = cls.sanitize_original_filename(file.filename)
        content_type = cls.validate_file_type(original_file_name, file.content_type)
        storage_path, absolute_path = cls.build_storage_path(
            company_id=company_id,
            work_object_id=work_object_id,
            original_file_name=original_file_name,
        )
        absolute_path.parent.mkdir(parents=True, exist_ok=True)

        size = 0
        checksum = hashlib.sha256()
        try:
            with absolute_path.open("wb") as output:
                while True:
                    chunk = file.file.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > cls.MAX_FILE_SIZE_BYTES:
                        output.close()
                        absolute_path.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                            detail="File is larger than the 10 MB upload limit",
                        )
                    checksum.update(chunk)
                    output.write(chunk)
        finally:
            file.file.seek(0)

        return StoredUpload(
            file_name=Path(storage_path).name,
            original_file_name=original_file_name,
            content_type=content_type,
            file_size=size,
            extension=Path(original_file_name).suffix.lower(),
            checksum_sha256=checksum.hexdigest(),
            storage_provider=cls.STORAGE_PROVIDER,
            storage_path=storage_path,
        )

    @staticmethod
    def build_attachment(payload: AttachmentCreate) -> Attachment:
        return Attachment(
            company_id=payload.company_id,
            work_object_id=payload.work_object_id,
            project_id=payload.project_id,
            uploaded_by_user_id=payload.uploaded_by_user_id,
            uploaded_by_employee_id=payload.uploaded_by_employee_id,
            linked_entity_type=payload.linked_entity_type,
            linked_entity_id=payload.linked_entity_id,
            file_name=payload.file_name,
            original_file_name=payload.original_file_name,
            content_type=payload.content_type,
            file_size=payload.file_size,
            extension=payload.extension,
            checksum_sha256=payload.checksum_sha256,
            storage_provider=payload.storage_provider,
            storage_path=payload.storage_path,
            public_url=payload.public_url,
            description=payload.description,
            tags=payload.tags,
            processing_status=payload.processing_status,
            scan_status=payload.scan_status,
            ai_processing_status=payload.ai_processing_status,
            metadata_json=payload.metadata,
            is_active=payload.is_active,
        )

    @classmethod
    def delete_local_file(cls, attachment: Attachment) -> None:
        if attachment.storage_provider != cls.STORAGE_PROVIDER:
            return
        try:
            path = cls.resolve_storage_path(attachment.storage_path)
        except HTTPException:
            return
        path.unlink(missing_ok=True)
        parent = path.parent
        root = cls.STORAGE_ROOT.resolve()
        while parent != root and parent.is_relative_to(root):
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    @classmethod
    def copy_probe_file(cls, *, source_path: Path, company_id: UUID, work_object_id: UUID, original_file_name: str) -> StoredUpload:
        original = cls.sanitize_original_filename(original_file_name)
        content_type = cls.validate_file_type(original, mimetypes.guess_type(original)[0])
        if source_path.stat().st_size > cls.MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail="File is larger than the 10 MB upload limit")
        storage_path, absolute_path = cls.build_storage_path(company_id=company_id, work_object_id=work_object_id, original_file_name=original)
        absolute_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source_path, absolute_path)
        return StoredUpload(
            file_name=Path(storage_path).name,
            original_file_name=original,
            content_type=content_type,
            file_size=source_path.stat().st_size,
            extension=Path(original).suffix.lower(),
            checksum_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),
            storage_provider=cls.STORAGE_PROVIDER,
            storage_path=storage_path,
        )
