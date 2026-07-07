import json
import re
import struct
import wave
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.utils import ensure_company, get_or_404
from app.core.ai_config import REAL_AI_PROVIDER_MODES, get_ai_provider_config, normalize_provider_mode
from app.core.permissions import MANAGER_ROLES, OWNER_ADMIN_ROLES, ensure_company_access, ensure_role
from app.models.ai_job import AIJob
from app.models.attachment import Attachment
from app.models.communication import Announcement
from app.models.common import utc_now
from app.models.company import Company
from app.models.department import Department
from app.models.employee import Employee
from app.models.event import Event
from app.models.leave_request import LeaveRequest
from app.models.notification import Notification
from app.models.project import Project, ProjectMember
from app.models.team import Team
from app.models.user import User
from app.models.work_object import WorkObject
from app.schemas.ai_job import (
    AI_JOB_STATUSES,
    AI_JOB_TYPES,
    MOCK_AI_JOB_TYPES,
    REAL_AI_JOB_TYPES,
    AICapabilitiesRead,
    AICapability,
    AIJobCreate,
    AIProviderStatusRead,
    AISafetySettingsRead,
    AISafetySettingsUpdate,
)
from app.services.ai_prompt_templates import build_summary_messages
from app.services.ai_providers import AIProviderError, AIProviderRequest, build_ai_provider
from app.services.event_service import EventService
from app.services.file_service import FileService
from app.services.notification_service import NotificationService

AI_INPUT_MAX_BYTES = 20_000
COMPANY_AI_SETTINGS_KEY = "ai"
RESERVED_AI_KEYS = {"system_prompt", "raw_prompt", "provider_api_key", "api_key", "secret", "password", "token"}
FILE_SUMMARY_MAX_BYTES = 1 * 1024 * 1024
FILE_SUMMARY_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log"}
DOCUMENT_ANALYSIS_EXTENSIONS = FILE_SUMMARY_EXTENSIONS
IMAGE_ANALYSIS_MAX_BYTES = 5 * 1024 * 1024
IMAGE_ANALYSIS_MAX_DIMENSION = 4096
IMAGE_ANALYSIS_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
IMAGE_ANALYSIS_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}
AUDIO_TRANSCRIPTION_MAX_BYTES = 15 * 1024 * 1024
AUDIO_TRANSCRIPTION_MAX_DURATION_SECONDS = 10 * 60
AUDIO_TRANSCRIPTION_EXTENSIONS = {".mp3", ".wav", ".m4a", ".webm", ".ogg"}
AUDIO_TRANSCRIPTION_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/x-m4a",
    "audio/webm",
    "audio/ogg",
    "application/ogg",
}
SECRET_FILE_EXTENSIONS = {".env", ".pem", ".key"}
SECRET_FILE_NAMES = {".env", "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519"}
SECRET_VALUE_PATTERN = re.compile(
    r"(?im)\b(api[_-]?key|secret|password|passwd|token|bearer|access[_-]?token|private[_-]?key)\b\s*[:=]\s*([^\s\"']{6,})"
)
BEARER_PATTERN = re.compile(r"(?i)\bAuthorization\s*:\s*Bearer\s+[A-Za-z0-9._~+/\-=]+")
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
LONG_SECRET_PATTERN = re.compile(r"\b[A-Za-z0-9_\-]{40,}\b")

CAPABILITY_DEFINITIONS = [
    AICapability(
        job_type="work_object_summary_mock",
        label="Work object summary",
        description="Prepare a future-safe mock summary for one work object.",
    ),
    AICapability(
        job_type="project_summary_mock",
        label="Project summary",
        description="Prepare a future-safe mock summary for one project.",
    ),
    AICapability(
        job_type="employee_workload_mock",
        label="Employee workload",
        description="Prepare a future-safe mock workload placeholder for one employee.",
    ),
    AICapability(
        job_type="file_summary_mock",
        label="File summary",
        description="Prepare a future-safe mock file summary without reading or parsing file contents.",
    ),
    AICapability(
        job_type="company_brief_mock",
        label="Company brief",
        description="Prepare a future-safe mock company brief placeholder.",
    ),
    AICapability(
        job_type="work_object_summary_safe",
        label="Safe work summary",
        description="Run a small text-only work object summary through the configured provider.",
        mock_only=False,
    ),
    AICapability(
        job_type="project_summary_safe",
        label="Safe project summary",
        description="Run a small text-only project summary through the configured provider.",
        mock_only=False,
    ),
    AICapability(
        job_type="company_brief_safe",
        label="Safe company brief",
        description="Run an owner/admin executive brief from aggregated company signals through the configured provider.",
        mock_only=False,
    ),
    AICapability(
        job_type="file_summary_safe",
        label="Safe file summary",
        description="Run a supported text-file summary through the configured provider after file safety checks.",
        mock_only=False,
    ),
    AICapability(
        job_type="document_analysis_safe",
        label="Safe document analysis",
        description="Analyze supported text documents for structured operational insights after document safety checks.",
        mock_only=False,
    ),
    AICapability(
        job_type="image_analysis_safe",
        label="Safe image analysis",
        description="Analyze supported images for operational context after image safety checks. Real providers must explicitly support image input.",
        mock_only=False,
    ),
    AICapability(
        job_type="audio_transcription_safe",
        label="Safe audio transcription",
        description="Transcribe supported audio files into operational notes after audio safety checks. Real providers must explicitly support audio transcription.",
        mock_only=False,
    ),
]


def metadata_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def linked_employee(db: Session, current_user: User | None) -> Employee | None:
    if current_user is None:
        return None
    return db.scalar(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.user_id == current_user.id,
            Employee.is_active.is_(True),
        )
    )


def safe_payload_size(payload: dict[str, Any]) -> int:
    try:
        return len(json.dumps(payload, default=str).encode("utf-8"))
    except (TypeError, ValueError):
        return AI_INPUT_MAX_BYTES + 1


def safe_text(value: Any, max_chars: int = 1200) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_chars]


def safe_json_value(value: Any, *, max_chars: int = 500, depth: int = 0) -> Any:
    if depth > 2:
        return None
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return safe_text(value, max_chars)
    if isinstance(value, list):
        return [safe_json_value(item, max_chars=max_chars, depth=depth + 1) for item in value[:10]]
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, nested in list(value.items())[:20]:
            text_key = safe_text(key, 80)
            if text_key and text_key.lower() not in RESERVED_AI_KEYS:
                cleaned[text_key] = safe_json_value(nested, max_chars=max_chars, depth=depth + 1)
        return cleaned
    return safe_text(value, max_chars)


def display_name(employee: Employee | None) -> str | None:
    if employee is None:
        return None
    return safe_text(employee.full_name, 160)


def contains_reserved_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in RESERVED_AI_KEYS:
                return True
            if contains_reserved_key(nested):
                return True
    if isinstance(value, list):
        return any(contains_reserved_key(item) for item in value)
    return False


def file_extension(attachment: Attachment) -> str:
    extension = (attachment.extension or Path(attachment.original_file_name).suffix or "").lower()
    return extension.strip()


def is_secret_like_filename(filename: str) -> bool:
    lowered = Path(filename).name.lower()
    extension = Path(lowered).suffix
    return lowered in SECRET_FILE_NAMES or extension in SECRET_FILE_EXTENSIONS or any(
        marker in lowered for marker in ("credential", "credentials", "private_key", "secret")
    )


def redact_secret_like_text(text: str) -> tuple[str, bool]:
    was_redacted = False

    def mark_redacted(_: re.Match[str]) -> str:
        nonlocal was_redacted
        was_redacted = True
        return "[REDACTED_SECRET]"

    redacted = PRIVATE_KEY_PATTERN.sub(mark_redacted, text)
    redacted = BEARER_PATTERN.sub(mark_redacted, redacted)
    redacted = SECRET_VALUE_PATTERN.sub(lambda match: f"{match.group(1)}=[REDACTED_SECRET]", redacted)
    if redacted != text:
        was_redacted = True
    return redacted, was_redacted


def secret_signal_count(text: str) -> int:
    return len(SECRET_VALUE_PATTERN.findall(text)) + len(BEARER_PATTERN.findall(text)) + len(PRIVATE_KEY_PATTERN.findall(text))


