from collections.abc import Iterable
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.permissions import OWNER_ADMIN_ROLES
from app.models.attachment import Attachment
from app.models.communication import Announcement, Comment
from app.models.configuration import CustomFieldDefinition, WorkObjectType
from app.models.department import Department
from app.models.employee import Employee
from app.models.event import Event
from app.models.leave_request import LeaveRequest
from app.models.notification import Notification
from app.models.project import Project
from app.models.team import Team
from app.models.user import User
from app.models.work_object import WorkObject
from app.schemas.search import SearchResponse, SearchResult

SEARCH_GROUPS = {
    "employees",
    "departments",
    "teams",
    "projects",
    "work_objects",
    "leaves",
    "events",
    "notifications",
    "announcements",
    "comments",
    "files",
    "work_object_types",
    "custom_fields",
}

TYPE_ALIASES = {
    "employee": "employees",
    "department": "departments",
    "team": "teams",
    "project": "projects",
    "work_object": "work_objects",
    "work-object": "work_objects",
    "work": "work_objects",
    "task": "work_objects",
    "leave": "leaves",
    "leave_request": "leaves",
    "leave-request": "leaves",
    "event": "events",
    "notification": "notifications",
    "announcement": "announcements",
    "comment": "comments",
    "attachment": "files",
    "attachments": "files",
    "file": "files",
    "work_object_type": "work_object_types",
    "work-object-type": "work_object_types",
    "work_type": "work_object_types",
    "custom_field": "custom_fields",
    "custom-field": "custom_fields",
    "field": "custom_fields",
}


def _as_iso(value: datetime | date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _snippet(value: str | None, length: int = 180) -> str | None:
    if not value:
        return None
    compact = " ".join(value.split())
    if len(compact) <= length:
        return compact
    return f"{compact[: length - 1].rstrip()}..."


def _text_match(*columns: Any, term: str):
    return or_(*(column.ilike(term) for column in columns))


def _normalize_types(types: Iterable[str] | None) -> set[str]:
    if not types:
        return set(SEARCH_GROUPS)
    normalized: set[str] = set()
    for raw_type in types:
        value = raw_type.strip().lower()
        if not value:
            continue
        normalized.add(TYPE_ALIASES.get(value, value))
    return normalized & SEARCH_GROUPS


def _linked_employee(db: Session, current_user: User | None) -> Employee | None:
    if current_user is None:
        return None
    return db.scalar(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.user_id == current_user.id,
            Employee.is_active.is_(True),
        )
    )


def _notification_visibility(db: Session, current_user: User | None) -> list[Any]:
    if current_user is None:
        return []
    conditions: list[Any] = [Notification.recipient_user_id == current_user.id]
    employee = _linked_employee(db, current_user)
    if employee is not None:
        conditions.append(Notification.recipient_employee_id == employee.id)
    if current_user.role in OWNER_ADMIN_ROLES:
        conditions.append(and_(Notification.recipient_user_id.is_(None), Notification.recipient_employee_id.is_(None)))
    return conditions


def _employee_visible_work_conditions(db: Session, current_user: User | None) -> list[Any]:
    if current_user is None or current_user.role != "employee":
        return []
    conditions: list[Any] = [WorkObject.creator_user_id == current_user.id]
    employee = _linked_employee(db, current_user)
    if employee is not None:
        conditions.extend([WorkObject.assignee_employee_id == employee.id, WorkObject.creator_employee_id == employee.id])
    return conditions


def _employee_visible_leave_conditions(db: Session, current_user: User | None) -> list[Any]:
    if current_user is None or current_user.role != "employee":
        return []
    conditions: list[Any] = [LeaveRequest.requested_by_user_id == current_user.id]
    employee = _linked_employee(db, current_user)
    if employee is not None:
        conditions.extend([LeaveRequest.employee_id == employee.id, LeaveRequest.approver_employee_id == employee.id])
    return conditions


