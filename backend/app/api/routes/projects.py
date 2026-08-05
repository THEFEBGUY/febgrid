from uuid import UUID, uuid4

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.api.serializers import serialize_events
from app.api.utils import ensure_company, get_or_404, update_model
from app.core.permissions import MANAGER_ROLES, ensure_company_access, ensure_role
from app.models.department import Department
from app.models.attachment import Attachment
from app.models.employee import Employee
from app.models.event import Event
from app.models.project import Project, ProjectMember
from app.models.team import Team
from app.models.user import User
from app.models.work_object import WorkObject
from app.schemas.ai_job import AIJobRead
from app.schemas.attachment import AttachmentCreate, AttachmentRead
from app.schemas.event import EventRead
from app.schemas.project import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberRead,
    ProjectOwnerUpdate,
    ProjectPriorityUpdate,
    ProjectRead,
    ProjectStatusUpdate,
    ProjectUpdate,
)
from app.schemas.work_object import WorkObjectRead
from app.services.ai_service import ai_service
from app.services.event_service import EventService
from app.services.file_service import FileService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/projects", tags=["projects"])

PROJECT_STATUSES = {"not_started", "active", "on_hold", "completed", "cancelled", "delayed"}
PROJECT_PRIORITIES = {"low", "medium", "high", "critical"}


def normalize_choice(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")


def clean_code(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def parse_attachment_metadata(raw: str | None) -> dict[str, object]:
    if not raw or not raw.strip():
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Attachment metadata must be valid JSON") from exc
    if not isinstance(value, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Attachment metadata must be an object")
    return value


def ensure_project_status(status_value: str) -> str:
    normalized = normalize_choice(status_value)
    if normalized not in PROJECT_STATUSES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid project status")
    return normalized


def ensure_project_priority(priority_value: str) -> str:
    normalized = normalize_choice(priority_value)
    if normalized not in PROJECT_PRIORITIES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid project priority")
    return normalized


def get_linked_employee(db: Session, current_user: User) -> Employee | None:
    cache_key = f"linked_employee:{current_user.id}"
    if cache_key in db.info:
        return db.info[cache_key]
    employee = db.scalar(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.user_id == current_user.id,
            Employee.is_active.is_(True),
        )
    )
    db.info[cache_key] = employee
    return employee


def actor_employee_id(db: Session, current_user: User) -> UUID | None:
    employee = get_linked_employee(db, current_user)
    return employee.id if employee else None


def validate_project_refs(
    db: Session,
    *,
    company_id: UUID,
    owner_employee_id: UUID | None = None,
    owner_user_id: UUID | None = None,
    department_id: UUID | None = None,
    team_id: UUID | None = None,
) -> None:
    checks: list[tuple[str, object]] = []
    if owner_employee_id is not None:
        checks.append(("Project owner", select(Employee.id).where(Employee.id == owner_employee_id, Employee.company_id == company_id).scalar_subquery()))
    if owner_user_id is not None:
        checks.append(("Project owner user", select(User.id).where(User.id == owner_user_id, User.company_id == company_id).scalar_subquery()))
    if department_id is not None:
        checks.append(("Department", select(Department.id).where(Department.id == department_id, Department.company_id == company_id).scalar_subquery()))
    if team_id is not None:
        checks.append(("Team", select(Team.id).where(Team.id == team_id, Team.company_id == company_id).scalar_subquery()))
    if not checks:
        return
    values = db.execute(select(*(expression for _, expression in checks))).one()
    for index, (label, _) in enumerate(checks):
        if values[index] is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")


def project_member_exists(project_id: UUID, company_id: UUID, employee_id: UUID):
    return (
        select(ProjectMember.id)
        .where(
            ProjectMember.project_id == project_id,
            ProjectMember.company_id == company_id,
            ProjectMember.employee_id == employee_id,
            ProjectMember.is_active.is_(True),
        )
        .exists()
    )


def can_view_project(db: Session, current_user: User, project: Project) -> bool:
    if current_user.role in MANAGER_ROLES:
        return True
    if project.owner_user_id == current_user.id:
        return True
    linked_employee = get_linked_employee(db, current_user)
    if linked_employee is None:
        return False
    if project.owner_employee_id == linked_employee.id:
        return True
    return bool(db.scalar(select(project_member_exists(project.id, project.company_id, linked_employee.id))))


def ensure_project_visible(db: Session, current_user: User, project: Project) -> None:
    if not can_view_project(db, current_user, project):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


def get_project_for_user(db: Session, current_user: User, project_id: UUID, company_id: UUID) -> Project:
    ensure_company_access(current_user, company_id)
    project = get_or_404(db, Project, project_id, label="Project")
    ensure_company(project, company_id, label="Project")
    ensure_project_visible(db, current_user, project)
    return project


def upsert_project_member(
    db: Session,
    *,
    project: Project,
    employee_id: UUID,
    role_on_project: str | None = None,
) -> ProjectMember:
    employee = get_or_404(db, Employee, employee_id, label="Project member")
    ensure_company(employee, project.company_id, label="Project member")
    member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project.id,
            ProjectMember.company_id == project.company_id,
            ProjectMember.employee_id == employee_id,
        )
    )
    if member is None:
        member = ProjectMember(
            project_id=project.id,
            company_id=project.company_id,
            employee_id=employee_id,
            role_on_project=role_on_project,
            is_active=True,
        )
        db.add(member)
        db.flush()
    else:
        member.is_active = True
        if role_on_project is not None:
            member.role_on_project = role_on_project
    return member