def detect_image_dimensions(path: Path, extension: str) -> tuple[int, int]:
    try:
        header = path.read_bytes()[:4096]
    except OSError as exc:
        raise AIProviderError("file_not_available", "Image content is not available for analysis.") from exc

    try:
        if extension == ".png":
            if len(header) < 24 or not header.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("invalid png")
            width, height = struct.unpack(">II", header[16:24])
            return int(width), int(height)
        if extension in {".jpg", ".jpeg"}:
            if len(header) < 4 or not header.startswith(b"\xff\xd8"):
                raise ValueError("invalid jpeg")
            offset = 2
            data = path.read_bytes()
            while offset < len(data):
                if data[offset] != 0xFF:
                    offset += 1
                    continue
                while offset < len(data) and data[offset] == 0xFF:
                    offset += 1
                if offset >= len(data):
                    break
                marker = data[offset]
                offset += 1
                if marker in {0xD8, 0xD9, 0x01} or 0xD0 <= marker <= 0xD7:
                    continue
                if offset + 2 > len(data):
                    break
                segment_length = int.from_bytes(data[offset : offset + 2], "big")
                if segment_length < 2 or offset + segment_length > len(data):
                    break
                if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                    if offset + 7 > len(data):
                        break
                    height = int.from_bytes(data[offset + 3 : offset + 5], "big")
                    width = int.from_bytes(data[offset + 5 : offset + 7], "big")
                    return int(width), int(height)
                offset += segment_length
        if extension == ".webp":
            if len(header) < 30 or not header.startswith(b"RIFF") or header[8:12] != b"WEBP":
                raise ValueError("invalid webp")
            chunk = header[12:16]
            if chunk == b"VP8X" and len(header) >= 30:
                width = 1 + int.from_bytes(header[24:27], "little")
                height = 1 + int.from_bytes(header[27:30], "little")
                return int(width), int(height)
            if chunk == b"VP8L" and len(header) >= 25:
                bits = int.from_bytes(header[21:25], "little")
                width = 1 + (bits & 0x3FFF)
                height = 1 + ((bits >> 14) & 0x3FFF)
                return int(width), int(height)
            if chunk == b"VP8 " and len(header) >= 30:
                width = int.from_bytes(header[26:28], "little") & 0x3FFF
                height = int.from_bytes(header[28:30], "little") & 0x3FFF
                return int(width), int(height)
    except (struct.error, ValueError) as exc:
        raise AIProviderError("corrupted_image", "This image appears to be corrupted or unreadable.") from exc
    raise AIProviderError("corrupted_image", "This image appears to be corrupted or unreadable.")


def detect_audio_duration(path: Path, extension: str) -> float | None:
    if extension != ".wav":
        return None
    try:
        with wave.open(str(path), "rb") as audio_file:
            frame_rate = audio_file.getframerate()
            frame_count = audio_file.getnframes()
            if frame_rate <= 0:
                raise wave.Error("invalid frame rate")
            return float(frame_count) / float(frame_rate)
    except (wave.Error, EOFError, OSError) as exc:
        raise AIProviderError("corrupted_audio", "This audio file appears to be corrupted or unreadable.") from exc


