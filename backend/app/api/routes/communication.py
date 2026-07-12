import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import db_session, get_optional_current_user
from app.api.utils import ensure_company, get_or_404
from app.core.permissions import MANAGER_ROLES, OWNER_ADMIN_ROLES, ensure_company_access, ensure_role
from app.models.communication import Announcement, Comment, CommentMention
from app.models.employee import Employee
from app.models.event import Event
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.models.work_object import WorkObject
from app.schemas.communication import (
    AnnouncementCreate,
    AnnouncementRead,
    AnnouncementUpdate,
    CommentCreate,
    CommentRead,
    CommentUpdate,
)
from app.services.event_service import EventService
from app.services.notification_service import NotificationService

comments_router = APIRouter(prefix="/comments", tags=["communication"])
announcements_router = APIRouter(prefix="/announcements", tags=["communication"])

COMMENT_TARGET_TYPES = {"work_object", "project"}
ANNOUNCEMENT_PRIORITIES = {"low", "normal", "high", "urgent"}
MENTION_PATTERN = re.compile(r"@([A-Za-z][A-Za-z0-9._'-]*(?:\s+[A-Za-z][A-Za-z0-9._'-]*){0,3})")


def normalize_priority(value: str) -> str:
    normalized = value.strip().lower()
    if normalized not in ANNOUNCEMENT_PRIORITIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid announcement priority")
    return normalized


def metadata_dict(value: dict[str, object] | None) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    return {}


def get_linked_employee(db: Session, current_user: User | None) -> Employee | None:
    if current_user is None:
        return None
    return db.scalar(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.user_id == current_user.id,
            Employee.is_active.is_(True),
        )
    )


def actor_employee_id(db: Session, current_user: User | None, fallback_employee_id: UUID | None = None) -> UUID | None:
    linked_employee = get_linked_employee(db, current_user)
    return linked_employee.id if linked_employee is not None else fallback_employee_id


def ensure_valid_comment_target_type(target_entity_type: str) -> str:
    normalized = target_entity_type.strip().lower()
    if normalized not in COMMENT_TARGET_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid comment target")
    return normalized


def can_view_work_object(db: Session, current_user: User | None, work_object: WorkObject) -> bool:
    if current_user is None or current_user.role in MANAGER_ROLES:
        return True
    if work_object.creator_user_id == current_user.id:
        return True
    linked_employee = get_linked_employee(db, current_user)
    if linked_employee is None:
        return False
    return work_object.assignee_employee_id == linked_employee.id or work_object.creator_employee_id == linked_employee.id


def can_view_project(db: Session, current_user: User | None, project: Project) -> bool:
    if current_user is None or current_user.role in MANAGER_ROLES:
        return True
    if project.owner_user_id == current_user.id:
        return True
    linked_employee = get_linked_employee(db, current_user)
    if linked_employee is None:
        return False
    if project.owner_employee_id == linked_employee.id:
        return True
    return bool(
        db.scalar(
            select(ProjectMember.id).where(
                ProjectMember.company_id == project.company_id,
                ProjectMember.project_id == project.id,
                ProjectMember.employee_id == linked_employee.id,
                ProjectMember.is_active.is_(True),
            )
        )
    )


def get_comment_target(
    db: Session,
    current_user: User | None,
    *,
    company_id: UUID,
    target_entity_type: str,
    target_entity_id: UUID,
) -> WorkObject | Project:
    target_type = ensure_valid_comment_target_type(target_entity_type)
    ensure_company_access(current_user, company_id)
    if target_type == "work_object":
        work_object = get_or_404(db, WorkObject, target_entity_id, label="Work object")
        ensure_company(work_object, company_id, label="Work object")
        if not can_view_work_object(db, current_user, work_object):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Work object not found")
        return work_object
    project = get_or_404(db, Project, target_entity_id, label="Project")
    ensure_company(project, company_id, label="Project")
    if not can_view_project(db, current_user, project):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def get_comment_for_user(
    db: Session,
    current_user: User | None,
    *,
    comment_id: UUID,
    company_id: UUID,
    include_archived: bool = False,
) -> Comment:
    ensure_company_access(current_user, company_id)
    comment = get_or_404(db, Comment, comment_id, label="Comment")
    ensure_company(comment, company_id, label="Comment")
    if comment.is_archived and not include_archived:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    get_comment_target(
        db,
        current_user,
        company_id=company_id,
        target_entity_type=comment.target_entity_type,
        target_entity_id=comment.target_entity_id,
    )
    return comment


