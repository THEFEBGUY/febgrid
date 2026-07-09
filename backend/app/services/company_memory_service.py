import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.permissions import MANAGER_ROLES, OWNER_ADMIN_ROLES, ensure_company_access
from app.models.ai_job import AIJob
from app.models.attachment import Attachment
from app.models.company_memory import CompanyMemory
from app.models.department import Department
from app.models.employee import Employee
from app.models.event import Event
from app.models.project import Project, ProjectMember
from app.models.team import Team
from app.models.user import User
from app.models.work_dna import WorkDNASnapshot
from app.models.work_object import WorkObject
from app.schemas.company_memory import (
    MEMORY_IMPORTANCE,
    MEMORY_STATUSES,
    MEMORY_TYPES,
    MEMORY_VISIBILITIES,
    SCOPE_TYPES,
    SOURCE_TYPES,
    CompanyMemoryCreate,
    CompanyMemoryFromAIJobPayload,
    CompanyMemoryUpdate,
)
from app.services.event_service import EventService
from app.services.notification_service import NotificationService

SECRET_VALUE_RE = re.compile(
    r"(?i)\b(api[_-]?key|password|passwd|token|secret|bearer|private[_-]?key|access[_-]?token)\b\s*[:=]\s*['\"]?[^,\s;'\"}]{6,}"
)
LONG_SECRET_RE = re.compile(r"\b[A-Za-z0-9_\-]{36,}\b")
MAX_MEMORY_TEXT_CHARS = 6000


def metadata_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def normalize_text(value: str | None, *, max_chars: int = MAX_MEMORY_TEXT_CHARS) -> str | None:
    if value is None:
        return None
    compact = "\n".join(line.rstrip() for line in str(value).splitlines()).strip()
    if not compact:
        return None
    compact = SECRET_VALUE_RE.sub(lambda match: f"{match.group(1)}=[REDACTED]", compact)
    compact = LONG_SECRET_RE.sub("[REDACTED_LONG_VALUE]", compact)
    if len(compact) > max_chars:
        return f"{compact[:max_chars].rstrip()}\n\n[Trimmed for Company Memory safety.]"
    return compact


def sanitize_metadata(value: Any, *, depth: int = 0) -> dict[str, Any]:
    if depth > 2 or not isinstance(value, dict):
        return {}
    blocked_keys = {
        "api_key",
        "apikey",
        "authorization",
        "bearer",
        "env",
        "file_content",
        "input_payload",
        "invite_token",
        "password",
        "private_key",
        "prompt",
        "raw_prompt",
        "secret",
        "storage_path",
        "system_prompt",
        "token",
    }
    sanitized: dict[str, Any] = {}
    for key, raw_value in value.items():
        key_text = str(key)
        if key_text.strip().lower() in blocked_keys:
            continue
        if isinstance(raw_value, dict):
            sanitized[key_text] = sanitize_metadata(raw_value, depth=depth + 1)
        elif isinstance(raw_value, list):
            sanitized[key_text] = [
                sanitize_metadata(item, depth=depth + 1) if isinstance(item, dict) else str(item)[:240]
                for item in raw_value[:12]
            ]
        elif isinstance(raw_value, (str, int, float, bool)) or raw_value is None:
            sanitized[key_text] = normalize_text(str(raw_value), max_chars=500) if isinstance(raw_value, str) else raw_value
    return sanitized


def ensure_choice(value: str, allowed: set[str], label: str) -> str:
    normalized = value.strip().lower()
    if normalized not in allowed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Invalid {label}")
    return normalized


def linked_employee(db: Session, user: User | None) -> Employee | None:
    if user is None:
        return None
    return db.scalar(
        select(Employee).where(
            Employee.company_id == user.company_id,
            Employee.user_id == user.id,
            Employee.is_active.is_(True),
        )
    )


def actor_employee_id(db: Session, user: User | None) -> UUID | None:
    employee = linked_employee(db, user)
    return employee.id if employee is not None else None


def owner_admin_required(user: User | None) -> None:
    if user is None or user.role not in OWNER_ADMIN_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner or admin access required")


