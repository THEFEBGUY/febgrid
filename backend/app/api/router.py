from fastapi import APIRouter

from app.api.routes import (
    attachments,
    ai_jobs,
    companies,
    employees,
    events,
    health,
    leaves,
    notifications,
    projects,
    search,
    teams,
    work_objects,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(companies.router)
api_router.include_router(employees.router)
api_router.include_router(teams.router)
api_router.include_router(projects.router)
api_router.include_router(work_objects.router)
api_router.include_router(leaves.router)
api_router.include_router(leaves.employee_router)
api_router.include_router(attachments.router)
api_router.include_router(attachments.uploads_router)
api_router.include_router(attachments.files_router)
api_router.include_router(events.router)
api_router.include_router(events.timeline_router)
api_router.include_router(notifications.router)
api_router.include_router(ai_jobs.router)
api_router.include_router(search.router)