def record_project_event(
    db: Session,
    *,
    project: Project,
    current_user: User,
    event_type: str,
    title: str,
    description: str,
    metadata: dict[str, object] | None = None,
) -> Event:
    event_metadata = {"actor_user_id": str(current_user.id)}
    if metadata:
        event_metadata.update(metadata)
    return EventService.record_event(
        db,
        company_id=project.company_id,
        actor_user_id=current_user.id,
        actor_employee_id=actor_employee_id(db, current_user),
        event_type=event_type,
        title=title,
        description=description,
        target_entity_type="project",
        target_entity_id=project.id,
        metadata=event_metadata,
    )


def project_notification_recipients(db: Session, project: Project, actor_employee_id_value: UUID | None = None) -> list[UUID]:
    recipients: list[UUID] = []
    for employee_id in [project.owner_employee_id]:
        if employee_id is not None and employee_id != actor_employee_id_value:
            recipients.append(employee_id)
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


def notify_project_change(
    db: Session,
    *,
    project: Project,
    current_user: User,
    event: Event | None,
    notification_type: str,
    title: str,
    message: str,
    priority: str = "normal",
    metadata: dict[str, object] | None = None,
) -> None:
    actor_id = actor_employee_id(db, current_user)
    recipients = project_notification_recipients(db, project, actor_id)
    if not recipients:
        return
    NotificationService.create_for_employees(
        db,
        company_id=project.company_id,
        recipient_employee_ids=recipients,
        actor_user_id=current_user.id,
        actor_employee_id=actor_id,
        event_id=event.id if event is not None else None,
        title=title,
        message=message,
        notification_type=notification_type,
        target_entity_type="project",
        target_entity_id=project.id,
        priority=priority,
        action_url="#/projects",
        metadata={"project_id": str(project.id), **(metadata or {})},
    )


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Project:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, MANAGER_ROLES)
    validate_project_refs(
        db,
        company_id=payload.company_id,
        owner_employee_id=payload.owner_employee_id,
        owner_user_id=payload.owner_user_id,
        department_id=payload.department_id,
        team_id=payload.team_id,
    )

    project_data = payload.model_dump()
    project_data["status"] = ensure_project_status(payload.status)
    project_data["priority"] = ensure_project_priority(payload.priority)
    project_data["code"] = clean_code(payload.code)
    project = Project(id=uuid4(), **project_data)
    db.add(project)
    if project.owner_employee_id:
        db.add(ProjectMember(
            id=uuid4(),
            project_id=project.id,
            company_id=project.company_id,
            employee_id=project.owner_employee_id,
            role_on_project="Owner",
            is_active=True,
        ))
    record_project_event(
        db,
        project=project,
        current_user=current_user,
        event_type="project.created",
        title=f"{project.name} created",
        description="Project was created.",
        metadata={
            "status": project.status,
            "priority": project.priority,
            "owner_employee_id": str(project.owner_employee_id) if project.owner_employee_id else None,
            "department_id": str(project.department_id) if project.department_id else None,
            "team_id": str(project.team_id) if project.team_id else None,
        },
    )
    db.commit()
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
    status_filter: str | None = Query(default=None, alias="status"),
    include_inactive: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Project]:
    ensure_company_access(current_user, company_id)
    statement = select(Project).where(Project.company_id == company_id)
    if not include_inactive:
        statement = statement.where(Project.is_active.is_(True))
    if status_filter:
        statement = statement.where(Project.status == ensure_project_status(status_filter))
    if current_user.role not in MANAGER_ROLES:
        linked_employee = get_linked_employee(db, current_user)
        visibility_conditions = [Project.owner_user_id == current_user.id]
        if linked_employee is not None:
            visibility_conditions.extend(
                [
                    Project.owner_employee_id == linked_employee.id,
                    project_member_exists(Project.id, company_id, linked_employee.id),
                ]
            )
        statement = statement.where(or_(*visibility_conditions))
    statement = statement.order_by(Project.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Project:
    return get_project_for_user(db, current_user, project_id, company_id)


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: UUID,
    company_id: UUID,
    payload: ProjectUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Project:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, MANAGER_ROLES)
    project = get_or_404(db, Project, project_id, label="Project")
    ensure_company(project, company_id, label="Project")
    validate_project_refs(
        db,
        company_id=company_id,
        owner_employee_id=payload.owner_employee_id,
        owner_user_id=payload.owner_user_id,
        department_id=payload.department_id,
        team_id=payload.team_id,
    )
    previous_status = project.status
    previous_priority = project.priority
    previous_owner_employee_id = project.owner_employee_id
    previous_owner_user_id = project.owner_user_id
    if payload.status is not None:
        payload.status = ensure_project_status(payload.status)
    if payload.priority is not None:
        payload.priority = ensure_project_priority(payload.priority)
    if "code" in payload.model_fields_set:
        payload.code = clean_code(payload.code)
    changed = update_model(project, payload)
    if project.owner_employee_id:
        upsert_project_member(db, project=project, employee_id=project.owner_employee_id, role_on_project="Owner")
    if changed:
        record_project_event(
            db,
            project=project,
            current_user=current_user,
            event_type="project.updated",
            title=f"{project.name} updated",
            description="Project details were updated.",
            metadata={"changed_fields": sorted(changed.keys())},
        )
    owner_changed = (
        ("owner_employee_id" in changed and previous_owner_employee_id != project.owner_employee_id)
        or ("owner_user_id" in changed and previous_owner_user_id != project.owner_user_id)
    )
    if owner_changed:
        record_project_event(
            db,
            project=project,
            current_user=current_user,
            event_type="project.owner_changed",
            title=f"{project.name} owner changed",
            description="Project owner was changed.",
            metadata={
                "from_employee_id": str(previous_owner_employee_id) if previous_owner_employee_id else None,
                "to_employee_id": str(project.owner_employee_id) if project.owner_employee_id else None,
                "from_user_id": str(previous_owner_user_id) if previous_owner_user_id else None,
                "to_user_id": str(project.owner_user_id) if project.owner_user_id else None,
            },
        )
    if "status" in changed and previous_status != project.status:
        status_event = record_project_event(
            db,
            project=project,
            current_user=current_user,
            event_type="project.status_changed",
            title=f"{project.name} status changed",
            description="Project status was changed.",
            metadata={"from": previous_status, "to": project.status},
        )
        notify_project_change(
            db,
            project=project,
            current_user=current_user,
            event=status_event,
            notification_type="project.status_changed",
            title=f"{project.name} status changed",
            message=f"Project status changed from {previous_status} to {project.status}.",
            metadata={"from": previous_status, "to": project.status},
        )
    if "priority" in changed and previous_priority != project.priority:
        priority_event = record_project_event(
            db,
            project=project,
            current_user=current_user,
            event_type="project.priority_changed",
            title=f"{project.name} priority changed",
            description="Project priority was changed.",
            metadata={"from": previous_priority, "to": project.priority},
        )
        if project.priority in {"high", "critical"}:
            notify_project_change(
                db,
                project=project,
                current_user=current_user,
                event=priority_event,
                notification_type="project.priority_changed",
                title=f"{project.name} priority changed",
                message=f"Project priority changed from {previous_priority} to {project.priority}.",
                priority="high" if project.priority == "high" else "urgent",
                metadata={"from": previous_priority, "to": project.priority},
            )
    db.commit()
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_project(
    project_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, MANAGER_ROLES)
    project = get_or_404(db, Project, project_id, label="Project")
    ensure_company(project, company_id, label="Project")
    project.is_active = False
    status_event = record_project_event(
        db,
        project=project,
        current_user=current_user,
        event_type="project.archived",
        title=f"{project.name} archived",
        description="Project was archived.",
        metadata={"status": project.status},
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{project_id}/status", response_model=ProjectRead)
def change_project_status(
    project_id: UUID,
    payload: ProjectStatusUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Project:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, MANAGER_ROLES)
    project = get_or_404(db, Project, project_id, label="Project")
    ensure_company(project, payload.company_id, label="Project")
    previous_status = project.status
    project.status = ensure_project_status(payload.status)
    status_event = record_project_event(
        db,
        project=project,
        current_user=current_user,
        event_type="project.status_changed",
        title=f"{project.name} status changed",
        description="Project status was changed.",
        metadata={"from": previous_status, "to": project.status},
    )
    notify_project_change(
        db,
        project=project,
        current_user=current_user,
        event=status_event,
        notification_type="project.status_changed",
        title=f"{project.name} status changed",
        message=f"Project status changed from {previous_status} to {project.status}.",
        metadata={"from": previous_status, "to": project.status},
    )
    db.commit()
    return project


@router.patch("/{project_id}/priority", response_model=ProjectRead)
def change_project_priority(
    project_id: UUID,
    payload: ProjectPriorityUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Project:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, MANAGER_ROLES)
    project = get_or_404(db, Project, project_id, label="Project")
    ensure_company(project, payload.company_id, label="Project")
    previous_priority = project.priority
    project.priority = ensure_project_priority(payload.priority)
    priority_event = record_project_event(
        db,
        project=project,
        current_user=current_user,
        event_type="project.priority_changed",
        title=f"{project.name} priority changed",
        description="Project priority was changed.",
        metadata={"from": previous_priority, "to": project.priority},
    )
    if project.priority in {"high", "critical"}:
        notify_project_change(
            db,
            project=project,
            current_user=current_user,
            event=priority_event,
            notification_type="project.priority_changed",
            title=f"{project.name} priority changed",
            message=f"Project priority changed from {previous_priority} to {project.priority}.",
            priority="high" if project.priority == "high" else "urgent",
            metadata={"from": previous_priority, "to": project.priority},
        )
    db.commit()
    return project


@router.patch("/{project_id}/owner", response_model=ProjectRead)
def change_project_owner(
    project_id: UUID,
    payload: ProjectOwnerUpdate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Project:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, MANAGER_ROLES)
    project = get_or_404(db, Project, project_id, label="Project")
    ensure_company(project, payload.company_id, label="Project")
    validate_project_refs(
        db,
        company_id=payload.company_id,
        owner_employee_id=payload.owner_employee_id,
        owner_user_id=payload.owner_user_id,
    )
    previous_owner_employee_id = project.owner_employee_id
    project.owner_employee_id = payload.owner_employee_id
    project.owner_user_id = payload.owner_user_id
    if project.owner_employee_id:
        upsert_project_member(db, project=project, employee_id=project.owner_employee_id, role_on_project="Owner")
    member_event = record_project_event(
        db,
        project=project,
        current_user=current_user,
        event_type="project.owner_changed",
        title=f"{project.name} owner changed",
        description="Project owner was changed.",
        metadata={
            "from": str(previous_owner_employee_id) if previous_owner_employee_id else None,
            "to": str(project.owner_employee_id) if project.owner_employee_id else None,
            "owner_user_id": str(project.owner_user_id) if project.owner_user_id else None,
        },
    )
    db.commit()
    return project


@router.get("/{project_id}/members", response_model=list[ProjectMemberRead])
def get_project_members(
    project_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
    include_inactive: bool = False,
) -> list[ProjectMember]:
    project = get_project_for_user(db, current_user, project_id, company_id)
    statement = select(ProjectMember).where(
        ProjectMember.company_id == company_id,
        ProjectMember.project_id == project.id,
    )
    if not include_inactive:
        statement = statement.where(ProjectMember.is_active.is_(True))
    statement = statement.order_by(ProjectMember.created_at.asc())
    return list(db.scalars(statement).all())


@router.post("/{project_id}/members", response_model=ProjectMemberRead, status_code=status.HTTP_201_CREATED)
def add_project_member(
    project_id: UUID,
    payload: ProjectMemberCreate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> ProjectMember:
    ensure_company_access(current_user, payload.company_id)
    ensure_role(current_user, MANAGER_ROLES)
    project = get_or_404(db, Project, project_id, label="Project")
    ensure_company(project, payload.company_id, label="Project")
    member = upsert_project_member(
        db,
        project=project,
        employee_id=payload.employee_id,
        role_on_project=payload.role_on_project,
    )
    member_event = record_project_event(
        db,
        project=project,
        current_user=current_user,
        event_type="project.member_added",
        title=f"Member added to {project.name}",
        description="Project member was added.",
        metadata={"employee_id": str(payload.employee_id), "role_on_project": payload.role_on_project},
    )
    actor_id = actor_employee_id(db, current_user)
    if payload.employee_id != actor_id:
        NotificationService.create_notification(
            db,
            company_id=project.company_id,
            recipient_employee_id=payload.employee_id,
            actor_user_id=current_user.id,
            actor_employee_id=actor_id,
            event_id=member_event.id,
            title=f"Added to {project.name}",
            message="You were added as a project member.",
            notification_type="project.member_added",
            target_entity_type="project",
            target_entity_id=project.id,
            priority="normal",
            action_url="#/projects",
            metadata={"project_id": str(project.id), "role_on_project": payload.role_on_project},
        )
    if project.owner_employee_id is not None and project.owner_employee_id not in {payload.employee_id, actor_id}:
        NotificationService.create_notification(
            db,
            company_id=project.company_id,
            recipient_employee_id=project.owner_employee_id,
            actor_user_id=current_user.id,
            actor_employee_id=actor_id,
            event_id=member_event.id,
            title=f"Member added to {project.name}",
            message="A project member was added.",
            notification_type="project.member_added",
            target_entity_type="project",
            target_entity_id=project.id,
            priority="normal",
            action_url="#/projects",
            metadata={"project_id": str(project.id), "employee_id": str(payload.employee_id)},
        )
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{project_id}/members/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_member(
    project_id: UUID,
    employee_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    ensure_company_access(current_user, company_id)
    ensure_role(current_user, MANAGER_ROLES)
    project = get_or_404(db, Project, project_id, label="Project")
    ensure_company(project, company_id, label="Project")
    employee = get_or_404(db, Employee, employee_id, label="Project member")
    ensure_company(employee, company_id, label="Project member")
    member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.company_id == company_id,
            ProjectMember.project_id == project_id,
            ProjectMember.employee_id == employee_id,
        )
    )
    if member is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    member.is_active = False
    remove_event = record_project_event(
        db,
        project=project,
        current_user=current_user,
        event_type="project.member_removed",
        title=f"Member removed from {project.name}",
        description="Project member was removed.",
        metadata={"employee_id": str(employee_id)},
    )
    actor_id = actor_employee_id(db, current_user)
    if employee_id != actor_id:
        NotificationService.create_notification(
            db,
            company_id=project.company_id,
            recipient_employee_id=employee_id,
            actor_user_id=current_user.id,
            actor_employee_id=actor_id,
            event_id=remove_event.id,
            title=f"Removed from {project.name}",
            message="You were removed as a project member.",
            notification_type="project.member_removed",
            target_entity_type="project",
            target_entity_id=project.id,
            priority="normal",
            action_url="#/projects",
            metadata={"project_id": str(project.id)},
        )
    if project.owner_employee_id is not None and project.owner_employee_id not in {employee_id, actor_id}:
        NotificationService.create_notification(
            db,
            company_id=project.company_id,
            recipient_employee_id=project.owner_employee_id,
            actor_user_id=current_user.id,
            actor_employee_id=actor_id,
            event_id=remove_event.id,
            title=f"Member removed from {project.name}",
            message="A project member was removed.",
            notification_type="project.member_removed",
            target_entity_type="project",
            target_entity_id=project.id,
            priority="normal",
            action_url="#/projects",
            metadata={"project_id": str(project.id), "employee_id": str(employee_id)},
        )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{project_id}/ai-summary", response_model=AIJobRead)
def generate_project_ai_summary(
    project_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJobRead:
    project = get_project_for_user(db, current_user, project_id, company_id)
    job = ai_service.generate_summary(
        db,
        company_id=company_id,
        job_type="project_summary_safe",
        input_entity_type="project",
        input_entity_id=project.id,
        current_user=current_user,
    )
    db.commit()
    db.refresh(job)
    return job


@router.get("/{project_id}/ai-summary/latest", response_model=AIJobRead | None)
def get_latest_project_ai_summary(
    project_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> AIJobRead | None:
    project = get_project_for_user(db, current_user, project_id, company_id)
    return ai_service.latest_summary_job(
        db,
        company_id=company_id,
        job_type="project_summary_safe",
        input_entity_type="project",
        input_entity_id=project.id,
        current_user=current_user,
    )


@router.get("/{project_id}/timeline", response_model=list[EventRead])
def get_project_timeline(
    project_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[EventRead]:
    project = get_project_for_user(db, current_user, project_id, company_id)
    statement = (
        select(Event)
        .where(
            Event.company_id == company_id,
            Event.target_entity_type == "project",
            Event.target_entity_id == project.id,
        )
        .order_by(Event.created_at.desc())
        .limit(limit)
    )
    return serialize_events(db.scalars(statement).all())


@router.post("/{project_id}/attachments", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
def add_project_attachment(
    project_id: UUID,
    company_id: UUID = Form(...),
    file: UploadFile = File(...),
    description: str | None = Form(default=None),
    metadata: str | None = Form(default=None),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Attachment:
    project = get_project_for_user(db, current_user, project_id, company_id)
    actor_id = actor_employee_id(db, current_user)
    stored_file = FileService.save_upload(
        file=file,
        company_id=company_id,
        linked_entity_type="project",
        linked_entity_id=project.id,
    )
    attachment = FileService.build_attachment(
        AttachmentCreate(
            company_id=company_id,
            project_id=project.id,
            uploaded_by_user_id=current_user.id,
            uploaded_by_employee_id=actor_id,
            linked_entity_type="project",
            linked_entity_id=project.id,
            file_name=stored_file.file_name,
            original_file_name=stored_file.original_file_name,
            content_type=stored_file.content_type,
            file_size=stored_file.file_size,
            extension=stored_file.extension,
            checksum_sha256=stored_file.checksum_sha256,
            storage_provider=stored_file.storage_provider,
            storage_path=stored_file.storage_path,
            public_url=None,
            description=description.strip() if description else None,
            tags=[],
            processing_status="uploaded",
            scan_status="not_scanned",
            metadata=parse_attachment_metadata(metadata),
            ai_processing_status="pending",
            is_active=True,
        )
    )
    db.add(attachment)
    db.flush()
    event = EventService.record_event(
        db,
        company_id=company_id,
        actor_user_id=current_user.id,
        actor_employee_id=actor_id,
        event_type="file.uploaded",
        title=f"{attachment.original_file_name} uploaded",
        description="File was uploaded to a project.",
        target_entity_type="attachment",
        target_entity_id=attachment.id,
        related_entity_type="project",
        related_entity_id=project.id,
        metadata={"attachment_id": str(attachment.id), "project_id": str(project.id), "content_type": attachment.content_type, "file_size": attachment.file_size},
    )
    notify_project_change(
        db,
        project=project,
        current_user=current_user,
        event=event,
        notification_type="file.uploaded",
        title=f"{attachment.original_file_name} uploaded",
        message=f"A file was uploaded to {project.name}.",
        metadata={"attachment_id": str(attachment.id), "project_id": str(project.id)},
    )
    db.commit()
    db.refresh(attachment)
    return attachment


@router.get("/{project_id}/attachments", response_model=list[AttachmentRead])
def list_project_attachments(
    project_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Attachment]:
    project = get_project_for_user(db, current_user, project_id, company_id)
    statement = (
        select(Attachment)
        .where(
            Attachment.company_id == company_id,
            Attachment.project_id == project.id,
            Attachment.is_active.is_(True),
            Attachment.is_deleted.is_(False),
        )
        .order_by(Attachment.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())


@router.get("/{project_id}/work-objects", response_model=list[WorkObjectRead])
def get_project_work_objects(
    project_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[WorkObject]:
    project = get_project_for_user(db, current_user, project_id, company_id)
    statement = (
        select(WorkObject)
        .where(
            WorkObject.company_id == company_id,
            WorkObject.project_id == project.id,
            WorkObject.is_active.is_(True),
        )
    )
    if current_user.role not in MANAGER_ROLES:
        linked_employee = get_linked_employee(db, current_user)
        visibility_conditions = [WorkObject.creator_user_id == current_user.id]
        if linked_employee is not None:
            visibility_conditions.extend(
                [
                    WorkObject.assignee_employee_id == linked_employee.id,
                    WorkObject.creator_employee_id == linked_employee.id,
                ]
            )
        statement = statement.where(or_(*visibility_conditions))
    statement = statement.order_by(WorkObject.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())
