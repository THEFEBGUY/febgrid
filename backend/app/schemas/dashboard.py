from datetime import datetime
from uuid import UUID

from app.schemas.common import FebGridModel
from app.schemas.communication import AnnouncementRead
from app.schemas.event import EventRead
from app.schemas.leave_request import LeaveRequestRead
from app.schemas.notification import NotificationRead
from app.schemas.project import ProjectRead
from app.schemas.work_object import WorkObjectRead


class DashboardCompanyOverview(FebGridModel):
    company_id: UUID
    company_name: str
    generated_at: datetime


class DashboardEmployeeSummary(FebGridModel):
    total_employees: int
    active_employees: int
    available_employees: int
    on_leave_employees: int
    busy_employees: int
    inactive_employees: int


class DashboardWorkSummary(FebGridModel):
    total_work_objects: int
    pending_or_assigned: int
    in_progress: int
    blocked: int
    under_review: int
    completed: int
    overdue: int
    due_today: int
    high_or_critical_priority: int


class DashboardProjectSummary(FebGridModel):
    total_projects: int
    active_projects: int
    on_hold_projects: int
    delayed_projects: int
    completed_projects: int
    high_priority_projects: int
    average_progress: float


class DashboardLeaveSummary(FebGridModel):
    total_leave_requests: int
    pending_leave_requests: int
    approved_leave_requests: int
    rejected_leave_requests: int
    cancelled_leave_requests: int
    upcoming_approved_leaves: int


class DashboardFileSummary(FebGridModel):
    total_attachments: int
    recent_uploads_count: int


class DashboardNotificationSummary(FebGridModel):
    unread_notifications: int
    important_notifications: int


class DashboardAnnouncementSummary(FebGridModel):
    active_announcements: int
    urgent_announcements: int


class DashboardMemorySummary(FebGridModel):
    approved_memories: int
    pending_suggestions: int
    important_memories: int


class DashboardSummaryRead(FebGridModel):
    company_overview: DashboardCompanyOverview
    employee_summary: DashboardEmployeeSummary
    work_summary: DashboardWorkSummary
    project_summary: DashboardProjectSummary
    leave_summary: DashboardLeaveSummary
    file_summary: DashboardFileSummary
    notification_summary: DashboardNotificationSummary
    announcement_summary: DashboardAnnouncementSummary
    memory_summary: DashboardMemorySummary
    recent_events: list[EventRead]
    recent_notifications: list[NotificationRead]
    recent_announcements: list[AnnouncementRead]
    priority_work: list[WorkObjectRead]
    project_health_list: list[ProjectRead]
    leave_attention_list: list[LeaveRequestRead]