def ensure_comment_author_or_admin(db: Session, current_user: User | None, comment: Comment) -> None:
    if current_user is None or current_user.role in OWNER_ADMIN_ROLES:
        return
    if comment.author_user_id == current_user.id:
        return
    linked_employee = get_linked_employee(db, current_user)
    if linked_employee is not None and comment.author_employee_id == linked_employee.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission for this comment")


def validate_mentioned_employees(db: Session, *, company_id: UUID, employee_ids: list[UUID] | None) -> list[Employee]:
    employees: list[Employee] = []
    seen: set[UUID] = set()
    for employee_id in employee_ids or []:
        if employee_id in seen:
            continue
        seen.add(employee_id)
        employee = get_or_404(db, Employee, employee_id, label="Mentioned employee")
        ensure_company(employee, company_id, label="Mentioned employee")
        employees.append(employee)
    return employees


def validate_mentioned_users(db: Session, *, company_id: UUID, user_ids: list[UUID] | None) -> list[User]:
    users: list[User] = []
    seen: set[UUID] = set()
    for user_id in user_ids or []:
        if user_id in seen:
            continue
        seen.add(user_id)
        user = get_or_404(db, User, user_id, label="Mentioned user")
        ensure_company_access(user, company_id)
        users.append(user)
    return users


def normalize_mention_name(value: str) -> str:
    return " ".join(value.strip(".,:;!?()[]{}").lower().split())


def mention_name_candidates(value: str) -> set[str]:
    words = normalize_mention_name(value).split()
    return {" ".join(words[:index]) for index in range(1, min(len(words), 4) + 1)}


def parse_mentioned_employees_from_body(db: Session, *, company_id: UUID, body: str) -> list[Employee]:
    mention_names: set[str] = set()
    for match in MENTION_PATTERN.finditer(body):
        mention_names.update(mention_name_candidates(match.group(1)))
    mention_names.discard("")
    if not mention_names:
        return []
    employees = db.scalars(
        select(Employee).where(
            Employee.company_id == company_id,
            Employee.is_active.is_(True),
        )
    ).all()
    matches: list[Employee] = []
    seen: set[UUID] = set()
    for employee in employees:
        full_name = normalize_mention_name(employee.full_name)
        first_name = normalize_mention_name(employee.full_name.split()[0]) if employee.full_name.split() else ""
        email_name = normalize_mention_name(employee.email.split("@")[0]) if employee.email else ""
        aliases = {full_name, first_name, email_name}
        if aliases.intersection(mention_names) and employee.id not in seen:
            matches.append(employee)
            seen.add(employee.id)
    return matches


def merge_employees(*employee_lists: list[Employee]) -> list[Employee]:
    merged: dict[UUID, Employee] = {}
    for employees in employee_lists:
        for employee in employees:
            merged.setdefault(employee.id, employee)
    return list(merged.values())


def merge_users(*user_lists: list[User]) -> list[User]:
    merged: dict[UUID, User] = {}
    for users in user_lists:
        for user in users:
            merged.setdefault(user.id, user)
    return list(merged.values())


def set_comment_mentions(
    db: Session,
    *,
    comment: Comment,
    employees: list[Employee],
    users: list[User],
) -> list[CommentMention]:
    for mention in list(comment.mentions):
        db.delete(mention)
    mentions: list[CommentMention] = []
    mentioned_user_ids_from_employees = {employee.user_id for employee in employees if employee.user_id is not None}
    for employee in employees:
        mention = CommentMention(
            company_id=comment.company_id,
            comment_id=comment.id,
            mentioned_employee_id=employee.id,
            mentioned_user_id=employee.user_id,
        )
        db.add(mention)
        mentions.append(mention)
    for user in users:
        if user.id in mentioned_user_ids_from_employees:
            continue
        mention = CommentMention(
            company_id=comment.company_id,
            comment_id=comment.id,
            mentioned_user_id=user.id,
        )
        db.add(mention)
        mentions.append(mention)
    db.flush()
    comment.mentions = mentions
    return mentions


