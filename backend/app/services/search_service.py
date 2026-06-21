from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.attachment import Attachment
from app.models.employee import Employee
from app.models.event import Event
from app.models.project import Project
from app.models.work_object import WorkObject
from app.schemas.search import SearchResponse, SearchResult


class SearchService:
    @staticmethod
    def search(db: Session, *, company_id: UUID, query: str, limit: int = 25) -> SearchResponse:
        term = f"%{query.strip()}%"
        results: list[SearchResult] = []

        employees = db.scalars(
            select(Employee)
            .where(
                Employee.company_id == company_id,
                or_(Employee.full_name.ilike(term), Employee.email.ilike(term), Employee.role.ilike(term)),
            )
            .limit(limit)
        ).all()
        results.extend(
            SearchResult(
                type="employee",
                id=str(employee.id),
                title=employee.full_name,
                subtitle=employee.role,
                metadata={"status": employee.status, "department": employee.department},
            )
            for employee in employees
        )

        projects = db.scalars(
            select(Project)
            .where(
                Project.company_id == company_id,
                Project.is_active.is_(True),
                or_(Project.name.ilike(term), Project.code.ilike(term), Project.description.ilike(term)),
            )
            .limit(limit)
        ).all()
        results.extend(
            SearchResult(
                type="project",
                id=str(project.id),
                title=project.name,
                subtitle=project.status,
                metadata={"priority": project.priority, "code": project.code, "risk_level": project.risk_level},
            )
            for project in projects
        )

        work_objects = db.scalars(
            select(WorkObject)
            .where(
                WorkObject.company_id == company_id,
                WorkObject.is_active.is_(True),
                or_(
                    WorkObject.title.ilike(term),
                    WorkObject.description.ilike(term),
                    WorkObject.object_type.ilike(term),
                ),
            )
            .limit(limit)
        ).all()
        results.extend(
            SearchResult(
                type="work_object",
                id=str(work_object.id),
                title=work_object.title,
                subtitle=work_object.status,
                metadata={
                    "priority": work_object.priority,
                    "object_type": work_object.object_type,
                    "project_id": str(work_object.project_id) if work_object.project_id else None,
                    "assignee_employee_id": str(work_object.assignee_employee_id) if work_object.assignee_employee_id else None,
                },
            )
            for work_object in work_objects
        )

        attachments = db.scalars(
            select(Attachment)
            .where(
                Attachment.company_id == company_id,
                or_(Attachment.file_name.ilike(term), Attachment.file_type.ilike(term)),
            )
            .limit(limit)
        ).all()
        results.extend(
            SearchResult(
                type="attachment",
                id=str(attachment.id),
                title=attachment.file_name,
                subtitle=attachment.linked_entity_type,
                metadata={"ai_processing_status": attachment.ai_processing_status},
            )
            for attachment in attachments
        )

        events = db.scalars(
            select(Event)
            .where(Event.company_id == company_id, or_(Event.title.ilike(term), Event.event_type.ilike(term)))
            .order_by(Event.created_at.desc())
            .limit(limit)
        ).all()
        results.extend(
            SearchResult(
                type="event",
                id=str(event.id),
                title=event.title,
                subtitle=event.event_type,
                metadata={"created_at": event.created_at.isoformat()},
            )
            for event in events
        )

        return SearchResponse(query=query, results=results[:limit])