def ensure_scope_allowed_for_role(*, scope_type: str, scope_id: UUID | None, current_user: User | None) -> None:
    if scope_type not in {"company", "unknown"} and scope_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Memory scope id is required")
    if scope_type == "company" and (current_user is None or current_user.role not in OWNER_ADMIN_ROLES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company-wide memory requires owner or admin access")


def memory_event_metadata(memory: CompanyMemory, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "memory_id": str(memory.id),
        "memory_type": memory.memory_type,
        "scope_type": memory.scope_type,
        "scope_id": str(memory.scope_id) if memory.scope_id else None,
        "source_type": memory.source_type,
        "source_id": str(memory.source_id) if memory.source_id else None,
        "source_ai_job_id": str(memory.source_ai_job_id) if memory.source_ai_job_id else None,
        "status": memory.status,
        "importance": memory.importance,
    }
    if extra:
        payload.update(sanitize_metadata(extra))
    return payload


class CompanyMemoryService:
    @staticmethod
    def visible_statement(db: Session, *, company_id: UUID, current_user: User | None):
        statement = select(CompanyMemory).where(CompanyMemory.company_id == company_id)
        if current_user is None or current_user.role in OWNER_ADMIN_ROLES:
            return statement
        employee = linked_employee(db, current_user)
        creator_conditions: list[Any] = [CompanyMemory.created_by_user_id == current_user.id]
        if employee is not None:
            creator_conditions.append(CompanyMemory.created_by_employee_id == employee.id)
        approved_visible = and_(
            CompanyMemory.status == "approved",
            CompanyMemory.visibility.in_(["company", "manager_hr"] if current_user.role in MANAGER_ROLES else ["company"]),
        )
        return statement.where(or_(approved_visible, *creator_conditions))

    @staticmethod
    def list_memories(
        db: Session,
        *,
        company_id: UUID,
        current_user: User | None,
        status_filter: str | None = None,
        memory_type: str | None = None,
        scope_type: str | None = None,
        source_type: str | None = None,
        source_id: UUID | None = None,
        importance: str | None = None,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CompanyMemory]:
        ensure_company_access(current_user, company_id)
        statement = CompanyMemoryService.visible_statement(db, company_id=company_id, current_user=current_user)
        if status_filter:
            statement = statement.where(CompanyMemory.status == ensure_choice(status_filter, MEMORY_STATUSES, "memory status"))
        if memory_type:
            statement = statement.where(CompanyMemory.memory_type == ensure_choice(memory_type, MEMORY_TYPES, "memory type"))
        if scope_type:
            statement = statement.where(CompanyMemory.scope_type == ensure_choice(scope_type, SCOPE_TYPES, "scope type"))
        if source_type:
            statement = statement.where(CompanyMemory.source_type == ensure_choice(source_type, SOURCE_TYPES, "source type"))
        if source_id:
            statement = statement.where(CompanyMemory.source_id == source_id)
        if importance:
            statement = statement.where(CompanyMemory.importance == ensure_choice(importance, MEMORY_IMPORTANCE, "importance"))
        if query and query.strip():
            term = f"%{query.strip()}%"
            statement = statement.where(
                or_(
                    CompanyMemory.title.ilike(term),
                    CompanyMemory.content.ilike(term),
                    CompanyMemory.summary.ilike(term),
                    CompanyMemory.memory_type.ilike(term),
                    CompanyMemory.scope_type.ilike(term),
                )
            )
        capped_limit = min(max(limit, 1), 100)
        return list(db.scalars(statement.order_by(CompanyMemory.updated_at.desc()).offset(max(offset, 0)).limit(capped_limit)).all())

    @staticmethod
    def get_memory(db: Session, *, memory_id: UUID, company_id: UUID, current_user: User | None) -> CompanyMemory:
        ensure_company_access(current_user, company_id)
        memory = db.scalar(
            CompanyMemoryService.visible_statement(db, company_id=company_id, current_user=current_user).where(CompanyMemory.id == memory_id)
        )
        if memory is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company memory not found")
        return memory

    @staticmethod
    def validate_scope_entity(db: Session, *, company_id: UUID, scope_type: str, scope_id: UUID | None, current_user: User | None) -> None:
        if scope_id is None:
            return
        model_by_scope = {
            "project": Project,
            "work_object": WorkObject,
            "team": Team,
            "department": Department,
            "file": Attachment,
            "employee_self": Employee,
        }
        if scope_type == "company":
            if scope_id != company_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company scope not found")
            return
        model = model_by_scope.get(scope_type)
        if model is None:
            return
        record = db.get(model, scope_id)
        if record is None or record.company_id != company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory scope not found")
        if current_user is not None and current_user.role == "employee":
            CompanyMemoryService.ensure_employee_scope_access(db, company_id=company_id, scope_type=scope_type, scope_id=scope_id, user=current_user)

    @staticmethod
    def ensure_employee_scope_access(db: Session, *, company_id: UUID, scope_type: str, scope_id: UUID, user: User) -> None:
        employee = linked_employee(db, user)
        if scope_type == "employee_self":
            if employee is None or employee.id != scope_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Memory scope not allowed")
            return
        if scope_type == "work_object":
            work = db.get(WorkObject, scope_id)
            if (
                work is None
                or work.company_id != company_id
                or not (work.creator_user_id == user.id or (employee is not None and work.assignee_employee_id == employee.id))
            ):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Memory scope not allowed")
            return
        if scope_type == "project" and employee is not None:
            project = db.get(Project, scope_id)
            member = db.scalar(
                select(ProjectMember).where(
                    ProjectMember.company_id == company_id,
                    ProjectMember.project_id == scope_id,
                    ProjectMember.employee_id == employee.id,
                    ProjectMember.is_active.is_(True),
                )
            )
            if project is None or project.company_id != company_id or (project.owner_employee_id != employee.id and member is None):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Memory scope not allowed")
            return
        if scope_type == "file" and employee is not None:
            attachment = db.get(Attachment, scope_id)
            if attachment is None or attachment.company_id != company_id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Memory scope not allowed")
            if attachment.uploaded_by_employee_id == employee.id or attachment.uploaded_by_user_id == user.id:
                return
            if attachment.work_object_id is not None:
                CompanyMemoryService.ensure_employee_scope_access(
                    db,
                    company_id=company_id,
                    scope_type="work_object",
                    scope_id=attachment.work_object_id,
                    user=user,
                )
                return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Memory scope not allowed")

    @staticmethod
    def validate_source(db: Session, *, company_id: UUID, source_type: str | None, source_id: UUID | None, source_ai_job_id: UUID | None) -> AIJob | None:
        source_job: AIJob | None = None
        if source_ai_job_id is not None:
            source_job = db.get(AIJob, source_ai_job_id)
            if source_job is None or source_job.company_id != company_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI source not found")
        if source_type is None or source_id is None:
            return source_job
        source_type = ensure_choice(source_type, SOURCE_TYPES, "source type")
        if source_type in {"ai_job", "company_brief"}:
            if source_type == "ai_job":
                source_job = db.get(AIJob, source_id)
                if source_job is None or source_job.company_id != company_id:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI source not found")
            elif source_id != company_id:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company brief source not found")
            return source_job
        model_by_source = {
            "work_object": WorkObject,
            "work_object_summary": WorkObject,
            "project": Project,
            "project_summary": Project,
            "attachment": Attachment,
            "file": Attachment,
            "file_summary": Attachment,
            "document_analysis": Attachment,
            "image_analysis": Attachment,
            "audio_transcription": Attachment,
            "work_dna": WorkDNASnapshot,
            "event": Event,
        }
        model = model_by_source.get(source_type)
        if model is None:
            return source_job
        record = db.get(model, source_id)
        if record is None or record.company_id != company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory source not found")
        return source_job

    @classmethod
    def create_memory(cls, db: Session, *, payload: CompanyMemoryCreate, current_user: User | None) -> CompanyMemory:
        ensure_company_access(current_user, payload.company_id)
        if current_user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        ensure_scope_allowed_for_role(scope_type=payload.scope_type, scope_id=payload.scope_id, current_user=current_user)
        cls.validate_scope_entity(
            db,
            company_id=payload.company_id,
            scope_type=payload.scope_type,
            scope_id=payload.scope_id,
            current_user=current_user,
        )
        cls.validate_source(
            db,
            company_id=payload.company_id,
            source_type=payload.source_type,
            source_id=payload.source_id,
            source_ai_job_id=payload.source_ai_job_id,
        )
        requested_status = payload.status
        if requested_status == "approved":
            owner_admin_required(current_user)
        elif current_user.role not in OWNER_ADMIN_ROLES:
            requested_status = "suggested"
        if requested_status == "suggested" and (
            (payload.source_type and payload.source_type != "manual" and payload.source_id is not None)
            or payload.source_ai_job_id is not None
        ):
            duplicate_conditions = [
                CompanyMemory.company_id == payload.company_id,
                CompanyMemory.status == "suggested",
                CompanyMemory.created_by_user_id == current_user.id,
            ]
            if payload.source_ai_job_id is not None:
                duplicate_conditions.append(CompanyMemory.source_ai_job_id == payload.source_ai_job_id)
            else:
                duplicate_conditions.extend(
                    [
                        CompanyMemory.source_type == payload.source_type,
                        CompanyMemory.source_id == payload.source_id,
                    ]
                )
            existing_suggestion = db.scalar(
                select(CompanyMemory)
                .where(*duplicate_conditions)
                .order_by(CompanyMemory.created_at.desc())
                .limit(1)
            )
            if existing_suggestion is not None:
                return existing_suggestion
        memory = CompanyMemory(
            company_id=payload.company_id,
            title=normalize_text(payload.title, max_chars=180) or "Company memory",
            memory_type=payload.memory_type,
            scope_type=payload.scope_type,
            scope_id=payload.scope_id,
            source_type=payload.source_type or "manual",
            source_id=payload.source_id,
            source_ai_job_id=payload.source_ai_job_id,
            content=normalize_text(payload.content) or "No content recorded.",
            summary=normalize_text(payload.summary, max_chars=1000),
            tags=[tag[:60] for tag in payload.tags[:12]],
            importance=payload.importance,
            confidence=payload.confidence,
            status=requested_status,
            visibility=payload.visibility,
            created_by_user_id=current_user.id,
            created_by_employee_id=actor_employee_id(db, current_user),
            metadata_json=sanitize_metadata(payload.metadata),
        )
        if requested_status == "approved":
            memory.approved_by_user_id = current_user.id
            memory.approved_at = datetime.now(timezone.utc)
        db.add(memory)
        db.flush()
        cls.record_memory_event(db, memory=memory, current_user=current_user, event_type="company_memory.created")
        if memory.status == "suggested":
            cls.record_memory_event(db, memory=memory, current_user=current_user, event_type="company_memory.suggested")
            cls.notify_suggestion_reviewers(db, memory=memory, current_user=current_user)
        if memory.source_type and (memory.source_id or memory.source_ai_job_id):
            cls.record_memory_event(db, memory=memory, current_user=current_user, event_type="company_memory.linked_to_source")
        return memory

    @classmethod
    def create_from_ai_job(
        cls,
        db: Session,
        *,
        ai_job_id: UUID,
        payload: CompanyMemoryFromAIJobPayload,
        current_user: User | None,
    ) -> CompanyMemory:
        ensure_company_access(current_user, payload.company_id)
        if current_user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        job = db.get(AIJob, ai_job_id)
        if job is None or job.company_id != payload.company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI job not found")
        if job.status != "succeeded" or not metadata_dict(job.output_payload):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="AI job has no successful safe output to save")
        if current_user.role not in MANAGER_ROLES and job.requested_by_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="AI job is not visible")
        source = cls.source_from_job(job)
        cls.validate_scope_entity(
            db,
            company_id=payload.company_id,
            scope_type=source["scope_type"],
            scope_id=source["scope_id"],
            current_user=current_user,
        )
        if source["scope_type"] == "company" and current_user.role not in OWNER_ADMIN_ROLES:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company-wide memory requires owner or admin access")
        approve_now = payload.approve_now and current_user.role in OWNER_ADMIN_ROLES
        memory_payload = CompanyMemoryCreate(
            company_id=payload.company_id,
            title=payload.title or source["title"],
            memory_type=payload.memory_type or source["memory_type"],
            scope_type=source["scope_type"],
            scope_id=source["scope_id"],
            source_type=source["source_type"],
            source_id=source["source_id"],
            source_ai_job_id=job.id,
            content=cls.content_from_ai_output(job),
            summary=cls.summary_from_ai_output(job),
            tags=[*payload.tags, source["memory_type"], "ai_summary"][:12],
            importance=payload.importance,
            confidence=cls.confidence_from_ai_output(job),
            status="approved" if approve_now else "suggested",
            visibility=payload.visibility,
            metadata={
                **sanitize_metadata(payload.metadata),
                "ai_job_id": str(job.id),
                "job_type": job.job_type,
                "provider_mode": job.provider_mode,
                "provider_key": job.provider_key,
                "model_name": metadata_dict(job.output_payload).get("model_name") or metadata_dict(job.metadata_json).get("model_name"),
            },
        )
        return cls.create_memory(db, payload=memory_payload, current_user=current_user)

    @staticmethod
    def source_from_job(job: AIJob) -> dict[str, Any]:
        entity_type = (job.input_entity_type or "").strip().lower()
        job_type = job.job_type
        if job_type in {"company_brief_safe", "company_brief_mock"} or entity_type == "company":
            return {
                "memory_type": "company_brief",
                "scope_type": "company",
                "scope_id": job.company_id,
                "source_type": "company_brief",
                "source_id": job.company_id,
                "title": "Company executive brief memory",
            }
        if entity_type == "project" or job_type in {"project_summary_safe", "project_summary_mock"}:
            return {
                "memory_type": "project_context",
                "scope_type": "project",
                "scope_id": job.input_entity_id,
                "source_type": "project_summary",
                "source_id": job.input_entity_id,
                "title": "Project summary memory",
            }
        if entity_type in {"file", "attachment"} or job_type in {"file_summary_safe", "file_summary_mock", "document_analysis_safe", "image_analysis_safe", "audio_transcription_safe"}:
            is_document_analysis = job_type == "document_analysis_safe"
            is_image_analysis = job_type == "image_analysis_safe"
            is_audio_transcription = job_type == "audio_transcription_safe"
            return {
                "memory_type": "file_insight",
                "scope_type": "file",
                "scope_id": job.input_entity_id,
                "source_type": "audio_transcription" if is_audio_transcription else "image_analysis" if is_image_analysis else "document_analysis" if is_document_analysis else "file_summary",
                "source_id": job.input_entity_id,
                "title": "Audio transcription memory" if is_audio_transcription else "Image analysis memory" if is_image_analysis else "Document analysis memory" if is_document_analysis else "File insight memory",
            }
        return {
            "memory_type": "work_context",
            "scope_type": "work_object",
            "scope_id": job.input_entity_id,
            "source_type": "work_object_summary",
            "source_id": job.input_entity_id,
            "title": "Work summary memory",
        }

    @staticmethod
    def content_from_ai_output(job: AIJob) -> str:
        output = metadata_dict(job.output_payload)
        lines: list[str] = []
        primary = (
            output.get("executive_summary")
            or output.get("summary")
            or output.get("document_overview")
            or output.get("image_overview")
            or output.get("transcript_summary")
        )
        if primary:
            lines.append(str(primary))
        sections = [
            ("Operational highlights", output.get("operational_highlights")),
            ("Key points", output.get("key_points")),
            ("Decisions or commitments", output.get("decisions_or_commitments")),
            ("Action items", output.get("action_items")),
            ("Important dates", output.get("important_dates")),
            ("Important dates or numbers", output.get("important_dates_or_numbers")),
            ("Important numbers", output.get("important_numbers")),
            ("Transcript summary", output.get("transcript_summary")),
            ("Transcript", output.get("transcript")),
            ("Visible objects or elements", output.get("visible_objects_or_elements")),
            ("Possible context", output.get("possible_context")),
            ("Operational relevance", output.get("operational_relevance")),
            ("Project overview", output.get("project_overview")),
            ("Work overview", output.get("work_overview")),
            ("People overview", output.get("people_overview")),
            ("Leave overview", output.get("leave_overview")),
            ("Blockers or risks", output.get("risks_or_blockers") or output.get("blockers_or_risks") or output.get("risks_or_concerns")),
            ("People or teams mentioned", output.get("people_or_teams_mentioned")),
            ("Related work suggestions", output.get("related_work_suggestions")),
            ("Attention items", output.get("attention_items")),
            ("Suggested next steps", output.get("suggested_next_actions") or output.get("suggested_next_steps")),
            ("Limitations", output.get("limitations")),
        ]
        for title, value in sections:
            if isinstance(value, list) and value:
                items = [str(item).strip() for item in value if str(item).strip()]
                if items:
                    lines.append(f"{title}:\n" + "\n".join(f"- {item}" for item in items[:8]))
            elif isinstance(value, str) and value.strip():
                lines.append(f"{title}: {value.strip()}")
        return normalize_text("\n\n".join(lines)) or "AI summary output saved as memory suggestion."

    @staticmethod
    def summary_from_ai_output(job: AIJob) -> str | None:
        output = metadata_dict(job.output_payload)
        return normalize_text(
            str(
                output.get("executive_summary")
                or output.get("summary")
                or output.get("document_overview")
                or output.get("image_overview")
                or output.get("transcript_summary")
                or ""
            ),
            max_chars=1000,
        )

    @staticmethod
    def confidence_from_ai_output(job: AIJob) -> float | None:
        confidence = metadata_dict(job.output_payload).get("confidence")
        if isinstance(confidence, (int, float)):
            return float(confidence)
        return None

    @classmethod
    def update_memory(
        cls,
        db: Session,
        *,
        memory_id: UUID,
        company_id: UUID,
        payload: CompanyMemoryUpdate,
        current_user: User | None,
    ) -> CompanyMemory:
        memory = cls.get_memory(db, memory_id=memory_id, company_id=company_id, current_user=current_user)
        if current_user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
        if current_user.role not in OWNER_ADMIN_ROLES and not (
            memory.created_by_user_id == current_user.id and memory.status in {"draft", "suggested"}
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Memory update not allowed")
        updates = payload.model_dump(exclude_unset=True, by_alias=False)
        next_scope_type = updates.get("scope_type") or memory.scope_type
        next_scope_id = updates.get("scope_id") if "scope_id" in updates else memory.scope_id
        ensure_scope_allowed_for_role(scope_type=next_scope_type, scope_id=next_scope_id, current_user=current_user)
        if "scope_type" in updates or "scope_id" in updates:
            cls.validate_scope_entity(
                db,
                company_id=company_id,
                scope_type=updates.get("scope_type") or memory.scope_type,
                scope_id=updates.get("scope_id") if "scope_id" in updates else memory.scope_id,
                current_user=current_user,
            )
        for field, value in updates.items():
            if field == "metadata":
                memory.metadata_json = sanitize_metadata(value)
            elif field == "content":
                memory.content = normalize_text(value) or memory.content
            elif field == "summary":
                memory.summary = normalize_text(value, max_chars=1000)
            elif field == "title":
                memory.title = normalize_text(value, max_chars=180) or memory.title
            elif field == "tags":
                memory.tags = [str(tag).strip()[:60] for tag in safe_list(value) if str(tag).strip()][:12]
            else:
                setattr(memory, field, value)
        db.flush()
        cls.record_memory_event(db, memory=memory, current_user=current_user, event_type="company_memory.updated")
        return memory

    @classmethod
    def approve_memory(cls, db: Session, *, memory_id: UUID, company_id: UUID, current_user: User | None) -> CompanyMemory:
        owner_admin_required(current_user)
        memory = cls.get_memory(db, memory_id=memory_id, company_id=company_id, current_user=current_user)
        memory.status = "approved"
        memory.approved_by_user_id = current_user.id if current_user is not None else None
        memory.approved_at = datetime.now(timezone.utc)
        memory.rejected_by_user_id = None
        memory.rejected_at = None
        db.flush()
        cls.record_memory_event(db, memory=memory, current_user=current_user, event_type="company_memory.approved")
        cls.notify_requester(db, memory=memory, current_user=current_user, approved=True)
        return memory

    @classmethod
    def reject_memory(cls, db: Session, *, memory_id: UUID, company_id: UUID, current_user: User | None, note: str | None = None) -> CompanyMemory:
        owner_admin_required(current_user)
        memory = cls.get_memory(db, memory_id=memory_id, company_id=company_id, current_user=current_user)
        memory.status = "rejected"
        memory.rejected_by_user_id = current_user.id if current_user is not None else None
        memory.rejected_at = datetime.now(timezone.utc)
        if note:
            metadata = metadata_dict(memory.metadata_json)
            metadata["rejection_note"] = normalize_text(note, max_chars=500)
            memory.metadata_json = sanitize_metadata(metadata)
        db.flush()
        cls.record_memory_event(db, memory=memory, current_user=current_user, event_type="company_memory.rejected")
        cls.notify_requester(db, memory=memory, current_user=current_user, approved=False)
        return memory

    @classmethod
    def archive_memory(cls, db: Session, *, memory_id: UUID, company_id: UUID, current_user: User | None) -> CompanyMemory:
        owner_admin_required(current_user)
        memory = cls.get_memory(db, memory_id=memory_id, company_id=company_id, current_user=current_user)
        memory.status = "archived"
        memory.archived_by_user_id = current_user.id if current_user is not None else None
        memory.archived_at = datetime.now(timezone.utc)
        db.flush()
        cls.record_memory_event(db, memory=memory, current_user=current_user, event_type="company_memory.archived")
        return memory

    @staticmethod
    def record_memory_event(db: Session, *, memory: CompanyMemory, current_user: User | None, event_type: str) -> None:
        actor_employee = actor_employee_id(db, current_user)
        title_by_event = {
            "company_memory.created": "Company memory created",
            "company_memory.suggested": "Company memory suggested",
            "company_memory.approved": "Company memory approved",
            "company_memory.rejected": "Company memory rejected",
            "company_memory.updated": "Company memory updated",
            "company_memory.archived": "Company memory archived",
            "company_memory.linked_to_source": "Company memory linked to source",
        }
        EventService.record_event(
            db,
            company_id=memory.company_id,
            actor_user_id=current_user.id if current_user is not None else None,
            actor_employee_id=actor_employee,
            event_type=event_type,
            title=title_by_event.get(event_type, "Company memory changed"),
            description=f"{memory.title} / {memory.memory_type}",
            target_entity_type="company_memory",
            target_entity_id=memory.id,
            related_entity_type=memory.source_type,
            related_entity_id=memory.source_id,
            metadata=memory_event_metadata(memory),
        )

    @staticmethod
    def notify_suggestion_reviewers(db: Session, *, memory: CompanyMemory, current_user: User) -> None:
        NotificationService.create_for_owner_admins(
            db,
            company_id=memory.company_id,
            title="Company memory needs review",
            message=f"{memory.title} was suggested for Company Memory.",
            notification_type="company_memory.suggested",
            actor_user_id=current_user.id,
            actor_employee_id=actor_employee_id(db, current_user),
            target_entity_type="company_memory",
            target_entity_id=memory.id,
            priority="normal",
            action_url="#/memory",
            metadata=memory_event_metadata(memory),
            exclude_user_ids={current_user.id},
        )

    @staticmethod
    def notify_requester(db: Session, *, memory: CompanyMemory, current_user: User | None, approved: bool) -> None:
        if memory.created_by_user_id is None or (current_user is not None and memory.created_by_user_id == current_user.id):
            return
        NotificationService.create_notification(
            db,
            company_id=memory.company_id,
            recipient_user_id=memory.created_by_user_id,
            title="Memory approved" if approved else "Memory rejected",
            message=f"{memory.title} was {'approved' if approved else 'rejected'} in Company Memory.",
            notification_type="company_memory.approved" if approved else "company_memory.rejected",
            actor_user_id=current_user.id if current_user is not None else None,
            actor_employee_id=actor_employee_id(db, current_user),
            target_entity_type="company_memory",
            target_entity_id=memory.id,
            priority="normal",
            action_url="#/memory",
            metadata=memory_event_metadata(memory),
        )