def record_comment_event(
    db: Session,
    *,
    comment: Comment,
    current_user: User | None,
    event_type: str,
    title: str,
    description: str,
    metadata: dict[str, object] | None = None,
) -> Event:
    event_metadata: dict[str, object] = {
        "comment_id": str(comment.id),
        "parent_comment_id": str(comment.parent_comment_id) if comment.parent_comment_id else None,
        "actor_user_id": str(current_user.id) if current_user else None,
    }
    event_metadata.update(metadata_dict(metadata))
    return EventService.record_event(
        db,
        company_id=comment.company_id,
        actor_user_id=current_user.id if current_user is not None else None,
        actor_employee_id=actor_employee_id(db, current_user, comment.author_employee_id),
        event_type=event_type,
        title=title,
        description=description,
        target_entity_type=comment.target_entity_type,
        target_entity_id=comment.target_entity_id,
        related_entity_type="comment",
        related_entity_id=comment.id,
        metadata=event_metadata,
    )


def action_url_for_comment(comment: Comment) -> str:
    if comment.target_entity_type == "project":
        return "#/projects"
    return "#/work-objects"


def comment_target_label(target: WorkObject | Project) -> str:
    if isinstance(target, WorkObject):
        return target.title
    return target.name


def comment_target_kind(target: WorkObject | Project) -> str:
    if isinstance(target, WorkObject):
        return "work object"
    return "project"


def actor_display_name(db: Session, current_user: User | None, actor_id: UUID | None) -> str:
    if actor_id is not None:
        employee = db.get(Employee, actor_id)
        if employee is not None:
            return employee.full_name
    if current_user is not None:
        return current_user.full_name
    return "A company member"


def notify_comment_mentions(
    db: Session,
    *,
    comment: Comment,
    target: WorkObject | Project,
    current_user: User | None,
    event: Event | None,
    employees: list[Employee],
    users: list[User],
) -> None:
    actor_id = actor_employee_id(db, current_user, comment.author_employee_id)
    actor_name = actor_display_name(db, current_user, actor_id)
    target_label = comment_target_label(target)
    target_kind = comment_target_kind(target)
    message = f"{actor_name} mentioned you in a {target_kind} comment on {target_label}."
    metadata = {
        "comment_id": str(comment.id),
        "target_entity_type": comment.target_entity_type,
        "target_entity_id": str(comment.target_entity_id),
        "target_label": target_label,
    }
    mentioned_user_ids_from_employees = {employee.user_id for employee in employees if employee.user_id is not None}
    recipient_employee_ids = [employee.id for employee in employees if employee.id != actor_id]
    if recipient_employee_ids:
        NotificationService.create_for_employees(
            db,
            company_id=comment.company_id,
            recipient_employee_ids=recipient_employee_ids,
            actor_user_id=current_user.id if current_user else None,
            actor_employee_id=actor_id,
            event_id=event.id if event else None,
            title=f"Mentioned in {target_label}",
            message=message,
            notification_type="communication.mentioned",
            target_entity_type="comment",
            target_entity_id=comment.id,
            priority="normal",
            action_url=action_url_for_comment(comment),
            metadata=metadata,
        )
    for user in users:
        if user.id == (current_user.id if current_user else None) or user.id in mentioned_user_ids_from_employees:
            continue
        NotificationService.create_notification(
            db,
            company_id=comment.company_id,
            recipient_user_id=user.id,
            actor_user_id=current_user.id if current_user else None,
            actor_employee_id=actor_id,
            event_id=event.id if event else None,
            title=f"Mentioned in {target_label}",
            message=message,
            notification_type="communication.mentioned",
            target_entity_type="comment",
            target_entity_id=comment.id,
            priority="normal",
            action_url=action_url_for_comment(comment),
            metadata=metadata,
        )


def work_comment_recipients(work_object: WorkObject, actor_employee_id_value: UUID | None) -> list[UUID]:
    recipients: list[UUID] = []
    for employee_id in [work_object.assignee_employee_id, work_object.creator_employee_id]:
        if employee_id is None or employee_id == actor_employee_id_value or employee_id in recipients:
            continue
        recipients.append(employee_id)
    return recipients


