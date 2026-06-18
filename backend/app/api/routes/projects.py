from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.api.utils import ensure_company, get_or_404, update_model
from app.models.company import Company
from app.models.employee import Employee
from app.models.event import Event
from app.models.project import Project
from app.models.work_object import WorkObject
from app.schemas.event import EventRead
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.schemas.work_object import WorkObjectRead
from app.services.event_service import EventService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(db_session)) -> Project:
    get_or_404(db, Company, payload.company_id, label="Company")
    if payload.owner_employee_id:
        owner = get_or_404(db, Employee, payload.owner_employee_id, label="Project owner")
        ensure_company(owner, payload.company_id, label="Project owner")

    project = Project(**payload.model_dump())
    db.add(project)
    db.flush()
    EventService.record_event(
        db,
        company_id=project.company_id,
        actor_employee_id=project.owner_employee_id,
        event_type="project.created",
        title=f"{project.name} created",
        target_entity_type="project",
        target_entity_id=project.id,
        metadata={"status": project.status, "priority": project.priority},
    )
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(
    company_id: UUID,
    db: Session = Depends(db_session),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Project]:
    statement = select(Project).where(Project.company_id == company_id)
    if status_filter:
        statement = statement.where(Project.status == status_filter)
    statement = statement.order_by(Project.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(statement).all())


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: UUID, company_id: UUID, db: Session = Depends(db_session)) -> Project:
    project = get_or_404(db, Project, project_id, label="Project")
    ensure_company(project, company_id, label="Project")
    return project


@router.put("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: UUID,
    company_id: UUID,
    payload: ProjectUpdate,
    db: Session = Depends(db_session),
) -> Project:
    project = get_or_404(db, Project, project_id, label="Project")
    ensure_company(project, company_id, label="Project")
    if payload.owner_employee_id:
        owner = get_or_404(db, Employee, payload.owner_employee_id, label="Project owner")
        ensure_company(owner, company_id, label="Project owner")
    changed = update_model(project, payload)
    if changed:
        EventService.record_event(
            db,
            company_id=company_id,
            actor_employee_id=project.owner_employee_id,
            event_type="project.updated",
            title=f"{project.name} updated",
            target_entity_type="project",
            target_entity_id=project.id,
            metadata={"changed_fields": sorted(changed.keys())},
        )
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    company_id: UUID,
    actor_employee_id: UUID | None = None,
    db: Session = Depends(db_session),
) -> Response:
    project = get_or_404(db, Project, project_id, label="Project")
    ensure_company(project, company_id, label="Project")
    EventService.record_event(
        db,
        company_id=company_id,
        actor_employee_id=actor_employee_id,
        event_type="project.deleted",
        title=f"{project.name} deleted",
        target_entity_type="project",
        target_entity_id=project.id,
    )
    db.delete(project)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}/timeline", response_model=list[EventRead])
def get_project_timeline(
    project_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Event]:
    project = get_or_404(db, Project, project_id, label="Project")
    ensure_company(project, company_id, label="Project")
    statement = (
        select(Event)
        .where(
            Event.company_id == company_id,
            Event.target_entity_type == "project",
            Event.target_entity_id == project_id,
        )
        .order_by(Event.created_at.desc())
        .limit(limit)
    )
    return list(db.scalars(statement).all())


@router.get("/{project_id}/work-objects", response_model=list[WorkObjectRead])
def get_project_work_objects(
    project_id: UUID,
    company_id: UUID,
    db: Session = Depends(db_session),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[WorkObject]:
    project = get_or_404(db, Project, project_id, label="Project")
    ensure_company(project, company_id, label="Project")
    statement = (
        select(WorkObject)
        .where(WorkObject.company_id == company_id, WorkObject.project_id == project_id)
        .order_by(WorkObject.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement).all())
