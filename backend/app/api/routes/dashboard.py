from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_optional_current_user
from app.api.serializers import serialize_events
from app.api.utils import get_or_404
from app.core.permissions import OWNER_ADMIN_ROLES, ensure_company_access
from app.models.attachment import Attachment
from app.models.ai_job import AIJob
from app.models.communication import Announcement
from app.models.company import Company
from app.models.company_memory import CompanyMemory
from app.models.employee import Employee
from app.models.employee_digital_twin import EmployeeDigitalTwinSnapshot
from app.models.event import Event
from app.models.leave_request import LeaveRequest
from app.models.notification import Notification
from app.models.project import Project
from app.models.user import User
from app.models.work_dna import WorkDNASnapshot
from app.models.work_object import WorkObject
from app.schemas.dashboard import (
    DashboardAnnouncementSummary,
    DashboardCompanyOverview,
    DashboardEmployeeSummary,
    DashboardFileSummary,
    DashboardIntelligenceSummary,
    DashboardLeaveSummary,
    DashboardMemorySummary,
    DashboardNotificationSummary,
    DashboardProjectSummary,
    DashboardSummaryRead,
    DashboardWorkSummary,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

OPEN_WORK_STATUSES = {"assigned", "pending", "in_progress", "under_review", "blocked"}


def grouped_counts(db: Session, model: type, company_id: UUID, **conditions: object) -> dict[str, int]:
    """Fetch related dashboard counters in one database round trip."""
    statement = select(
        *(func.count().filter(condition).label(name) for name, condition in conditions.items())
    ).select_from(model).where(model.company_id == company_id)
    row = db.execute(statement).one()
    return {name: int(row._mapping[name] or 0) for name in conditions}


def get_linked_employee(db: Session, current_user: User | None) -> Employee | None:
    if current_user is None:
        return None
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


def notification_visibility_conditions(db: Session, current_user: User | None) -> list[object]:
    if current_user is None:
        return []
    conditions: list[object] = [Notification.recipient_user_id == current_user.id]
    linked_employee = get_linked_employee(db, current_user)
    if linked_employee is not None:
        conditions.append(Notification.recipient_employee_id == linked_employee.id)
    if current_user.role in OWNER_ADMIN_ROLES:
        conditions.append(and_(Notification.recipient_user_id.is_(None), Notification.recipient_employee_id.is_(None)))
    return conditions


def apply_notification_visibility(statement, db: Session, current_user: User | None):
    conditions = notification_visibility_conditions(db, current_user)
    if conditions:
        return statement.where(or_(*conditions))
    return statement


@router.get("/summary", response_model=DashboardSummaryRead)
def get_dashboard_summary(
    company_id: UUID,
    db: Session = Depends(db_session),
    current_user: User | None = Depends(get_optional_current_user),
) -> DashboardSummaryRead:
    ensure_company_access(current_user, company_id)
    if current_user is not None and current_user.role == "employee":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Employees use the employee dashboard")
    company = get_or_404(db, Company, company_id, label="Company")
    now = datetime.now(timezone.utc)
    today = date.today()
    today_start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    tomorrow_start = today_start + timedelta(days=1)
    seven_days_ago = now - timedelta(days=7)

    active_work = WorkObject.is_active.is_(True)
    open_work = WorkObject.status.in_(OPEN_WORK_STATUSES)

    notification_counts_statement = select(
        func.count().filter(
            Notification.is_read.is_(False),
            Notification.is_dismissed.is_(False),
        ).label("unread"),
        func.count().filter(
            Notification.priority.in_(["high", "urgent"]),
            Notification.is_dismissed.is_(False),
        ).label("important"),
    ).select_from(Notification).where(Notification.company_id == company_id)
    notification_counts_statement = apply_notification_visibility(notification_counts_statement, db, current_user)
    notification_counts = db.execute(notification_counts_statement).one()._mapping
    unread_notifications = int(notification_counts["unread"] or 0)
    important_notifications = int(notification_counts["important"] or 0)

    employee_counts = grouped_counts(
        db,
        Employee,
        company_id,
        total_employees=Employee.id.is_not(None),
        active_employees=Employee.is_active.is_(True),
        available_employees=and_(Employee.is_active.is_(True), Employee.status == "available"),
        on_leave_employees=and_(Employee.is_active.is_(True), Employee.status == "on_leave"),
        busy_employees=and_(Employee.is_active.is_(True), Employee.status == "busy"),
        inactive_employees=Employee.is_active.is_(False),
    )
    employee_summary = DashboardEmployeeSummary(**employee_counts)

    work_counts = grouped_counts(
        db,
        WorkObject,
        company_id,
        total_work_objects=active_work,
        pending_or_assigned=and_(active_work, WorkObject.status.in_(["pending", "assigned"])),
        in_progress=and_(active_work, WorkObject.status == "in_progress"),
        blocked=and_(active_work, WorkObject.status == "blocked"),
        under_review=and_(active_work, WorkObject.status == "under_review"),
        completed=and_(active_work, WorkObject.status == "completed"),
        overdue=and_(active_work, open_work, WorkObject.due_date.is_not(None), WorkObject.due_date < today_start),
        due_today=and_(active_work, open_work, WorkObject.due_date >= today_start, WorkObject.due_date < tomorrow_start),
        high_or_critical_priority=and_(active_work, WorkObject.priority.in_(["high", "critical"])),
    )
    work_summary = DashboardWorkSummary(**work_counts)

    active_project = Project.is_active.is_(True)
    project_counts_statement = select(
        func.count().filter(active_project).label("total_projects"),
        func.count().filter(active_project, Project.status == "active").label("active_projects"),
        func.count().filter(active_project, Project.status == "on_hold").label("on_hold_projects"),
        func.count().filter(active_project, Project.status == "delayed").label("delayed_projects"),
        func.count().filter(active_project, Project.status == "completed").label("completed_projects"),
        func.count().filter(active_project, Project.priority.in_(["high", "critical"])).label("high_priority_projects"),
        func.coalesce(func.avg(Project.progress_percent).filter(active_project), 0).label("average_progress"),
    ).where(Project.company_id == company_id)
    project_counts = db.execute(project_counts_statement).one()._mapping
    project_summary = DashboardProjectSummary(
        total_projects=int(project_counts["total_projects"] or 0),
        active_projects=int(project_counts["active_projects"] or 0),
        on_hold_projects=int(project_counts["on_hold_projects"] or 0),
        delayed_projects=int(project_counts["delayed_projects"] or 0),
        completed_projects=int(project_counts["completed_projects"] or 0),
        high_priority_projects=int(project_counts["high_priority_projects"] or 0),
        average_progress=round(float(project_counts["average_progress"] or 0), 1),
    )

    active_leave = LeaveRequest.is_active.is_(True)
    leave_counts = grouped_counts(
        db,
        LeaveRequest,
        company_id,
        total_leave_requests=active_leave,
        pending_leave_requests=and_(active_leave, LeaveRequest.status == "pending"),
        approved_leave_requests=and_(active_leave, LeaveRequest.status == "approved"),
        rejected_leave_requests=and_(active_leave, LeaveRequest.status == "rejected"),
        cancelled_leave_requests=and_(active_leave, LeaveRequest.status == "cancelled"),
        upcoming_approved_leaves=and_(active_leave, LeaveRequest.status == "approved", LeaveRequest.start_date >= today),
    )
    leave_summary = DashboardLeaveSummary(**leave_counts)

    file_counts = grouped_counts(
        db,
        Attachment,
        company_id,
        total_attachments=Attachment.is_active.is_(True),
        recent_uploads_count=and_(Attachment.is_active.is_(True), Attachment.created_at >= seven_days_ago),
    )
    file_summary = DashboardFileSummary(**file_counts)

    notification_summary = DashboardNotificationSummary(
        unread_notifications=unread_notifications,
        important_notifications=important_notifications,
    )

    published_announcement = and_(Announcement.is_archived.is_(False), Announcement.is_published.is_(True))
    announcement_counts = grouped_counts(
        db,
        Announcement,
        company_id,
        active_announcements=published_announcement,
        urgent_announcements=and_(published_announcement, Announcement.priority == "urgent"),
    )
    announcement_summary = DashboardAnnouncementSummary(**announcement_counts)

    memory_counts = grouped_counts(
        db,
        CompanyMemory,
        company_id,
        approved_memories=CompanyMemory.status == "approved",
        pending_suggestions=CompanyMemory.status == "suggested",
        important_memories=and_(CompanyMemory.status == "approved", CompanyMemory.importance.in_(["high", "critical"])),
    )
    memory_summary = DashboardMemorySummary(**memory_counts)

    intelligence_summary: DashboardIntelligenceSummary | None = None
    if current_user is not None and current_user.role in OWNER_ADMIN_ROLES:
        latest_work_dna = db.scalar(
            select(WorkDNASnapshot)
            .where(WorkDNASnapshot.company_id == company_id)
            .order_by(WorkDNASnapshot.created_at.desc())
            .limit(1)
        )
        recent_twin_employee_count = int(
            db.scalar(
                select(func.count(func.distinct(EmployeeDigitalTwinSnapshot.employee_id)))
                .join(Employee, Employee.id == EmployeeDigitalTwinSnapshot.employee_id)
                .where(
                    EmployeeDigitalTwinSnapshot.company_id == company_id,
                    Employee.company_id == company_id,
                    Employee.is_active.is_(True),
                    EmployeeDigitalTwinSnapshot.created_at >= now - timedelta(days=30),
                )
            )
            or 0
        )
        active_employee_count = employee_summary.active_employees
        ai_counts = grouped_counts(
            db,
            AIJob,
            company_id,
            queued=AIJob.status == "queued",
            running=AIJob.status == "running",
            failed=AIJob.status == "failed",
            cancelled=AIJob.status == "cancelled",
        )
        intelligence_summary = DashboardIntelligenceSummary(
            latest_work_dna_scope=latest_work_dna.scope_type if latest_work_dna is not None else None,
            latest_work_dna_generated_at=latest_work_dna.created_at if latest_work_dna is not None else None,
            latest_work_dna_bottlenecks=len(latest_work_dna.bottlenecks_json or []) if latest_work_dna is not None else 0,
            latest_work_dna_recurring_patterns=len(latest_work_dna.recurring_patterns_json or []) if latest_work_dna is not None else 0,
            latest_work_dna_template_candidates=len(latest_work_dna.template_candidates_json or []) if latest_work_dna is not None else 0,
            employee_twins_recent_count=recent_twin_employee_count,
            employee_twins_missing_recent_count=max(active_employee_count - recent_twin_employee_count, 0),
            ai_queued_jobs=ai_counts["queued"],
            ai_running_jobs=ai_counts["running"],
            ai_failed_jobs=ai_counts["failed"],
            ai_cancelled_jobs=ai_counts["cancelled"],
        )

    recent_events = serialize_events(
        db.scalars(
            select(Event)
            .where(Event.company_id == company_id)
            .order_by(Event.created_at.desc())
            .limit(8)
        ).all()
    )

    recent_notifications_statement = (
        select(Notification)
        .where(
            Notification.company_id == company_id,
            Notification.is_dismissed.is_(False),
            or_(Notification.is_read.is_(False), Notification.priority.in_(["high", "urgent"])),
        )
        .order_by(Notification.created_at.desc())
        .limit(8)
    )
    recent_notifications_statement = apply_notification_visibility(recent_notifications_statement, db, current_user)

    priority_work = db.scalars(
        select(WorkObject)
        .where(
            WorkObject.company_id == company_id,
            WorkObject.is_active.is_(True),
            or_(
                WorkObject.status == "blocked",
                WorkObject.priority.in_(["high", "critical"]),
                and_(WorkObject.due_date.is_not(None), WorkObject.due_date < tomorrow_start, open_work),
            ),
        )
        .order_by(WorkObject.due_date.asc().nullslast(), WorkObject.updated_at.desc())
        .limit(8)
    ).all()

    project_health_list = db.scalars(
        select(Project)
        .where(
            Project.company_id == company_id,
            Project.is_active.is_(True),
            Project.status.in_(["active", "on_hold", "delayed"]),
        )
        .order_by(Project.priority.desc(), Project.updated_at.desc())
        .limit(8)
    ).all()

    leave_attention_list = db.scalars(
        select(LeaveRequest)
        .where(
            LeaveRequest.company_id == company_id,
            LeaveRequest.is_active.is_(True),
            or_(
                LeaveRequest.status == "pending",
                and_(LeaveRequest.status == "approved", LeaveRequest.start_date >= today),
            ),
        )
        .order_by(LeaveRequest.status.desc(), LeaveRequest.start_date.asc())
        .limit(8)
    ).all()

    recent_announcements = db.scalars(
        select(Announcement)
        .where(
            Announcement.company_id == company_id,
            Announcement.is_archived.is_(False),
            Announcement.is_published.is_(True),
        )
        .order_by(Announcement.published_at.desc().nullslast(), Announcement.created_at.desc())
        .limit(5)
    ).all()

    return DashboardSummaryRead(
        company_overview=DashboardCompanyOverview(company_id=company.id, company_name=company.name, generated_at=now),
        employee_summary=employee_summary,
        work_summary=work_summary,
        project_summary=project_summary,
        leave_summary=leave_summary,
        file_summary=file_summary,
        notification_summary=notification_summary,
        announcement_summary=announcement_summary,
        memory_summary=memory_summary,
        intelligence_summary=intelligence_summary,
        recent_events=recent_events,
        recent_notifications=list(db.scalars(recent_notifications_statement).all()),
        recent_announcements=list(recent_announcements),
        priority_work=list(priority_work),
        project_health_list=list(project_health_list),
        leave_attention_list=list(leave_attention_list),
    )