def project_comment_recipients(db: Session, project: Project, actor_employee_id_value: UUID | None) -> list[UUID]:
    recipients: list[UUID] = []
    if project.owner_employee_id is not None and project.owner_employee_id != actor_employee_id_value:
        recipients.append(project.owner_employee_id)
    members = db.scalars(
        select(ProjectMember).where(
            ProjectMember.company_id == project.company_id,
            ProjectMember.project_id == project.id,
            ProjectMember.is_active.is_(True),
        )
    ).all()
    for member in members:
        if member.employee_id == actor_employee_id_value or member.employee_id in recipients:
            continue
        recipients.append(member.employee_id)
    return recipients


def notify_comment_target_watchers(
    db: Session,
    *,
    comment: Comment,
    target: WorkObject | Project,
    current_user: User | None,
    event: Event | None,
    exclude_employee_ids: set[UUID] | None = None,
) -> None:
    actor_id = actor_employee_id(db, current_user, comment.author_employee_id)
    if isinstance(target, WorkObject):
        recipients = work_comment_recipients(target, actor_id)
        notification_type = "comment.added_to_assigned_work"
        message = f"A comment was added to {target.title}."
    else:
        recipients = project_comment_recipients(db, target, actor_id)
        notification_type = "comment.added_to_project"
        message = f"A comment was added to {target.name}."
    if not recipients:
        return
    NotificationService.create_for_employees(
        db,
        company_id=comment.company_id,
        recipient_employee_ids=recipients,
        actor_user_id=current_user.id if current_user else None,
        actor_employee_id=actor_id,
        event_id=event.id if event else None,
        title="New comment",
        message=message,
        notification_type=notification_type,
        target_entity_type="comment",
        target_entity_id=comment.id,
        priority="normal",
        action_url=action_url_for_comment(comment),
        metadata={"comment_id": str(comment.id), "target_entity_type": comment.target_entity_type},
        exclude_employee_ids=exclude_employee_ids,
    )


def notify_reply(
    db: Session,
    *,
    comment: Comment,
    parent: Comment | None,
    current_user: User | None,
    event: Event | None,
) -> None:
    if parent is None:
        return
    actor_id = actor_employee_id(db, current_user, comment.author_employee_id)
    if parent.author_employee_id is not None and parent.author_employee_id != actor_id:
        NotificationService.create_notification(
            db,
            company_id=comment.company_id,
            recipient_employee_id=parent.author_employee_id,
            actor_user_id=current_user.id if current_user else None,
            actor_employee_id=actor_id,
            event_id=event.id if event else None,
            title="New reply",
            message="A comment received a reply.",
            notification_type="communication.reply",
            target_entity_type="comment",
            target_entity_id=comment.id,
            priority="normal",
            action_url=action_url_for_comment(comment),
            metadata={"comment_id": str(comment.id), "parent_comment_id": str(parent.id)},
        )
    elif parent.author_user_id is not None and parent.author_user_id != (current_user.id if current_user else None):
        NotificationService.create_notification(
            db,
            company_id=comment.company_id,
            recipient_user_id=parent.author_user_id,
            actor_user_id=current_user.id if current_user else None,
            actor_employee_id=actor_id,
            event_id=event.id if event else None,
            title="New reply",
            message="A comment received a reply.",
            notification_type="communication.reply",
            target_entity_type="comment",
            target_entity_id=comment.id,
            priority="normal",
            action_url=action_url_for_comment(comment),
            metadata={"comment_id": str(comment.id), "parent_comment_id": str(parent.id)},
        )