class AIService:
    @staticmethod
    def ensure_job_type(job_type: str) -> str:
        if job_type not in AI_JOB_TYPES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid AI job type")
        return job_type

    @staticmethod
    def ensure_status(status_value: str) -> str:
        if status_value not in AI_JOB_STATUSES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid AI job status")
        return status_value

    @staticmethod
    def actor_employee_id(db: Session, current_user: User | None) -> UUID | None:
        employee = linked_employee(db, current_user)
        return employee.id if employee else None

    @staticmethod
    def ensure_payload_safe(payload: dict[str, Any], *, max_bytes: int = AI_INPUT_MAX_BYTES) -> None:
        if safe_payload_size(payload) > max_bytes:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="AI input payload is too large")
        if contains_reserved_key(payload):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="AI input payload contains unsupported prompt or secret fields",
            )

    @classmethod
    def company_ai_settings(cls, company: Company) -> dict[str, Any]:
        settings = metadata_dict(company.settings_json)
        raw_ai = metadata_dict(settings.get(COMPANY_AI_SETTINGS_KEY))
        runtime = get_ai_provider_config()
        allowed_types = raw_ai.get("allowed_ai_job_types")
        if not isinstance(allowed_types, list):
            allowed_types = sorted(AI_JOB_TYPES)
        normalized_allowed = sorted({str(item).strip() for item in allowed_types if str(item).strip() in AI_JOB_TYPES})
        for default_job_type in {"image_analysis_safe", "audio_transcription_safe"}:
            if default_job_type not in normalized_allowed:
                normalized_allowed.append(default_job_type)
            normalized_allowed = sorted(normalized_allowed)
        return {
            "ai_enabled": bool(raw_ai.get("ai_enabled", True)),
            "external_ai_processing_allowed": bool(raw_ai.get("external_ai_processing_allowed", False)),
            "default_provider_mode": normalize_provider_mode(raw_ai.get("default_provider_mode") or runtime.provider_mode),
            "allowed_ai_job_types": normalized_allowed or sorted(AI_JOB_TYPES),
            "max_monthly_ai_jobs": raw_ai.get("max_monthly_ai_jobs") if isinstance(raw_ai.get("max_monthly_ai_jobs"), int) else None,
            "metadata": metadata_dict(raw_ai.get("metadata")),
        }

    @classmethod
    def validate_entity_access(
        cls,
        db: Session,
        *,
        company_id: UUID,
        input_entity_type: str | None,
        input_entity_id: UUID | None,
    ) -> None:
        if input_entity_type is None and input_entity_id is None:
            return
        if input_entity_type is None or input_entity_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="input_entity_type and input_entity_id must be provided together",
            )

        if input_entity_type == "company":
            company = get_or_404(db, Company, input_entity_id, label="Company")
            if company.id != company_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
            return
        if input_entity_type == "work_object":
            work_object = get_or_404(db, WorkObject, input_entity_id, label="Work object")
            ensure_company(work_object, company_id, label="Work object")
            return
        if input_entity_type == "project":
            project = get_or_404(db, Project, input_entity_id, label="Project")
            ensure_company(project, company_id, label="Project")
            return
        if input_entity_type == "employee":
            employee = get_or_404(db, Employee, input_entity_id, label="Employee")
            ensure_company(employee, company_id, label="Employee")
            return
        if input_entity_type in {"attachment", "file"}:
            attachment = get_or_404(db, Attachment, input_entity_id, label="File")
            ensure_company(attachment, company_id, label="File")
            if attachment.is_deleted or not attachment.is_active:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
            return

        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported AI input entity type")

    @staticmethod
    def validate_job_entity_pair(job_type: str, input_entity_type: str | None) -> None:
        expected = {
            "work_object_summary_safe": "work_object",
            "project_summary_safe": "project",
            "company_brief_safe": "company",
            "file_summary_safe": "attachment",
            "document_analysis_safe": "attachment",
            "image_analysis_safe": "attachment",
            "audio_transcription_safe": "attachment",
        }
        if job_type in {"file_summary_safe", "document_analysis_safe", "image_analysis_safe", "audio_transcription_safe"} and input_entity_type in {"attachment", "file"}:
            return
        if job_type in expected and input_entity_type != expected[job_type]:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{job_type} requires input_entity_type={expected[job_type]}",
            )

    @classmethod
    def ensure_file_summary_access(cls, db: Session, *, attachment: Attachment, current_user: User) -> None:
        ensure_company_access(current_user, attachment.company_id)
        if current_user.role in MANAGER_ROLES:
            return
        if attachment.uploaded_by_user_id == current_user.id:
            return

        employee = linked_employee(db, current_user)
        if employee is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        if attachment.uploaded_by_employee_id == employee.id:
            return
        if attachment.work_object_id is not None:
            work_object = get_or_404(db, WorkObject, attachment.work_object_id, label="Work object")
            ensure_company(work_object, attachment.company_id, label="Work object")
            if work_object.assignee_employee_id == employee.id or work_object.creator_employee_id == employee.id:
                return
        if attachment.project_id is not None:
            project = get_or_404(db, Project, attachment.project_id, label="Project")
            ensure_company(project, attachment.company_id, label="Project")
            if project.owner_employee_id == employee.id:
                return
            membership = db.scalar(
                select(ProjectMember.id).where(
                    ProjectMember.company_id == attachment.company_id,
                    ProjectMember.project_id == project.id,
                    ProjectMember.employee_id == employee.id,
                    ProjectMember.is_active.is_(True),
                )
            )
            if membership is not None:
                return
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    @classmethod
    def ensure_summary_entity_permission(
        cls,
        db: Session,
        *,
        company_id: UUID,
        job_type: str,
        input_entity_type: str,
        input_entity_id: UUID,
        current_user: User,
    ) -> None:
        if job_type not in {"file_summary_safe", "document_analysis_safe", "image_analysis_safe", "audio_transcription_safe"}:
            return
        attachment = get_or_404(db, Attachment, input_entity_id, label="File")
        ensure_company(attachment, company_id, label="File")
        if attachment.is_deleted or not attachment.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        cls.ensure_file_summary_access(db, attachment=attachment, current_user=current_user)

    @classmethod
    def resolved_provider_mode(cls, job_type: str, company_settings: dict[str, Any]) -> str:
        if job_type in MOCK_AI_JOB_TYPES:
            return "mock"
        return normalize_provider_mode(company_settings.get("default_provider_mode"))

    @classmethod
    def provider_key_for_mode(cls, provider_mode: str) -> str:
        if provider_mode == "groq":
            return "groq"
        if provider_mode == "mock":
            return "mock"
        return provider_mode

    @classmethod
    def create_job(cls, db: Session, *, payload: AIJobCreate, current_user: User) -> AIJob:
        ensure_company_access(current_user, payload.company_id)
        ensure_role(current_user, MANAGER_ROLES)
        if payload.job_type == "company_brief_safe":
            ensure_role(current_user, OWNER_ADMIN_ROLES)
        company = get_or_404(db, Company, payload.company_id, label="Company")
        cls.ensure_job_type(payload.job_type)
        cls.ensure_payload_safe(payload.input_payload)
        cls.ensure_payload_safe(payload.metadata)
        cls.validate_job_entity_pair(payload.job_type, payload.input_entity_type)
        cls.validate_entity_access(
            db,
            company_id=payload.company_id,
            input_entity_type=payload.input_entity_type,
            input_entity_id=payload.input_entity_id,
        )
        if payload.input_entity_type is not None and payload.input_entity_id is not None:
            cls.ensure_summary_entity_permission(
                db,
                company_id=payload.company_id,
                job_type=payload.job_type,
                input_entity_type=payload.input_entity_type,
                input_entity_id=payload.input_entity_id,
                current_user=current_user,
            )

        company_settings = cls.company_ai_settings(company)
        if payload.job_type not in company_settings["allowed_ai_job_types"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AI job type is not allowed for this company")
        provider_mode = cls.resolved_provider_mode(payload.job_type, company_settings)
        requester_employee = linked_employee(db, current_user)
        job = AIJob(
            company_id=payload.company_id,
            requested_by_user_id=current_user.id,
            requested_by_employee_id=requester_employee.id if requester_employee else None,
            job_type=payload.job_type,
            status="queued",
            priority=payload.priority,
            input_entity_type=payload.input_entity_type,
            input_entity_id=payload.input_entity_id,
            input_payload=metadata_dict(payload.input_payload),
            output_payload={},
            provider_key=cls.provider_key_for_mode(provider_mode),
            provider_mode=provider_mode,
            max_attempts=max(1, min(payload.max_attempts, 3)),
            queued_at=utc_now(),
            next_attempt_at=payload.scheduled_at,
            timeout_seconds=get_ai_provider_config().groq_timeout_seconds,
            run_mode="manual",
            scheduled_at=payload.scheduled_at,
            metadata_json={
                **metadata_dict(payload.metadata),
                "provider_mode_requested": provider_mode,
                "external_processing_used": False,
                "safety_status": "queued",
            },
            related_entity_type=payload.input_entity_type,
            related_entity_id=payload.input_entity_id,
        )
        db.add(job)
        db.flush()
        cls.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.created",
            title=f"AI job queued: {job.job_type}",
            description="A tenant-safe AI foundation job was created.",
        )
        cls.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.queued",
            title=f"AI job queued: {job.job_type}",
            description="A tenant-safe AI foundation job entered the queue.",
        )
        return job

    @classmethod
    def create_summary_job(
        cls,
        db: Session,
        *,
        company_id: UUID,
        job_type: str,
        input_entity_type: str,
        input_entity_id: UUID,
        current_user: User,
    ) -> AIJob:
        ensure_company_access(current_user, company_id)
        if job_type not in {
            "work_object_summary_safe",
            "project_summary_safe",
            "company_brief_safe",
            "file_summary_safe",
            "document_analysis_safe",
            "image_analysis_safe",
            "audio_transcription_safe",
        }:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unsupported AI summary type")
        if job_type == "company_brief_safe":
            ensure_role(current_user, OWNER_ADMIN_ROLES)
        company = get_or_404(db, Company, company_id, label="Company")
        cls.ensure_job_type(job_type)
        cls.validate_job_entity_pair(job_type, input_entity_type)
        cls.validate_entity_access(
            db,
            company_id=company_id,
            input_entity_type=input_entity_type,
            input_entity_id=input_entity_id,
        )
        cls.ensure_summary_entity_permission(
            db,
            company_id=company_id,
            job_type=job_type,
            input_entity_type=input_entity_type,
            input_entity_id=input_entity_id,
            current_user=current_user,
        )

        company_settings = cls.company_ai_settings(company)
        if job_type not in company_settings["allowed_ai_job_types"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AI job type is not allowed for this company")

        provider_mode = cls.resolved_provider_mode(job_type, company_settings)
        requester_employee = linked_employee(db, current_user)
        job = AIJob(
            company_id=company_id,
            requested_by_user_id=current_user.id,
            requested_by_employee_id=requester_employee.id if requester_employee else None,
            job_type=job_type,
            status="queued",
            priority="normal",
            input_entity_type=input_entity_type,
            input_entity_id=input_entity_id,
            input_payload={
                "source": "entity_ai_summary",
                "safe_fields_only": True,
                "frontend_prompt_allowed": False,
            },
            output_payload={},
            provider_key=cls.provider_key_for_mode(provider_mode),
            provider_mode=provider_mode,
            max_attempts=3,
            queued_at=utc_now(),
            timeout_seconds=get_ai_provider_config().groq_timeout_seconds,
            run_mode="manual",
            metadata_json={
                "provider_mode_requested": provider_mode,
                "external_processing_used": False,
                "safety_status": "queued",
                "summary_feature": True,
                "input_entity_type": input_entity_type,
                "input_entity_id": str(input_entity_id),
            },
            related_entity_type=input_entity_type,
            related_entity_id=input_entity_id,
        )
        db.add(job)
        db.flush()
        cls.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.created",
            title=f"AI summary queued: {job.job_type}",
            description="A tenant-safe AI summary job was created.",
        )
        cls.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.queued",
            title=f"AI summary queued: {job.job_type}",
            description="A tenant-safe AI summary job entered the queue.",
        )
        cls.record_summary_event(db, job=job, current_user=current_user, phase="requested")
        return job

    @classmethod
    def generate_summary(
        cls,
        db: Session,
        *,
        company_id: UUID,
        job_type: str,
        input_entity_type: str,
        input_entity_id: UUID,
        current_user: User,
    ) -> AIJob:
        job = cls.create_summary_job(
            db,
            company_id=company_id,
            job_type=job_type,
            input_entity_type=input_entity_type,
            input_entity_id=input_entity_id,
            current_user=current_user,
        )
        job = cls.run_job(db, job=job, current_user=current_user)
        if job.status in {"succeeded", "failed"}:
            cls.record_summary_event(db, job=job, current_user=current_user, phase="succeeded" if job.status == "succeeded" else "failed")
        return job

    @classmethod
    def latest_summary_job(
        cls,
        db: Session,
        *,
        company_id: UUID,
        job_type: str,
        input_entity_type: str,
        input_entity_id: UUID,
        current_user: User,
    ) -> AIJob | None:
        ensure_company_access(current_user, company_id)
        if job_type == "company_brief_safe":
            ensure_role(current_user, OWNER_ADMIN_ROLES)
        cls.ensure_job_type(job_type)
        cls.validate_job_entity_pair(job_type, input_entity_type)
        cls.validate_entity_access(
            db,
            company_id=company_id,
            input_entity_type=input_entity_type,
            input_entity_id=input_entity_id,
        )
        cls.ensure_summary_entity_permission(
            db,
            company_id=company_id,
            job_type=job_type,
            input_entity_type=input_entity_type,
            input_entity_id=input_entity_id,
            current_user=current_user,
        )
        return db.scalar(
            select(AIJob)
            .where(
                AIJob.company_id == company_id,
                AIJob.job_type == job_type,
                AIJob.input_entity_type == input_entity_type,
                AIJob.input_entity_id == input_entity_id,
                AIJob.status == "succeeded",
            )
            .order_by(AIJob.completed_at.desc(), AIJob.created_at.desc())
            .limit(1)
        )

    @classmethod
    def visible_statement(cls, company_id: UUID, current_user: User):
        ensure_company_access(current_user, company_id)
        statement = select(AIJob).where(AIJob.company_id == company_id)
        if current_user.role not in OWNER_ADMIN_ROLES:
            statement = statement.where(AIJob.job_type != "company_brief_safe")
        if current_user.role not in MANAGER_ROLES:
            statement = statement.where(AIJob.requested_by_user_id == current_user.id)
        return statement

    @classmethod
    def get_visible_job(cls, db: Session, *, job_id: UUID, company_id: UUID, current_user: User) -> AIJob:
        job = db.get(AIJob, job_id)
        if job is None or job.company_id != company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI job not found")
        if job.job_type == "company_brief_safe" and current_user.role not in OWNER_ADMIN_ROLES:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI job not found")
        if current_user.role not in MANAGER_ROLES and job.requested_by_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI job not found")
        return job

    @classmethod
    def ensure_manage_job(cls, current_user: User, job: AIJob) -> None:
        ensure_company_access(current_user, job.company_id)
        if job.job_type == "company_brief_safe":
            ensure_role(current_user, OWNER_ADMIN_ROLES)
            return
        if current_user.role in MANAGER_ROLES:
            return
        if job.requested_by_user_id == current_user.id and job.input_entity_type != "company":
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission for this action")

    @classmethod
    def build_file_summary_context(
        cls,
        db: Session,
        *,
        attachment: Attachment,
        max_input_chars: int,
        purpose: str = "summary",
    ) -> dict[str, Any]:
        is_analysis = purpose == "analysis"
        unsupported_message = (
            "This document type is not supported for analysis yet."
            if is_analysis
            else "This file type is not supported for AI summary yet."
        )
        unavailable_message = "File content is not available for document analysis." if is_analysis else "File content is not available for AI summary."
        too_large_message = "This document is too large for AI document analysis v1." if is_analysis else "This file is too large for AI summary v1."
        provider_message = (
            "This file storage provider is not supported for document analysis yet."
            if is_analysis
            else "This file storage provider is not supported for AI summary yet."
        )
        extension = file_extension(attachment)
        if is_secret_like_filename(attachment.original_file_name):
            raise AIProviderError(
                "file_contains_secrets",
                "This file appears to contain secrets and cannot be analyzed." if is_analysis else "This file appears to contain secrets and cannot be summarized.",
            )
        if extension not in (DOCUMENT_ANALYSIS_EXTENSIONS if is_analysis else FILE_SUMMARY_EXTENSIONS):
            raise AIProviderError(
                "unsupported_file_type",
                unsupported_message,
                {"unsupported_reason": "unsupported_file_type", "extension": extension},
            )
        if attachment.storage_provider != FileService.STORAGE_PROVIDER:
            raise AIProviderError("unsupported_storage_provider", provider_message)
        if attachment.file_size is not None and attachment.file_size > FILE_SUMMARY_MAX_BYTES:
            raise AIProviderError("file_too_large", too_large_message, {"file_size": attachment.file_size})

        path = FileService.resolve_storage_path(attachment.storage_path)
        if not path.exists() or not path.is_file():
            raise AIProviderError("file_not_available", unavailable_message)
        actual_size = path.stat().st_size
        if actual_size > FILE_SUMMARY_MAX_BYTES:
            raise AIProviderError("file_too_large", too_large_message, {"file_size": actual_size})

        raw_text = path.read_bytes().decode("utf-8", errors="replace")
        if PRIVATE_KEY_PATTERN.search(raw_text) or secret_signal_count(raw_text) >= 3:
            raise AIProviderError(
                "file_contains_secrets",
                "This file appears to contain secrets and cannot be analyzed." if is_analysis else "This file appears to contain secrets and cannot be summarized.",
            )
        redacted_text, was_redacted = redact_secret_like_text(raw_text)
        if LONG_SECRET_PATTERN.search(redacted_text) and secret_signal_count(raw_text) > 0:
            raise AIProviderError(
                "file_contains_secrets",
                "This file appears to contain secrets and cannot be analyzed." if is_analysis else "This file appears to contain secrets and cannot be summarized.",
            )

        max_text_chars = max(1000, min(max_input_chars - 2500, max_input_chars))
        sanitized_text = redacted_text.strip()
        truncated = len(sanitized_text) > max_text_chars
        if truncated:
            sanitized_text = sanitized_text[:max_text_chars]

        uploader_name = None
        if attachment.uploaded_by_employee_id:
            uploader_name = display_name(
                db.scalar(select(Employee).where(Employee.id == attachment.uploaded_by_employee_id, Employee.company_id == attachment.company_id))
            )
        linked_work_title = None
        linked_project_name = None
        if attachment.work_object_id:
            linked_work_title = db.scalar(
                select(WorkObject.title).where(WorkObject.id == attachment.work_object_id, WorkObject.company_id == attachment.company_id)
            )
        if attachment.project_id:
            linked_project_name = db.scalar(select(Project.name).where(Project.id == attachment.project_id, Project.company_id == attachment.company_id))

        return {
            "type": "document" if is_analysis else "file",
            "file_id": str(attachment.id),
            "original_file_name": safe_text(attachment.original_file_name, 255),
            "content_type": safe_text(attachment.content_type, 120),
            "extension": extension,
            "file_size": attachment.file_size,
            "upload_date": attachment.created_at.isoformat() if attachment.created_at else None,
            "uploader_display_name": uploader_name,
            "linked_entity_type": safe_text(attachment.linked_entity_type, 80),
            "linked_entity_id": str(attachment.linked_entity_id) if attachment.linked_entity_id else None,
            "linked_work_object_title": safe_text(linked_work_title, 220),
            "linked_project_name": safe_text(linked_project_name, 220),
            "description": safe_text(attachment.description, 600),
            "tags": [safe_text(tag, 80) for tag in attachment.tags[:10] if safe_text(tag, 80)],
            "text": sanitized_text,
            "truncated": truncated,
            "redacted_secret_like_values": was_redacted,
            "extraction_mode": "utf8_text_only",
            "analysis_mode": purpose,
        }

    @classmethod
    def build_image_analysis_context(
        cls,
        db: Session,
        *,
        attachment: Attachment,
    ) -> dict[str, Any]:
        extension = file_extension(attachment)
        content_type = (attachment.content_type or "").strip().lower()
        if is_secret_like_filename(attachment.original_file_name):
            raise AIProviderError("file_contains_secrets", "This image file name appears to reference secrets and cannot be analyzed.")
        if extension not in IMAGE_ANALYSIS_EXTENSIONS or content_type not in IMAGE_ANALYSIS_CONTENT_TYPES:
            raise AIProviderError(
                "unsupported_image_type",
                "This image type is not supported for analysis yet.",
                {"unsupported_reason": "unsupported_image_type", "extension": extension, "content_type": content_type or None},
            )
        if attachment.storage_provider != FileService.STORAGE_PROVIDER:
            raise AIProviderError("unsupported_storage_provider", "This file storage provider is not supported for image analysis yet.")
        if attachment.file_size is not None and attachment.file_size > IMAGE_ANALYSIS_MAX_BYTES:
            raise AIProviderError("image_too_large", "This image is too large for AI image analysis v1.", {"file_size": attachment.file_size})

        path = FileService.resolve_storage_path(attachment.storage_path)
        if not path.exists() or not path.is_file():
            raise AIProviderError("file_not_available", "Image content is not available for analysis.")
        actual_size = path.stat().st_size
        if actual_size > IMAGE_ANALYSIS_MAX_BYTES:
            raise AIProviderError("image_too_large", "This image is too large for AI image analysis v1.", {"file_size": actual_size})
        width, height = detect_image_dimensions(path, extension)
        if width <= 0 or height <= 0:
            raise AIProviderError("corrupted_image", "This image appears to be corrupted or unreadable.")
        if width > IMAGE_ANALYSIS_MAX_DIMENSION or height > IMAGE_ANALYSIS_MAX_DIMENSION:
            raise AIProviderError(
                "image_dimensions_too_large",
                "This image dimensions are too large for AI image analysis v1.",
                {"width": width, "height": height},
            )

        uploader_name = None
        if attachment.uploaded_by_employee_id:
            uploader_name = display_name(
                db.scalar(select(Employee).where(Employee.id == attachment.uploaded_by_employee_id, Employee.company_id == attachment.company_id))
            )
        linked_work_title = None
        linked_project_name = None
        if attachment.work_object_id:
            linked_work_title = db.scalar(
                select(WorkObject.title).where(WorkObject.id == attachment.work_object_id, WorkObject.company_id == attachment.company_id)
            )
        if attachment.project_id:
            linked_project_name = db.scalar(select(Project.name).where(Project.id == attachment.project_id, Project.company_id == attachment.company_id))

        return {
            "type": "image",
            "file_id": str(attachment.id),
            "original_file_name": safe_text(attachment.original_file_name, 255),
            "content_type": safe_text(attachment.content_type, 120),
            "extension": extension,
            "file_size": attachment.file_size,
            "upload_date": attachment.created_at.isoformat() if attachment.created_at else None,
            "uploader_display_name": uploader_name,
            "linked_entity_type": safe_text(attachment.linked_entity_type, 80),
            "linked_entity_id": str(attachment.linked_entity_id) if attachment.linked_entity_id else None,
            "linked_work_object_title": safe_text(linked_work_title, 220),
            "linked_project_name": safe_text(linked_project_name, 220),
            "description": safe_text(attachment.description, 600),
            "tags": [safe_text(tag, 80) for tag in attachment.tags[:10] if safe_text(tag, 80)],
            "image_width": width,
            "image_height": height,
            "image_metadata_included": False,
            "raw_image_bytes_included": False,
            "base64_included": False,
            "exif_gps_included": False,
            "analysis_mode": "image",
        }

    @classmethod
    def build_audio_transcription_context(
        cls,
        db: Session,
        *,
        attachment: Attachment,
    ) -> dict[str, Any]:
        extension = file_extension(attachment)
        content_type = (attachment.content_type or "").strip().lower()
        if is_secret_like_filename(attachment.original_file_name):
            raise AIProviderError("file_contains_secrets", "This audio file name appears to reference secrets and cannot be transcribed.")
        if extension not in AUDIO_TRANSCRIPTION_EXTENSIONS or content_type not in AUDIO_TRANSCRIPTION_CONTENT_TYPES:
            raise AIProviderError(
                "unsupported_audio_type",
                "This audio type is not supported for transcription yet.",
                {"unsupported_reason": "unsupported_audio_type", "extension": extension, "content_type": content_type or None},
            )
        if attachment.storage_provider != FileService.STORAGE_PROVIDER:
            raise AIProviderError("unsupported_storage_provider", "This file storage provider is not supported for audio transcription yet.")
        if attachment.file_size is not None and attachment.file_size > AUDIO_TRANSCRIPTION_MAX_BYTES:
            raise AIProviderError("audio_too_large", "This audio file is too large for AI audio transcription v1.", {"file_size": attachment.file_size})

        path = FileService.resolve_storage_path(attachment.storage_path)
        if not path.exists() or not path.is_file():
            raise AIProviderError("file_not_available", "Audio content is not available for transcription.")
        actual_size = path.stat().st_size
        if actual_size > AUDIO_TRANSCRIPTION_MAX_BYTES:
            raise AIProviderError("audio_too_large", "This audio file is too large for AI audio transcription v1.", {"file_size": actual_size})
        duration_seconds = detect_audio_duration(path, extension)
        if duration_seconds is not None and duration_seconds > AUDIO_TRANSCRIPTION_MAX_DURATION_SECONDS:
            raise AIProviderError(
                "audio_too_long",
                "This audio file is too long for AI audio transcription v1.",
                {"duration_seconds": duration_seconds},
            )

        uploader_name = None
        if attachment.uploaded_by_employee_id:
            uploader_name = display_name(
                db.scalar(select(Employee).where(Employee.id == attachment.uploaded_by_employee_id, Employee.company_id == attachment.company_id))
            )
        linked_work_title = None
        linked_project_name = None
        if attachment.work_object_id:
            linked_work_title = db.scalar(
                select(WorkObject.title).where(WorkObject.id == attachment.work_object_id, WorkObject.company_id == attachment.company_id)
            )
        if attachment.project_id:
            linked_project_name = db.scalar(select(Project.name).where(Project.id == attachment.project_id, Project.company_id == attachment.company_id))

        return {
            "type": "audio",
            "file_id": str(attachment.id),
            "original_file_name": safe_text(attachment.original_file_name, 255),
            "content_type": safe_text(attachment.content_type, 120),
            "extension": extension,
            "file_size": attachment.file_size,
            "upload_date": attachment.created_at.isoformat() if attachment.created_at else None,
            "uploader_display_name": uploader_name,
            "linked_entity_type": safe_text(attachment.linked_entity_type, 80),
            "linked_entity_id": str(attachment.linked_entity_id) if attachment.linked_entity_id else None,
            "linked_work_object_title": safe_text(linked_work_title, 220),
            "linked_project_name": safe_text(linked_project_name, 220),
            "description": safe_text(attachment.description, 600),
            "tags": [safe_text(tag, 80) for tag in attachment.tags[:10] if safe_text(tag, 80)],
            "duration_seconds": round(duration_seconds, 2) if duration_seconds is not None else None,
            "duration_detection_mode": "wav_header" if duration_seconds is not None else "not_available_without_media_probe",
            "raw_audio_bytes_included": False,
            "audio_stream_included": False,
            "local_path_included": False,
            "hidden_metadata_included": False,
            "analysis_mode": "audio_transcription",
        }

    @classmethod
    def build_safe_context(cls, db: Session, job: AIJob) -> dict[str, Any]:
        if job.input_entity_type == "work_object" and job.input_entity_id:
            work_object = get_or_404(db, WorkObject, job.input_entity_id, label="Work object")
            ensure_company(work_object, job.company_id, label="Work object")
            project_name = None
            department_name = None
            team_name = None
            assignee_name = None
            creator_name = None
            if work_object.project_id:
                project_name = db.scalar(select(Project.name).where(Project.id == work_object.project_id, Project.company_id == job.company_id))
            if work_object.department_id:
                department_name = db.scalar(select(Department.name).where(Department.id == work_object.department_id, Department.company_id == job.company_id))
            if work_object.team_id:
                team_name = db.scalar(select(Team.name).where(Team.id == work_object.team_id, Team.company_id == job.company_id))
            if work_object.assignee_employee_id:
                assignee_name = display_name(
                    db.scalar(select(Employee).where(Employee.id == work_object.assignee_employee_id, Employee.company_id == job.company_id))
                )
            if work_object.creator_employee_id:
                creator_name = display_name(
                    db.scalar(select(Employee).where(Employee.id == work_object.creator_employee_id, Employee.company_id == job.company_id))
                )
            return {
                "type": "work_object",
                "title": safe_text(work_object.title),
                "description": safe_text(work_object.description, 1600),
                "status": safe_text(work_object.status),
                "priority": safe_text(work_object.priority),
                "object_type": safe_text(work_object.object_type),
                "project_name": safe_text(project_name),
                "department_name": safe_text(department_name),
                "team_name": safe_text(team_name),
                "assignee_display_name": assignee_name,
                "creator_display_name": creator_name,
                "start_date": work_object.start_date.isoformat() if work_object.start_date else None,
                "due_date": work_object.due_date.isoformat() if work_object.due_date else None,
                "completed_at": work_object.completed_at.isoformat() if work_object.completed_at else None,
                "tags": [safe_text(tag, 80) for tag in metadata_dict({"tags": work_object.tags}).get("tags", [])[:10] if safe_text(tag, 80)],
                "custom_fields": safe_json_value(work_object.custom_fields),
            }
        if job.input_entity_type == "project" and job.input_entity_id:
            project = get_or_404(db, Project, job.input_entity_id, label="Project")
            ensure_company(project, job.company_id, label="Project")
            owner_name = None
            department_name = None
            team_name = None
            if project.owner_employee_id:
                owner_name = display_name(db.scalar(select(Employee).where(Employee.id == project.owner_employee_id, Employee.company_id == job.company_id)))
            if project.department_id:
                department_name = db.scalar(select(Department.name).where(Department.id == project.department_id, Department.company_id == job.company_id))
            if project.team_id:
                team_name = db.scalar(select(Team.name).where(Team.id == project.team_id, Team.company_id == job.company_id))
            work_objects = list(
                db.scalars(
                    select(WorkObject)
                    .where(WorkObject.company_id == job.company_id, WorkObject.project_id == project.id, WorkObject.is_active.is_(True))
                    .order_by(WorkObject.updated_at.desc())
                    .limit(100)
                ).all()
            )
            status_counts: dict[str, int] = {}
            priority_counts: dict[str, int] = {}
            overdue_count = 0
            upcoming_due_count = 0
            now = utc_now()
            open_statuses = {"assigned", "in_progress", "under_review", "blocked"}
            for work_object in work_objects:
                status_key = work_object.status or "unknown"
                priority_key = work_object.priority or "unknown"
                status_counts[status_key] = status_counts.get(status_key, 0) + 1
                priority_counts[priority_key] = priority_counts.get(priority_key, 0) + 1
                if work_object.status in open_statuses and work_object.due_date:
                    due_at = work_object.due_date
                    if due_at.tzinfo is None:
                        due_at = due_at.replace(tzinfo=now.tzinfo)
                    if due_at < now:
                        overdue_count += 1
                    elif (due_at - now).days <= 7:
                        upcoming_due_count += 1
            top_open_work_objects = [
                {
                    "title": safe_text(work_object.title, 220),
                    "status": safe_text(work_object.status),
                    "priority": safe_text(work_object.priority),
                    "due_date": work_object.due_date.isoformat() if work_object.due_date else None,
                }
                for work_object in work_objects
                if work_object.status in open_statuses
            ][:5]
            return {
                "type": "project",
                "name": safe_text(project.name),
                "description": safe_text(project.description, 1600),
                "status": safe_text(project.status),
                "priority": safe_text(project.priority),
                "progress_percent": project.progress_percent,
                "risk_level": safe_text(project.risk_level),
                "owner_display_name": owner_name,
                "department_name": safe_text(department_name),
                "team_name": safe_text(team_name),
                "start_date": project.start_date.isoformat() if project.start_date else None,
                "due_date": project.due_date.isoformat() if project.due_date else None,
                "work_object_counts_by_status": status_counts,
                "work_object_counts_by_priority": priority_counts,
                "overdue_work_count": overdue_count,
                "upcoming_due_work_count": upcoming_due_count,
                "top_open_work_objects": top_open_work_objects,
            }
        if job.input_entity_type in {"attachment", "file"} and job.input_entity_id:
            attachment = get_or_404(db, Attachment, job.input_entity_id, label="File")
            ensure_company(attachment, job.company_id, label="File")
            if attachment.is_deleted or not attachment.is_active:
                if job.job_type == "audio_transcription_safe":
                    message = "Audio content is not available for transcription."
                elif job.job_type == "image_analysis_safe":
                    message = "Image content is not available for analysis."
                else:
                    message = "File content is not available for document analysis." if job.job_type == "document_analysis_safe" else "File content is not available for AI summary."
                raise AIProviderError("file_not_available", message)
            if job.job_type == "audio_transcription_safe":
                return cls.build_audio_transcription_context(db, attachment=attachment)
            if job.job_type == "image_analysis_safe":
                return cls.build_image_analysis_context(db, attachment=attachment)
            runtime = get_ai_provider_config()
            return cls.build_file_summary_context(
                db,
                attachment=attachment,
                max_input_chars=runtime.groq_max_input_chars,
                purpose="analysis" if job.job_type == "document_analysis_safe" else "summary",
            )
        if job.input_entity_type == "company":
            company = get_or_404(db, Company, job.company_id, label="Company")
            now = utc_now()
            today = now.date()

            def counts_by(column, *filters) -> dict[str, int]:
                rows = db.execute(select(column, func.count()).where(*filters).group_by(column)).all()
                return {(safe_text(key, 80) or "unknown").lower().replace(" ", "_"): int(count or 0) for key, count in rows}

            employee_status_counts = counts_by(
                Employee.status,
                Employee.company_id == job.company_id,
                Employee.is_active.is_(True),
            )
            active_employee_count = db.scalar(
                select(func.count(Employee.id)).where(Employee.company_id == job.company_id, Employee.is_active.is_(True))
            ) or 0
            inactive_employee_count = db.scalar(
                select(func.count(Employee.id)).where(Employee.company_id == job.company_id, Employee.is_active.is_(False))
            ) or 0
            project_status_counts = counts_by(Project.status, Project.company_id == job.company_id, Project.is_active.is_(True))
            project_priority_counts = counts_by(Project.priority, Project.company_id == job.company_id, Project.is_active.is_(True))
            project_risk_counts = counts_by(Project.risk_level, Project.company_id == job.company_id, Project.is_active.is_(True))
            work_status_counts = counts_by(WorkObject.status, WorkObject.company_id == job.company_id, WorkObject.is_active.is_(True))
            work_priority_counts = counts_by(WorkObject.priority, WorkObject.company_id == job.company_id, WorkObject.is_active.is_(True))
            leave_status_counts = counts_by(LeaveRequest.status, LeaveRequest.company_id == job.company_id, LeaveRequest.is_active.is_(True))

            open_statuses = {"assigned", "in_progress", "under_review", "blocked"}
            important_priorities = {"high", "critical"}
            active_project_statuses = {"active", "on_hold", "delayed"}
            overdue_work_count = db.scalar(
                select(func.count(WorkObject.id)).where(
                    WorkObject.company_id == job.company_id,
                    WorkObject.is_active.is_(True),
                    WorkObject.status.in_(open_statuses),
                    WorkObject.due_date.is_not(None),
                    WorkObject.due_date < now,
                )
            ) or 0
            # Keep the upcoming count explicit to avoid timezone/date math surprises in SQL dialects.
            upcoming_due_work_count = sum(
                1
                for due_date, status_value in db.execute(
                    select(WorkObject.due_date, WorkObject.status).where(
                        WorkObject.company_id == job.company_id,
                        WorkObject.is_active.is_(True),
                        WorkObject.status.in_(open_statuses),
                        WorkObject.due_date.is_not(None),
                    )
                ).all()
                if due_date
                and ((due_date if due_date.tzinfo else due_date.replace(tzinfo=now.tzinfo)) >= now)
                and (((due_date if due_date.tzinfo else due_date.replace(tzinfo=now.tzinfo)) - now).days <= 7)
                and status_value in open_statuses
            )
            recently_completed_work_count = db.scalar(
                select(func.count(WorkObject.id)).where(
                    WorkObject.company_id == job.company_id,
                    WorkObject.is_active.is_(True),
                    WorkObject.completed_at.is_not(None),
                    WorkObject.completed_at >= now.replace(hour=0, minute=0, second=0, microsecond=0),
                )
            ) or 0

            top_projects = list(
                db.scalars(
                    select(Project)
                    .where(Project.company_id == job.company_id, Project.is_active.is_(True), Project.status.in_(active_project_statuses))
                    .order_by(Project.priority.desc(), Project.updated_at.desc())
                    .limit(5)
                ).all()
            )
            top_work = list(
                db.scalars(
                    select(WorkObject)
                    .where(
                        WorkObject.company_id == job.company_id,
                        WorkObject.is_active.is_(True),
                        WorkObject.status.in_(open_statuses),
                    )
                    .order_by(WorkObject.priority.desc(), WorkObject.due_date.asc().nulls_last(), WorkObject.updated_at.desc())
                    .limit(5)
                ).all()
            )
            pending_leave_count = leave_status_counts.get("pending", 0)
            approved_leave_count = leave_status_counts.get("approved", 0)
            rejected_leave_count = leave_status_counts.get("rejected", 0)
            upcoming_leave_count = db.scalar(
                select(func.count(LeaveRequest.id)).where(
                    LeaveRequest.company_id == job.company_id,
                    LeaveRequest.is_active.is_(True),
                    LeaveRequest.status == "approved",
                    LeaveRequest.start_date >= today,
                )
            ) or 0
            unread_notifications = db.scalar(
                select(func.count(Notification.id)).where(
                    Notification.company_id == job.company_id,
                    Notification.is_read.is_(False),
                    Notification.is_dismissed.is_(False),
                )
            ) or 0
            important_notifications = db.scalar(
                select(func.count(Notification.id)).where(
                    Notification.company_id == job.company_id,
                    Notification.priority.in_(("high", "urgent")),
                    Notification.is_dismissed.is_(False),
                )
            ) or 0
            recent_announcements = list(
                db.scalars(
                    select(Announcement)
                    .where(
                        Announcement.company_id == job.company_id,
                        Announcement.is_published.is_(True),
                        Announcement.is_archived.is_(False),
                    )
                    .order_by(Announcement.published_at.desc().nulls_last(), Announcement.created_at.desc())
                    .limit(5)
                ).all()
            )
            file_count = db.scalar(
                select(func.count(Attachment.id)).where(
                    Attachment.company_id == job.company_id,
                    Attachment.is_active.is_(True),
                    Attachment.is_deleted.is_(False),
                )
            ) or 0
            storage_size = db.scalar(
                select(func.coalesce(func.sum(Attachment.file_size), 0)).where(
                    Attachment.company_id == job.company_id,
                    Attachment.is_active.is_(True),
                    Attachment.is_deleted.is_(False),
                )
            ) or 0
            latest_events = list(
                db.scalars(
                    select(Event)
                    .where(Event.company_id == job.company_id)
                    .order_by(Event.created_at.desc())
                    .limit(10)
                ).all()
            )
            event_type_counts = counts_by(Event.event_type, Event.company_id == job.company_id)
            return {
                "type": "company",
                "name": safe_text(company.name),
                "industry": safe_text(company.industry),
                "size": safe_text(company.size),
                "generated_at": now.isoformat(),
                "employee_counts": {
                    "total_active": active_employee_count,
                    "inactive": inactive_employee_count,
                    "available": employee_status_counts.get("available", 0),
                    "busy": employee_status_counts.get("busy", 0),
                    "on_leave": employee_status_counts.get("on_leave", 0),
                    "by_status": employee_status_counts,
                },
                "project_counts": {
                    "total_active": sum(project_status_counts.values()),
                    "by_status": project_status_counts,
                    "by_priority": project_priority_counts,
                    "by_risk": project_risk_counts,
                },
                "top_active_projects": [
                    {
                        "name": safe_text(project.name, 220),
                        "status": safe_text(project.status),
                        "priority": safe_text(project.priority),
                        "progress_percent": project.progress_percent,
                        "risk_level": safe_text(project.risk_level),
                        "due_date": project.due_date.isoformat() if project.due_date else None,
                    }
                    for project in top_projects
                ],
                "work_object_counts": {
                    "total_active": sum(work_status_counts.values()),
                    "by_status": work_status_counts,
                    "by_priority": work_priority_counts,
                    "overdue": overdue_work_count,
                    "upcoming_due_next_7_days": upcoming_due_work_count,
                    "recently_completed_today": recently_completed_work_count,
                },
                "top_important_open_work": [
                    {
                        "title": safe_text(work_object.title, 220),
                        "status": safe_text(work_object.status),
                        "priority": safe_text(work_object.priority),
                        "due_date": work_object.due_date.isoformat() if work_object.due_date else None,
                    }
                    for work_object in top_work
                    if (work_object.priority in important_priorities or work_object.status == "blocked" or work_object.due_date)
                ][:5],
                "leave_counts": {
                    "pending": pending_leave_count,
                    "approved": approved_leave_count,
                    "rejected": rejected_leave_count,
                    "cancelled": leave_status_counts.get("cancelled", 0),
                    "upcoming_approved": upcoming_leave_count,
                },
                "notification_counts": {
                    "unread": unread_notifications,
                    "important": important_notifications,
                },
                "announcement_counts": {
                    "active": len(recent_announcements),
                    "urgent_recent": len([item for item in recent_announcements if item.priority == "urgent"]),
                },
                "recent_announcement_titles": [
                    {
                        "title": safe_text(announcement.title, 180),
                        "priority": safe_text(announcement.priority),
                        "published_at": announcement.published_at.isoformat() if announcement.published_at else None,
                    }
                    for announcement in recent_announcements
                ],
                "file_metadata_counts": {
                    "active_files": file_count,
                    "storage_bytes": int(storage_size),
                },
                "event_counts_by_type": event_type_counts,
                "latest_safe_event_summaries": [
                    {
                        "event_type": safe_text(event.event_type, 120),
                        "title": safe_text(event.title, 220),
                        "target_entity_type": safe_text(event.target_entity_type, 80),
                        "created_at": event.created_at.isoformat() if event.created_at else None,
                    }
                    for event in latest_events
                ],
            }
        return {"type": job.input_entity_type or "company"}

    @staticmethod
    def build_messages(job: AIJob, entity_context: dict[str, Any], max_input_chars: int) -> list[dict[str, str]]:
        return build_summary_messages(
            job_type=job.job_type,
            entity_context=entity_context,
            input_payload=metadata_dict(job.input_payload),
            max_input_chars=max_input_chars,
        )

    @classmethod
    def run_job(cls, db: Session, *, job: AIJob, current_user: User) -> AIJob:
        from app.services.ai_job_runner import AIJobRunner

        return AIJobRunner().run_job(db, job=job, current_user=current_user, run_mode="manual")

    @classmethod
    def fail_job(
        cls,
        db: Session,
        *,
        job: AIJob,
        current_user: User,
        error_code: str,
        error_message: str,
        metadata: dict[str, Any],
    ) -> None:
        if job.job_type in {"file_summary_safe", "document_analysis_safe", "image_analysis_safe", "audio_transcription_safe"}:
            output_payload = metadata_dict(job.output_payload)
            if job.job_type == "audio_transcription_safe":
                output_payload.update(
                    {
                        "transcript": "",
                        "transcript_summary": "",
                        "key_points": [],
                        "action_items": [],
                        "decisions_or_commitments": [],
                        "important_dates_or_numbers": [],
                        "risks_or_concerns": [],
                        "suggested_next_steps": [],
                        "limitations": [error_message[:500]],
                        "language_detected": None,
                        "duration_seconds": None,
                        "unsupported_reason": metadata.get("unsupported_reason") or error_code,
                    }
                )
            elif job.job_type == "image_analysis_safe":
                output_payload.update(
                    {
                        "image_overview": "",
                        "visible_objects_or_elements": [],
                        "possible_context": [],
                        "operational_relevance": "",
                        "risks_or_concerns": [],
                        "suggested_next_steps": [],
                        "limitations": [error_message[:500]],
                        "unsupported_reason": metadata.get("unsupported_reason") or error_code,
                    }
                )
            elif job.job_type == "document_analysis_safe":
                output_payload.update(
                    {
                        "document_overview": "",
                        "document_type_guess": "unknown",
                        "key_points": [],
                        "decisions_or_commitments": [],
                        "action_items": [],
                        "important_dates": [],
                        "important_numbers": [],
                        "risks_or_concerns": [],
                        "people_or_teams_mentioned": [],
                        "related_work_suggestions": [],
                        "suggested_next_steps": [],
                        "limitations": [error_message[:500]],
                        "truncated": bool(metadata.get("truncated", False)),
                        "unsupported_reason": metadata.get("unsupported_reason") or error_code,
                    }
                )
            else:
                output_payload.update(
                    {
                        "summary": "",
                        "document_type_guess": "unknown",
                        "key_points": [],
                        "important_dates_or_numbers": [],
                        "risks_or_concerns": [],
                        "suggested_next_steps": [],
                        "limitations": [error_message[:500]],
                        "truncated": bool(metadata.get("truncated", False)),
                        "unsupported_reason": metadata.get("unsupported_reason") or error_code,
                    }
                )
            output_payload.update(
                {
                    "provider_key": job.provider_key,
                    "provider_mode": job.provider_mode,
                    "is_mock": job.provider_mode == "mock",
                    "generated_at": utc_now().isoformat(),
                }
            )
            job.output_payload = output_payload
        job.status = "failed"
        job.failed_at = utc_now()
        job.error_message = error_message[:1000]
        job.error_code = error_code
        job.retryable = bool(error_code in {"provider_timeout", "provider_rate_limited", "provider_unavailable", "provider_unknown_error"})
        job.locked_at = None
        job.locked_by = None
        job.next_attempt_at = None
        job.metadata_json = cls.merged_job_metadata(
            job,
            {
                "error_code": error_code,
                "error_message": error_message[:500],
                "retryable": job.retryable,
                "safety_status": "failed_safely",
                "external_processing_used": False,
                "provider_metadata": metadata_dict(metadata),
            },
        )
        db.flush()
        failed_event = cls.record_job_event(
            db,
            job=job,
            current_user=current_user,
            event_type="ai_job.failed",
            title=f"AI job failed: {job.job_type}",
            description=error_message[:500],
        )
        cls.notify_requester(db, job=job, event_id=failed_event.id, success=False)

    @staticmethod
    def merged_job_metadata(job: AIJob, updates: dict[str, Any]) -> dict[str, Any]:
        current = metadata_dict(job.metadata_json)
        return {**current, **{key: value for key, value in updates.items() if value is not None}}

    @classmethod
    def cancel_job(cls, db: Session, *, job: AIJob, current_user: User) -> AIJob:
        from app.services.ai_job_runner import AIJobRunner

        return AIJobRunner().cancel_job(db, job=job, current_user=current_user)

    @classmethod
    def record_job_event(
        cls,
        db: Session,
        *,
        job: AIJob,
        current_user: User | None,
        event_type: str,
        title: str,
        description: str,
    ):
        metadata = metadata_dict(job.metadata_json)
        return EventService.record_event(
            db,
            company_id=job.company_id,
            actor_user_id=current_user.id if current_user is not None else job.requested_by_user_id,
            actor_employee_id=cls.actor_employee_id(db, current_user) if current_user is not None else job.requested_by_employee_id,
            event_type=event_type,
            title=title,
            description=description,
            target_entity_type="ai_job",
            target_entity_id=job.id,
            related_entity_type=job.input_entity_type,
            related_entity_id=job.input_entity_id,
            metadata={
                "job_type": job.job_type,
                "status": job.status,
                "priority": job.priority,
                "provider_key": job.provider_key,
                "provider_mode": job.provider_mode,
                "model_name": metadata.get("model_name"),
                "safety_status": metadata.get("safety_status"),
                "external_processing_used": bool(metadata.get("external_processing_used", False)),
                "error_code": job.error_code or metadata.get("error_code"),
                "attempts": job.attempts,
                "max_attempts": job.max_attempts,
                "retryable": job.retryable,
                "run_mode": job.run_mode,
                "input_entity_type": job.input_entity_type,
                "input_entity_id": str(job.input_entity_id) if job.input_entity_id else None,
            },
        )

    @classmethod
    def record_summary_event(cls, db: Session, *, job: AIJob, current_user: User, phase: str):
        if job.input_entity_type not in {"work_object", "project", "company", "attachment", "file"} or job.input_entity_id is None:
            return None
        if job.input_entity_type == "company":
            entity_label = "company brief"
            event_type = f"ai_brief.company.{phase}"
            title = f"AI company brief {phase}"
            description = f"A tenant-safe AI company brief was {phase}."
            target_entity_type = "company"
        elif job.input_entity_type in {"attachment", "file"}:
            is_document_analysis = job.job_type == "document_analysis_safe"
            is_image_analysis = job.job_type == "image_analysis_safe"
            is_audio_transcription = job.job_type == "audio_transcription_safe"
            if is_audio_transcription:
                event_type = f"ai_transcription.audio.{phase}"
                title = f"AI audio transcription {phase}"
                description = f"A tenant-safe AI audio transcription was {phase}."
            elif is_image_analysis:
                event_type = f"ai_analysis.image.{phase}"
                title = f"AI image analysis {phase}"
                description = f"A tenant-safe AI image analysis was {phase}."
            elif is_document_analysis:
                event_type = f"ai_analysis.document.{phase}"
                title = f"AI document analysis {phase}"
                description = f"A tenant-safe AI document analysis was {phase}."
            else:
                event_type = f"ai_summary.file.{phase}"
                title = f"AI file summary {phase}"
                description = f"A tenant-safe AI file summary was {phase}."
            target_entity_type = "attachment"
        else:
            entity_label = "work object" if job.input_entity_type == "work_object" else "project"
            event_type = f"ai_summary.{job.input_entity_type}.{phase}"
            title = f"AI {entity_label} summary {phase}"
            description = f"A tenant-safe AI {entity_label} summary was {phase}."
            target_entity_type = job.input_entity_type
        metadata = metadata_dict(job.metadata_json)
        output_payload = metadata_dict(job.output_payload)
        return EventService.record_event(
            db,
            company_id=job.company_id,
            actor_user_id=current_user.id,
            actor_employee_id=cls.actor_employee_id(db, current_user),
            event_type=event_type,
            title=title,
            description=description,
            target_entity_type=target_entity_type,
            target_entity_id=job.input_entity_id,
            related_entity_type="ai_job",
            related_entity_id=job.id,
            metadata={
                "ai_job_id": str(job.id),
                "entity_type": "file" if job.input_entity_type in {"attachment", "file"} else job.input_entity_type,
                "entity_id": str(job.input_entity_id),
                "job_type": job.job_type,
                "status": job.status,
                "provider_key": job.provider_key,
                "provider_mode": job.provider_mode,
                "model_name": metadata.get("model_name"),
                "safety_status": metadata.get("safety_status"),
                "external_processing_used": bool(metadata.get("external_processing_used", False)),
                "error_code": metadata.get("error_code"),
                "truncated": bool(output_payload.get("truncated", False)) if job.job_type in {"file_summary_safe", "document_analysis_safe"} else None,
                "unsupported_reason": output_payload.get("unsupported_reason")
                if job.job_type in {"file_summary_safe", "document_analysis_safe", "image_analysis_safe", "audio_transcription_safe"}
                else None,
            },
        )

    @classmethod
    def notify_requester(cls, db: Session, *, job: AIJob, event_id: UUID, success: bool, cancelled: bool = False) -> None:
        if cancelled:
            title = "AI job cancelled"
            message = f"{job.job_type} was cancelled."
            notification_type = "ai_job.cancelled"
            priority = "normal"
        else:
            title = "AI job completed" if success else "AI job failed"
            message = f"{job.job_type} {'completed' if success else 'failed safely'}."
            notification_type = "ai_job.succeeded" if success else "ai_job.failed"
            priority = "normal" if success else "high"
        NotificationService.create_notification(
            db,
            company_id=job.company_id,
            recipient_user_id=job.requested_by_user_id,
            recipient_employee_id=job.requested_by_employee_id,
            event_id=event_id,
            target_entity_type="ai_job",
            target_entity_id=job.id,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            action_url="#/settings",
            metadata={"job_type": job.job_type, "provider_mode": job.provider_mode, "status": job.status},
        )

    @classmethod
    def capabilities(cls, db: Session, *, company_id: UUID, current_user: User) -> AICapabilitiesRead:
        status_read = cls.provider_status(db, company_id=company_id, current_user=current_user, require_admin=False)
        return AICapabilitiesRead(
            company_id=company_id,
            provider_key=status_read.provider_key,
            provider_mode=status_read.provider_mode,
            real_ai_connected=status_read.real_ai_connected,
            external_calls_enabled=status_read.external_processing_enabled and status_read.external_processing_allowed,
            capabilities=CAPABILITY_DEFINITIONS,
            message=status_read.message,
        )

    @classmethod
    def safety_settings(cls, db: Session, *, company_id: UUID, current_user: User) -> AISafetySettingsRead:
        ensure_company_access(current_user, company_id)
        ensure_role(current_user, OWNER_ADMIN_ROLES)
        company = get_or_404(db, Company, company_id, label="Company")
        settings = cls.company_ai_settings(company)
        return AISafetySettingsRead(company_id=company_id, **settings)

    @classmethod
    def update_safety_settings(
        cls,
        db: Session,
        *,
        company_id: UUID,
        payload: AISafetySettingsUpdate,
        current_user: User,
    ) -> AISafetySettingsRead:
        ensure_company_access(current_user, company_id)
        ensure_role(current_user, OWNER_ADMIN_ROLES)
        company = get_or_404(db, Company, company_id, label="Company")
        current_settings = cls.company_ai_settings(company)
        settings_json = dict(metadata_dict(company.settings_json))
        updated = dict(metadata_dict(settings_json.get(COMPANY_AI_SETTINGS_KEY)))
        if payload.ai_enabled is not None:
            updated["ai_enabled"] = payload.ai_enabled
        if payload.external_ai_processing_allowed is not None:
            updated["external_ai_processing_allowed"] = payload.external_ai_processing_allowed
        if payload.default_provider_mode is not None:
            updated["default_provider_mode"] = normalize_provider_mode(payload.default_provider_mode)
        if payload.allowed_ai_job_types is not None:
            updated["allowed_ai_job_types"] = sorted({item for item in payload.allowed_ai_job_types if item in AI_JOB_TYPES})
        if payload.max_monthly_ai_jobs is not None:
            updated["max_monthly_ai_jobs"] = payload.max_monthly_ai_jobs
        if payload.metadata is not None:
            cls.ensure_payload_safe(payload.metadata)
            updated["metadata"] = metadata_dict(payload.metadata)

        settings_json[COMPANY_AI_SETTINGS_KEY] = updated
        company.settings_json = settings_json
        db.flush()

        next_settings = cls.company_ai_settings(company)
        cls.record_settings_event(db, company_id=company_id, current_user=current_user, old=current_settings, new=next_settings)
        return AISafetySettingsRead(company_id=company_id, **next_settings)

    @classmethod
    def record_settings_event(
        cls,
        db: Session,
        *,
        company_id: UUID,
        current_user: User,
        old: dict[str, Any],
        new: dict[str, Any],
    ) -> None:
        EventService.record_event(
            db,
            company_id=company_id,
            actor_user_id=current_user.id,
            actor_employee_id=cls.actor_employee_id(db, current_user),
            event_type="ai_settings.updated",
            title="AI safety settings updated",
            description="AI provider and external processing safety settings were updated.",
            target_entity_type="company",
            target_entity_id=company_id,
            metadata={
                "ai_enabled": new.get("ai_enabled"),
                "external_ai_processing_allowed": new.get("external_ai_processing_allowed"),
                "default_provider_mode": new.get("default_provider_mode"),
                "allowed_job_types_count": len(new.get("allowed_ai_job_types", [])),
            },
        )
        if old.get("external_ai_processing_allowed") != new.get("external_ai_processing_allowed"):
            event_type = "ai_external_processing.enabled" if new.get("external_ai_processing_allowed") else "ai_external_processing.disabled"
            event = EventService.record_event(
                db,
                company_id=company_id,
                actor_user_id=current_user.id,
                actor_employee_id=cls.actor_employee_id(db, current_user),
                event_type=event_type,
                title="External AI processing updated",
                description="External AI processing was explicitly toggled by an owner/admin.",
                target_entity_type="company",
                target_entity_id=company_id,
                metadata={"enabled": bool(new.get("external_ai_processing_allowed"))},
            )
            NotificationService.create_notification(
                db,
                company_id=company_id,
                recipient_user_id=current_user.id,
                event_id=event.id,
                target_entity_type="company",
                target_entity_id=company_id,
                notification_type=event_type,
                title="External AI processing updated",
                message="Your AI external-processing safety setting was updated.",
                priority="high" if new.get("external_ai_processing_allowed") else "normal",
                action_url="#/settings",
                metadata={"enabled": bool(new.get("external_ai_processing_allowed"))},
            )

    @classmethod
    def provider_status(
        cls,
        db: Session,
        *,
        company_id: UUID,
        current_user: User,
        require_admin: bool = True,
    ) -> AIProviderStatusRead:
        ensure_company_access(current_user, company_id)
        if require_admin:
            ensure_role(current_user, OWNER_ADMIN_ROLES)
        company = get_or_404(db, Company, company_id, label="Company")
        company_settings = cls.company_ai_settings(company)
        runtime = get_ai_provider_config()
        provider_mode = normalize_provider_mode(company_settings.get("default_provider_mode") or runtime.provider_mode)
        configured = provider_mode in {"mock", "disabled"} or (provider_mode == "groq" and runtime.groq_configured)
        model_name = runtime.groq_model if provider_mode == "groq" else ("mock-deterministic" if provider_mode == "mock" else None)
        external_enabled = runtime.external_processing_enabled
        external_allowed = bool(company_settings["external_ai_processing_allowed"])
        real_connected = (
            provider_mode == "groq"
            and runtime.groq_configured
            and external_enabled
            and external_allowed
            and bool(company_settings["ai_enabled"])
        )
        if provider_mode == "groq" and not runtime.groq_configured:
            message = "Groq is selected but not configured. Add GROQ_API_KEY locally; the key is never exposed by the API."
        elif provider_mode == "groq" and not external_allowed:
            message = "Groq is configured as the real provider, but company external AI processing is off."
        elif provider_mode == "groq" and not external_enabled:
            message = "Groq is configured, but global external AI processing is off."
        elif provider_mode == "mock":
            message = "Mock AI provider is active. Real external AI calls are not made."
        elif provider_mode == "disabled":
            message = "AI provider mode is disabled."
        else:
            message = "Future provider mode is reserved and not implemented yet."
        supported_real_job_types = sorted(REAL_AI_JOB_TYPES - {"image_analysis_safe", "audio_transcription_safe"})
        return AIProviderStatusRead(
            company_id=company_id,
            provider_key=cls.provider_key_for_mode(provider_mode),
            provider_mode=provider_mode,
            configured=configured,
            model_name=model_name,
            external_processing_enabled=external_enabled,
            external_processing_allowed=external_allowed,
            ai_enabled=bool(company_settings["ai_enabled"]),
            real_ai_connected=real_connected,
            supported_real_job_types=supported_real_job_types,
            supported_mock_job_types=sorted(MOCK_AI_JOB_TYPES),
            message=message,
        )


ai_service = AIService()