def _visible_work_object_ids_statement(db: Session, company_id: UUID, current_user: User | None):
    statement = select(WorkObject.id).where(WorkObject.company_id == company_id, WorkObject.is_active.is_(True))
    conditions = _employee_visible_work_conditions(db, current_user)
    if conditions:
        statement = statement.where(or_(*conditions))
    return statement


def _result(
    *,
    item_type: str,
    item_id: UUID,
    title: str,
    subtitle: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    related_entity_type: str | None = None,
    related_entity_id: UUID | None = None,
    created_at: datetime | date | None = None,
    updated_at: datetime | date | None = None,
    href: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> SearchResult:
    return SearchResult(
        type=item_type,
        id=str(item_id),
        title=title,
        subtitle=subtitle,
        description=_snippet(description),
        status=status,
        priority=priority,
        related_entity_type=related_entity_type,
        related_entity_id=str(related_entity_id) if related_entity_id else None,
        created_at=_as_iso(created_at),
        updated_at=_as_iso(updated_at),
        href=href,
        metadata=metadata or {},
    )


class SearchService:
    @staticmethod
    def search(
        db: Session,
        *,
        company_id: UUID,
        query: str | None,
        types: Iterable[str] | None = None,
        limit: int = 25,
        current_user: User | None = None,
    ) -> SearchResponse:
        trimmed_query = (query or "").strip()
        term = f"%{trimmed_query}%" if trimmed_query else None
        group_limit = min(max(limit, 1), 25)
        selected_types = _normalize_types(types)
        if current_user is not None and current_user.role == "employee":
            selected_types &= {"work_objects", "leaves", "notifications", "announcements", "comments", "files"}

        groups: dict[str, list[SearchResult]] = {group: [] for group in SEARCH_GROUPS}

        if "employees" in selected_types:
            groups["employees"] = SearchService._employees(db, company_id, term, group_limit)
        if "departments" in selected_types:
            groups["departments"] = SearchService._departments(db, company_id, term, group_limit)
        if "teams" in selected_types:
            groups["teams"] = SearchService._teams(db, company_id, term, group_limit)
        if "projects" in selected_types:
            groups["projects"] = SearchService._projects(db, company_id, term, group_limit)
        if "work_objects" in selected_types:
            groups["work_objects"] = SearchService._work_objects(db, company_id, term, group_limit, current_user)
        if "work_object_types" in selected_types:
            groups["work_object_types"] = SearchService._work_object_types(db, company_id, term, group_limit)
        if "custom_fields" in selected_types:
            groups["custom_fields"] = SearchService._custom_fields(db, company_id, term, group_limit)
        if "leaves" in selected_types:
            groups["leaves"] = SearchService._leaves(db, company_id, term, group_limit, current_user)
        if "files" in selected_types:
            groups["files"] = SearchService._files(db, company_id, term, group_limit, current_user)
        if "comments" in selected_types:
            groups["comments"] = SearchService._comments(db, company_id, term, group_limit, current_user)
        if "announcements" in selected_types:
            groups["announcements"] = SearchService._announcements(db, company_id, term, group_limit, current_user)
        if "events" in selected_types:
            groups["events"] = SearchService._events(db, company_id, term, group_limit)
        if "notifications" in selected_types:
            groups["notifications"] = SearchService._notifications(db, company_id, term, group_limit, current_user)

        filtered_groups = {name: results for name, results in groups.items() if results}
        flat_results = [result for results in filtered_groups.values() for result in results]
        return SearchResponse(
            query=trimmed_query,
            company_id=str(company_id),
            total=len(flat_results),
            groups=filtered_groups,
            results=flat_results,
        )

    @staticmethod
    def _employees(db: Session, company_id: UUID, term: str | None, limit: int) -> list[SearchResult]:
        statement = select(Employee).where(Employee.company_id == company_id)
        if term:
            statement = statement.where(
                _text_match(Employee.full_name, Employee.email, Employee.phone, Employee.role, Employee.department, Employee.status, term=term)
            )
        statement = statement.order_by(Employee.updated_at.desc()).limit(limit)
        return [
            _result(
                item_type="employee",
                item_id=employee.id,
                title=employee.full_name,
                subtitle=employee.email or employee.role,
                description=employee.department,
                status=employee.status,
                created_at=employee.created_at,
                updated_at=employee.updated_at,
                href="#/employees",
                metadata={
                    "role_title": employee.role,
                    "department_id": str(employee.department_id) if employee.department_id else None,
                    "team_id": str(employee.team_id) if employee.team_id else None,
                    "is_active": employee.is_active,
                },
            )
            for employee in db.scalars(statement).all()
        ]

    @staticmethod
    def _departments(db: Session, company_id: UUID, term: str | None, limit: int) -> list[SearchResult]:
        statement = select(Department).where(Department.company_id == company_id)
        if term:
            statement = statement.where(_text_match(Department.name, Department.description, term=term))
        statement = statement.order_by(Department.updated_at.desc()).limit(limit)
        return [
            _result(
                item_type="department",
                item_id=department.id,
                title=department.name,
                subtitle="Department",
                description=department.description,
                status="active" if department.is_active else "inactive",
                created_at=department.created_at,
                updated_at=department.updated_at,
                href="#/teams",
            )
            for department in db.scalars(statement).all()
        ]

    @staticmethod
    def _teams(db: Session, company_id: UUID, term: str | None, limit: int) -> list[SearchResult]:
        statement = select(Team).where(Team.company_id == company_id)
        if term:
            statement = statement.where(_text_match(Team.name, Team.department, Team.description, term=term))
        statement = statement.order_by(Team.updated_at.desc()).limit(limit)
        return [
            _result(
                item_type="team",
                item_id=team.id,
                title=team.name,
                subtitle=team.department or "Team",
                description=team.description,
                status="active" if team.is_active else "inactive",
                related_entity_type="department",
                related_entity_id=team.department_id,
                created_at=team.created_at,
                updated_at=team.updated_at,
                href="#/teams",
                metadata={"lead_employee_id": str(team.lead_employee_id) if team.lead_employee_id else None},
            )
            for team in db.scalars(statement).all()
        ]

    @staticmethod
    def _projects(db: Session, company_id: UUID, term: str | None, limit: int) -> list[SearchResult]:
        statement = select(Project).where(Project.company_id == company_id, Project.is_active.is_(True))
        if term:
            statement = statement.where(_text_match(Project.name, Project.code, Project.description, Project.status, Project.priority, term=term))
        statement = statement.order_by(Project.updated_at.desc()).limit(limit)
        return [
            _result(
                item_type="project",
                item_id=project.id,
                title=project.name,
                subtitle=project.code or project.status,
                description=project.description,
                status=project.status,
                priority=project.priority,
                related_entity_type="team" if project.team_id else "department" if project.department_id else None,
                related_entity_id=project.team_id or project.department_id,
                created_at=project.created_at,
                updated_at=project.updated_at,
                href="#/projects",
                metadata={
                    "owner_employee_id": str(project.owner_employee_id) if project.owner_employee_id else None,
                    "progress_percent": project.progress_percent,
                    "risk_level": project.risk_level,
                },
            )
            for project in db.scalars(statement).all()
        ]

    @staticmethod
    def _work_objects(db: Session, company_id: UUID, term: str | None, limit: int, current_user: User | None = None) -> list[SearchResult]:
        statement = select(WorkObject).where(WorkObject.company_id == company_id, WorkObject.is_active.is_(True))
        visibility_conditions = _employee_visible_work_conditions(db, current_user)
        if visibility_conditions:
            statement = statement.where(or_(*visibility_conditions))
        if term:
            statement = statement.where(
                _text_match(WorkObject.title, WorkObject.description, WorkObject.object_type, WorkObject.status, WorkObject.priority, term=term)
            )
        statement = statement.order_by(WorkObject.updated_at.desc()).limit(limit)
        return [
            _result(
                item_type="work_object",
                item_id=work_object.id,
                title=work_object.title,
                subtitle=work_object.object_type,
                description=work_object.description,
                status=work_object.status,
                priority=work_object.priority,
                related_entity_type="project" if work_object.project_id else None,
                related_entity_id=work_object.project_id,
                created_at=work_object.created_at,
                updated_at=work_object.updated_at,
                href="#/work-objects",
                metadata={
                    "assignee_employee_id": str(work_object.assignee_employee_id) if work_object.assignee_employee_id else None,
                    "department_id": str(work_object.department_id) if work_object.department_id else None,
                    "team_id": str(work_object.team_id) if work_object.team_id else None,
                    "tags": work_object.tags,
                    "custom_fields": work_object.custom_fields,
                },
            )
            for work_object in db.scalars(statement).all()
        ]

    @staticmethod
    def _work_object_types(db: Session, company_id: UUID, term: str | None, limit: int) -> list[SearchResult]:
        statement = select(WorkObjectType).where(WorkObjectType.company_id == company_id)
        if term:
            statement = statement.where(_text_match(WorkObjectType.key, WorkObjectType.name, WorkObjectType.description, term=term))
        statement = statement.order_by(WorkObjectType.updated_at.desc()).limit(limit)
        return [
            _result(
                item_type="work_object_type",
                item_id=work_type.id,
                title=work_type.name,
                subtitle=work_type.key,
                description=work_type.description,
                status="active" if work_type.is_active else "inactive",
                created_at=work_type.created_at,
                updated_at=work_type.updated_at,
                href="#/settings",
                metadata={"is_default": work_type.is_default, "sort_order": work_type.sort_order},
            )
            for work_type in db.scalars(statement).all()
        ]

    @staticmethod
    def _custom_fields(db: Session, company_id: UUID, term: str | None, limit: int) -> list[SearchResult]:
        statement = select(CustomFieldDefinition).where(CustomFieldDefinition.company_id == company_id)
        if term:
            statement = statement.where(
                _text_match(
                    CustomFieldDefinition.type_key,
                    CustomFieldDefinition.field_key,
                    CustomFieldDefinition.label,
                    CustomFieldDefinition.field_type,
                    CustomFieldDefinition.help_text,
                    term=term,
                )
            )
        statement = statement.order_by(CustomFieldDefinition.updated_at.desc()).limit(limit)
        return [
            _result(
                item_type="custom_field",
                item_id=field.id,
                title=field.label,
                subtitle=f"{field.type_key} / {field.field_type}",
                description=field.help_text,
                status="active" if field.is_active else "inactive",
                related_entity_type="work_object_type",
                related_entity_id=field.work_object_type_id,
                created_at=field.created_at,
                updated_at=field.updated_at,
                href="#/settings",
                metadata={
                    "type_key": field.type_key,
                    "field_key": field.field_key,
                    "required": field.required,
                    "options": field.options,
                },
            )
            for field in db.scalars(statement).all()
        ]

    @staticmethod
    def _leaves(db: Session, company_id: UUID, term: str | None, limit: int, current_user: User | None = None) -> list[SearchResult]:
        matching_employee_ids = []
        if term:
            matching_employee_ids = list(
                db.scalars(
                    select(Employee.id).where(
                        Employee.company_id == company_id,
                        _text_match(Employee.full_name, Employee.email, Employee.role, term=term),
                    )
                ).all()
            )
        statement = select(LeaveRequest).where(LeaveRequest.company_id == company_id, LeaveRequest.is_active.is_(True))
        visibility_conditions = _employee_visible_leave_conditions(db, current_user)
        if visibility_conditions:
            statement = statement.where(or_(*visibility_conditions))
        if term:
            conditions = [
                LeaveRequest.leave_type.ilike(term),
                LeaveRequest.status.ilike(term),
                LeaveRequest.reason.ilike(term),
                LeaveRequest.manager_note.ilike(term),
            ]
            if matching_employee_ids:
                conditions.append(LeaveRequest.employee_id.in_(matching_employee_ids))
                conditions.append(LeaveRequest.approver_employee_id.in_(matching_employee_ids))
            statement = statement.where(or_(*conditions))
        statement = statement.order_by(LeaveRequest.updated_at.desc()).limit(limit)
        return [
            _result(
                item_type="leave_request",
                item_id=leave.id,
                title=f"{leave.leave_type.replace('_', ' ').title()} leave",
                subtitle=f"{leave.start_date.isoformat()} to {leave.end_date.isoformat()}",
                description=leave.reason,
                status=leave.status,
                related_entity_type="employee",
                related_entity_id=leave.employee_id,
                created_at=leave.created_at,
                updated_at=leave.updated_at,
                href="#/leaves",
                metadata={
                    "employee_id": str(leave.employee_id),
                    "approver_employee_id": str(leave.approver_employee_id) if leave.approver_employee_id else None,
                    "total_days": leave.total_days,
                },
            )
            for leave in db.scalars(statement).all()
        ]

    @staticmethod
    def _files(db: Session, company_id: UUID, term: str | None, limit: int, current_user: User | None = None) -> list[SearchResult]:
        statement = select(Attachment).where(Attachment.company_id == company_id, Attachment.is_active.is_(True))
        if current_user is not None and current_user.role == "employee":
            statement = statement.where(Attachment.work_object_id.in_(_visible_work_object_ids_statement(db, company_id, current_user)))
        if term:
            statement = statement.where(
                _text_match(
                    Attachment.file_name,
                    Attachment.original_file_name,
                    Attachment.content_type,
                    Attachment.description,
                    Attachment.linked_entity_type,
                    term=term,
                )
            )
        statement = statement.order_by(Attachment.updated_at.desc()).limit(limit)
        return [
            _result(
                item_type="file",
                item_id=attachment.id,
                title=attachment.original_file_name,
                subtitle=attachment.content_type or "File",
                description=attachment.description,
                related_entity_type=attachment.linked_entity_type,
                related_entity_id=attachment.linked_entity_id,
                created_at=attachment.created_at,
                updated_at=attachment.updated_at,
                href="#/work-objects" if attachment.work_object_id else "#/projects",
                metadata={
                    "file_size": attachment.file_size,
                    "work_object_id": str(attachment.work_object_id) if attachment.work_object_id else None,
                    "project_id": str(attachment.project_id) if attachment.project_id else None,
                    "uploaded_by_employee_id": str(attachment.uploaded_by_employee_id) if attachment.uploaded_by_employee_id else None,
                },
            )
            for attachment in db.scalars(statement).all()
        ]

    @staticmethod
    def _comments(db: Session, company_id: UUID, term: str | None, limit: int, current_user: User | None = None) -> list[SearchResult]:
        statement = select(Comment).where(Comment.company_id == company_id, Comment.is_archived.is_(False))
        if current_user is not None and current_user.role == "employee":
            statement = statement.where(
                Comment.target_entity_type == "work_object",
                Comment.target_entity_id.in_(_visible_work_object_ids_statement(db, company_id, current_user)),
            )
        if term:
            statement = statement.where(Comment.body.ilike(term))
        statement = statement.order_by(Comment.updated_at.desc()).limit(limit)
        return [
            _result(
                item_type="comment",
                item_id=comment.id,
                title=_snippet(comment.body, 80) or "Comment",
                subtitle=comment.target_entity_type,
                description=comment.body,
                related_entity_type=comment.target_entity_type,
                related_entity_id=comment.target_entity_id,
                created_at=comment.created_at,
                updated_at=comment.updated_at,
                href="#/work-objects" if comment.target_entity_type == "work_object" else "#/projects",
                metadata={
                    "author_user_id": str(comment.author_user_id) if comment.author_user_id else None,
                    "author_employee_id": str(comment.author_employee_id) if comment.author_employee_id else None,
                    "is_edited": comment.is_edited,
                },
            )
            for comment in db.scalars(statement).all()
        ]

    @staticmethod
    def _announcements(db: Session, company_id: UUID, term: str | None, limit: int, current_user: User | None = None) -> list[SearchResult]:
        statement = select(Announcement).where(Announcement.company_id == company_id, Announcement.is_archived.is_(False))
        if current_user is not None and current_user.role not in OWNER_ADMIN_ROLES:
            statement = statement.where(Announcement.is_published.is_(True))
        if term:
            statement = statement.where(_text_match(Announcement.title, Announcement.body, Announcement.priority, term=term))
        statement = statement.order_by(Announcement.updated_at.desc()).limit(limit)
        return [
            _result(
                item_type="announcement",
                item_id=announcement.id,
                title=announcement.title,
                subtitle="Published" if announcement.is_published else "Draft",
                description=announcement.body,
                priority=announcement.priority,
                created_at=announcement.created_at,
                updated_at=announcement.updated_at,
                href="#/announcements",
                metadata={"published_at": announcement.published_at.isoformat() if announcement.published_at else None},
            )
            for announcement in db.scalars(statement).all()
        ]

    @staticmethod
    def _events(db: Session, company_id: UUID, term: str | None, limit: int) -> list[SearchResult]:
        statement = select(Event).where(Event.company_id == company_id)
        if term:
            statement = statement.where(
                _text_match(Event.title, Event.description, Event.event_type, Event.target_entity_type, Event.related_entity_type, term=term)
            )
        statement = statement.order_by(Event.created_at.desc()).limit(limit)
        return [
            _result(
                item_type="event",
                item_id=event.id,
                title=event.title,
                subtitle=event.event_type,
                description=event.description,
                related_entity_type=event.target_entity_type,
                related_entity_id=event.target_entity_id,
                created_at=event.created_at,
                href="#/events",
                metadata={
                    "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
                    "actor_employee_id": str(event.actor_employee_id) if event.actor_employee_id else None,
                    "related_entity_type": event.related_entity_type,
                    "related_entity_id": str(event.related_entity_id) if event.related_entity_id else None,
                },
            )
            for event in db.scalars(statement).all()
        ]

    @staticmethod
    def _notifications(
        db: Session,
        company_id: UUID,
        term: str | None,
        limit: int,
        current_user: User | None,
    ) -> list[SearchResult]:
        statement = select(Notification).where(Notification.company_id == company_id, Notification.is_dismissed.is_(False))
        conditions = _notification_visibility(db, current_user)
        if conditions:
            statement = statement.where(or_(*conditions))
        if term:
            statement = statement.where(
                _text_match(Notification.title, Notification.message, Notification.notification_type, Notification.priority, term=term)
            )
        statement = statement.order_by(Notification.created_at.desc()).limit(limit)
        return [
            _result(
                item_type="notification",
                item_id=notification.id,
                title=notification.title,
                subtitle=notification.notification_type,
                description=notification.message,
                status="read" if notification.is_read else "unread",
                priority=notification.priority,
                related_entity_type=notification.target_entity_type,
                related_entity_id=notification.target_entity_id,
                created_at=notification.created_at,
                updated_at=notification.updated_at,
                href=notification.action_url or "#/notifications",
                metadata={
                    "recipient_user_id": str(notification.recipient_user_id) if notification.recipient_user_id else None,
                    "recipient_employee_id": str(notification.recipient_employee_id) if notification.recipient_employee_id else None,
                },
            )
            for notification in db.scalars(statement).all()
        ]