@comments_router.get("", response_model=list[CommentRead])
def list_comments(
    company_id: UUID,
    target_entity_type: str,
    target_entity_id: UUID,
    include_archived: bool = False,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    limit: int = Query(default=100, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
) -> list[Comment]:
    target_type = ensure_valid_comment_target_type(target_entity_type)
    get_comment_target(db, current_user, company_id=company_id, target_entity_type=target_type, target_entity_id=target_entity_id)
    statement = (
        select(Comment)
        .options(selectinload(Comment.mentions))
        .where(
            Comment.company_id == company_id,
            Comment.target_entity_type == target_type,
            Comment.target_entity_id == target_entity_id,
        )
        .order_by(Comment.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    if not include_archived:
        statement = statement.where(Comment.is_archived.is_(False))
    return list(db.scalars(statement).all())


@comments_router.post("", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def create_comment(
    payload: CommentCreate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Comment:
    target_type = ensure_valid_comment_target_type(payload.target_entity_type)
    target = get_comment_target(db, current_user, company_id=payload.company_id, target_entity_type=target_type, target_entity_id=payload.target_entity_id)
    parent: Comment | None = None
    if payload.parent_comment_id is not None:
        parent = get_comment_for_user(
            db,
            current_user,
            comment_id=payload.parent_comment_id,
            company_id=payload.company_id,
        )
        if parent.target_entity_type != target_type or parent.target_entity_id != payload.target_entity_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Reply target does not match parent comment")
    author_id = actor_employee_id(db, current_user, payload.author_employee_id)
    if author_id is not None:
        employee = get_or_404(db, Employee, author_id, label="Author")
        ensure_company(employee, payload.company_id, label="Author")
    explicit_employees = validate_mentioned_employees(db, company_id=payload.company_id, employee_ids=payload.mentioned_employee_ids)
    parsed_employees = parse_mentioned_employees_from_body(db, company_id=payload.company_id, body=payload.body)
    employees = merge_employees(explicit_employees, parsed_employees)
    users = validate_mentioned_users(db, company_id=payload.company_id, user_ids=payload.mentioned_user_ids)
    comment = Comment(
        company_id=payload.company_id,
        author_user_id=current_user.id if current_user else None,
        author_employee_id=author_id,
        target_entity_type=target_type,
        target_entity_id=payload.target_entity_id,
        parent_comment_id=payload.parent_comment_id,
        body=payload.body.strip(),
        metadata_json=payload.metadata,
    )
    db.add(comment)
    db.flush()
    mentions = set_comment_mentions(db, comment=comment, employees=employees, users=users)
    created_event = record_comment_event(
        db,
        comment=comment,
        current_user=current_user,
        event_type="comment.created",
        title="Comment added",
        description="A comment was added.",
        metadata={
            "mentioned_employee_ids": [str(mention.mentioned_employee_id) for mention in mentions if mention.mentioned_employee_id],
            "mentioned_user_ids": [str(mention.mentioned_user_id) for mention in mentions if mention.mentioned_user_id],
        },
    )
    if mentions:
        mention_event = record_comment_event(
            db,
            comment=comment,
            current_user=current_user,
            event_type="comment.mentioned",
            title="Comment mention added",
            description="A comment mentioned one or more people.",
            metadata={
                "mentioned_employee_ids": [str(mention.mentioned_employee_id) for mention in mentions if mention.mentioned_employee_id],
                "mentioned_user_ids": [str(mention.mentioned_user_id) for mention in mentions if mention.mentioned_user_id],
            },
        )
        notify_comment_mentions(db, comment=comment, target=target, current_user=current_user, event=mention_event, employees=employees, users=users)
    notify_reply(db, comment=comment, parent=parent, current_user=current_user, event=created_event)
    notify_comment_target_watchers(
        db,
        comment=comment,
        target=target,
        current_user=current_user,
        event=created_event,
        exclude_employee_ids={employee.id for employee in employees},
    )
    db.commit()
    db.refresh(comment)
    return comment


@comments_router.patch("/{comment_id}", response_model=CommentRead)
def update_comment(
    comment_id: UUID,
    company_id: UUID,
    payload: CommentUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Comment:
    comment = get_comment_for_user(db, current_user, comment_id=comment_id, company_id=company_id)
    ensure_comment_author_or_admin(db, current_user, comment)
    target = get_comment_target(
        db,
        current_user,
        company_id=company_id,
        target_entity_type=comment.target_entity_type,
        target_entity_id=comment.target_entity_id,
    )
    changed_fields: list[str] = []
    body_changed = False
    if payload.body is not None and payload.body.strip() != comment.body:
        comment.body = payload.body.strip()
        comment.is_edited = True
        comment.edited_at = datetime.now(timezone.utc)
        changed_fields.extend(["body", "edited_at"])
        body_changed = True
    if payload.metadata:
        comment.metadata_json = payload.metadata
        changed_fields.append("metadata")
    if body_changed or payload.mentioned_employee_ids is not None or payload.mentioned_user_ids is not None:
        previous_employee_ids = {mention.mentioned_employee_id for mention in comment.mentions if mention.mentioned_employee_id is not None}
        previous_user_ids = {mention.mentioned_user_id for mention in comment.mentions if mention.mentioned_user_id is not None}
        employee_ids = (
            payload.mentioned_employee_ids
            if payload.mentioned_employee_ids is not None
            else [employee_id for employee_id in previous_employee_ids]
        )
        user_ids = (
            payload.mentioned_user_ids
            if payload.mentioned_user_ids is not None
            else [user_id for user_id in previous_user_ids]
        )
        explicit_employees = validate_mentioned_employees(db, company_id=company_id, employee_ids=employee_ids)
        parsed_employees = parse_mentioned_employees_from_body(db, company_id=company_id, body=comment.body)
        employees = merge_employees(explicit_employees, parsed_employees)
        users = validate_mentioned_users(db, company_id=company_id, user_ids=user_ids)
        mentions = set_comment_mentions(db, comment=comment, employees=employees, users=users)
        changed_fields.append("mentions")
        new_employees = [employee for employee in employees if employee.id not in previous_employee_ids]
        new_users = [user for user in users if user.id not in previous_user_ids]
        if new_employees or new_users:
            mention_event = record_comment_event(
                db,
                comment=comment,
                current_user=current_user,
                event_type="comment.mentioned",
                title="Comment mention added",
                description="A comment mentioned one or more people.",
                metadata={
                    "mentioned_employee_ids": [str(mention.mentioned_employee_id) for mention in mentions if mention.mentioned_employee_id],
                    "mentioned_user_ids": [str(mention.mentioned_user_id) for mention in mentions if mention.mentioned_user_id],
                },
            )
            notify_comment_mentions(db, comment=comment, target=target, current_user=current_user, event=mention_event, employees=new_employees, users=new_users)
    if changed_fields:
        record_comment_event(
            db,
            comment=comment,
            current_user=current_user,
            event_type="comment.updated",
            title="Comment updated",
            description="A comment was updated.",
            metadata={"changed_fields": sorted(set(changed_fields))},
        )
    db.commit()
    db.refresh(comment)
    return comment


@comments_router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_comment(
    comment_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Response:
    comment = get_comment_for_user(db, current_user, comment_id=comment_id, company_id=company_id)
    ensure_comment_author_or_admin(db, current_user, comment)
    comment.is_archived = True
    comment.body = "[archived comment]"
    record_comment_event(
        db,
        comment=comment,
        current_user=current_user,
        event_type="comment.archived",
        title="Comment archived",
        description="A comment was archived.",
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def record_announcement_event(
    db: Session,
    *,
    announcement: Announcement,
    current_user: User | None,
    event_type: str,
    title: str,
    description: str,
    metadata: dict[str, object] | None = None,
) -> Event:
    event_metadata = {
        "announcement_id": str(announcement.id),
        "priority": announcement.priority,
        "actor_user_id": str(current_user.id) if current_user else None,
    }
    event_metadata.update(metadata_dict(metadata))
    return EventService.record_event(
        db,
        company_id=announcement.company_id,
        actor_user_id=current_user.id if current_user else None,
        actor_employee_id=actor_employee_id(db, current_user),
        event_type=event_type,
        title=title,
        description=description,
        target_entity_type="announcement",
        target_entity_id=announcement.id,
        metadata=event_metadata,
    )


def notify_announcement(db: Session, *, announcement: Announcement, current_user: User | None, event: Event | None) -> None:
    NotificationService.create_notification(
        db,
        company_id=announcement.company_id,
        actor_user_id=current_user.id if current_user else None,
        actor_employee_id=actor_employee_id(db, current_user),
        event_id=event.id if event else None,
        title=announcement.title,
        message=announcement.body[:240],
        notification_type="announcement.published",
        target_entity_type="announcement",
        target_entity_id=announcement.id,
        priority=announcement.priority if announcement.priority in ANNOUNCEMENT_PRIORITIES else "normal",
        action_url="#/announcements",
        metadata={"announcement_id": str(announcement.id)},
        company_wide=True,
    )


@announcements_router.get("", response_model=list[AnnouncementRead])
def list_announcements(
    company_id: UUID,
    include_archived: bool = False,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Announcement]:
    ensure_company_access(current_user, company_id)
    statement = select(Announcement).where(Announcement.company_id == company_id)
    if not include_archived:
        statement = statement.where(Announcement.is_archived.is_(False))
    if current_user is not None and current_user.role not in OWNER_ADMIN_ROLES:
        statement = statement.where(Announcement.is_published.is_(True))
    statement = statement.order_by(Announcement.published_at.desc().nullslast(), Announcement.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@announcements_router.post("", response_model=AnnouncementRead, status_code=status.HTTP_201_CREATED)
def create_announcement(
    payload: AnnouncementCreate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Announcement:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    announcement = Announcement(
        id=uuid4(),
        company_id=payload.company_id,
        author_user_id=current_user.id if current_user else None,
        title=payload.title.strip(),
        body=payload.body.strip(),
        priority=normalize_priority(payload.priority),
        metadata_json=payload.metadata,
        is_published=payload.is_published,
        published_at=datetime.now(timezone.utc) if payload.is_published else None,
    )
    db.add(announcement)
    record_announcement_event(
        db,
        announcement=announcement,
        current_user=current_user,
        event_type="announcement.created",
        title=f"{announcement.title} created",
        description="An internal announcement was created.",
    )
    if announcement.is_published:
        published_event = record_announcement_event(
            db,
            announcement=announcement,
            current_user=current_user,
            event_type="announcement.published",
            title=f"{announcement.title} published",
            description="An internal announcement was published.",
        )
        notify_announcement(db, announcement=announcement, current_user=current_user, event=published_event)
    db.commit()
    return announcement


@announcements_router.patch("/{announcement_id}", response_model=AnnouncementRead)
def update_announcement(
    announcement_id: UUID,
    company_id: UUID,
    payload: AnnouncementUpdate,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Announcement:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    announcement = get_or_404(db, Announcement, announcement_id, label="Announcement")
    ensure_company(announcement, company_id, label="Announcement")
    was_published = announcement.is_published
    changed_fields: list[str] = []
    data = payload.model_dump(exclude_unset=True)
    if "metadata" in data:
        announcement.metadata_json = data.pop("metadata") or {}
        changed_fields.append("metadata")
    if "priority" in data and data["priority"] is not None:
        data["priority"] = normalize_priority(str(data["priority"]))
    for field, value in data.items():
        setattr(announcement, field, value)
        changed_fields.append(field)
    if announcement.is_published and not was_published:
        announcement.published_at = datetime.now(timezone.utc)
        published_event = record_announcement_event(
            db,
            announcement=announcement,
            current_user=current_user,
            event_type="announcement.published",
            title=f"{announcement.title} published",
            description="An internal announcement was published.",
        )
        notify_announcement(db, announcement=announcement, current_user=current_user, event=published_event)
    if changed_fields:
        record_announcement_event(
            db,
            announcement=announcement,
            current_user=current_user,
            event_type="announcement.updated",
            title=f"{announcement.title} updated",
            description="An internal announcement was updated.",
            metadata={"changed_fields": sorted(set(changed_fields))},
        )
    db.commit()
    return announcement


@announcements_router.patch("/{announcement_id}/archive", response_model=AnnouncementRead)
def archive_announcement(
    announcement_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> Announcement:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, OWNER_ADMIN_ROLES)
    announcement = get_or_404(db, Announcement, announcement_id, label="Announcement")
    ensure_company(announcement, company_id, label="Announcement")
    announcement.is_archived = True
    record_announcement_event(
        db,
        announcement=announcement,
        current_user=current_user,
        event_type="announcement.archived",
        title=f"{announcement.title} archived",
        description="An internal announcement was archived.",
    )
    db.commit()
    return announcement
