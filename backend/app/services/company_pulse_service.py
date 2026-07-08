from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.permissions import OWNER_ADMIN_ROLES, ensure_company_access, ensure_role
from app.models.ai_job import AIJob
from app.models.attachment import Attachment
from app.models.company import Company
from app.models.company_memory import CompanyMemory
from app.models.company_pulse import CompanyPulseSnapshot
from app.models.employee import Employee
from app.models.event import Event
from app.models.leave_request import LeaveRequest
from app.models.notification import Notification
from app.models.project import Project
from app.models.user import User
from app.models.work_object import WorkObject
from app.services.event_service import EventService
from app.services.notification_service import NotificationService

OPEN_WORK_STATUSES = {"assigned", "pending", "in_progress", "under_review", "blocked"}
RISKY_PROJECT_STATUSES = {"blocked", "delayed", "at_risk", "on_hold"}
RISKY_PROJECT_LEVELS = {"high", "critical", "blocked", "at_risk"}
STALE_AI_LOCK_MINUTES = 10

SECTION_WEIGHTS = {
    "work_health": 0.25,
    "project_health": 0.18,
    "people_health": 0.18,
    "leave_health": 0.10,
    "communication_health": 0.10,
    "ai_system_health": 0.09,
    "memory_health": 0.10,
}


def clamp_score(value: float | int) -> int:
    return max(0, min(100, int(round(float(value)))))


def count_rows(db: Session, model: type, *criteria: Any) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(*criteria)) or 0)


def linked_employee_id(db: Session, current_user: User | None) -> UUID | None:
    if current_user is None:
        return None
    employee = db.scalar(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.user_id == current_user.id,
            Employee.is_active.is_(True),
        )
    )
    return employee.id if employee is not None else None


class CompanyPulseService:
    @staticmethod
    def ensure_owner_admin_company_access(current_user: User | None, company_id: UUID) -> None:
        ensure_company_access(current_user, company_id)
        ensure_role(current_user, OWNER_ADMIN_ROLES)

    @staticmethod
    def latest_snapshot(db: Session, *, company_id: UUID, current_user: User | None) -> CompanyPulseSnapshot | None:
        CompanyPulseService.ensure_owner_admin_company_access(current_user, company_id)
        return db.scalar(
            select(CompanyPulseSnapshot)
            .where(CompanyPulseSnapshot.company_id == company_id)
            .order_by(CompanyPulseSnapshot.created_at.desc())
            .limit(1)
        )

    @staticmethod
    def history(
        db: Session,
        *,
        company_id: UUID,
        current_user: User | None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[CompanyPulseSnapshot]:
        CompanyPulseService.ensure_owner_admin_company_access(current_user, company_id)
        return list(
            db.scalars(
                select(CompanyPulseSnapshot)
                .where(CompanyPulseSnapshot.company_id == company_id)
                .order_by(CompanyPulseSnapshot.created_at.desc())
                .offset(max(offset, 0))
                .limit(min(max(limit, 1), 100))
            ).all()
        )

    @staticmethod
    def calculate_signals(db: Session, *, company_id: UUID, current_user: User | None) -> dict[str, Any]:
        CompanyPulseService.ensure_owner_admin_company_access(current_user, company_id)
        company = db.get(Company, company_id)
        if company is None or not company.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        latest = CompanyPulseService.latest_snapshot(db, company_id=company_id, current_user=current_user)
        return CompanyPulseService.build_snapshot_payload(db, company=company, previous_snapshot=latest)

    @staticmethod
    def generate_snapshot(db: Session, *, company_id: UUID, current_user: User | None) -> CompanyPulseSnapshot:
        CompanyPulseService.ensure_owner_admin_company_access(current_user, company_id)
        company = db.get(Company, company_id)
        if company is None or not company.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        previous_snapshot = db.scalar(
            select(CompanyPulseSnapshot)
            .where(CompanyPulseSnapshot.company_id == company_id)
            .order_by(CompanyPulseSnapshot.created_at.desc())
            .limit(1)
        )
        payload = CompanyPulseService.build_snapshot_payload(db, company=company, previous_snapshot=previous_snapshot)
        snapshot = CompanyPulseSnapshot(
            company_id=company_id,
            overall_score=payload["overall_score"],
            pulse_status=payload["pulse_status"],
            trend=payload["trend"],
            summary=payload["summary"],
            section_scores=payload["section_scores"],
            key_signals=payload["key_signals"],
            risks=payload["risks"],
            recommended_actions=payload["recommended_actions"],
            source_counts=payload["source_counts"],
            generated_by_user_id=current_user.id if current_user is not None else None,
            is_rule_based=True,
            metadata_json=payload["metadata"],
        )
        db.add(snapshot)
        db.flush()
        CompanyPulseService.record_generated_event(db, snapshot=snapshot, current_user=current_user)
        CompanyPulseService.notify_requester(db, snapshot=snapshot, current_user=current_user)
        return snapshot

    @staticmethod
    def build_snapshot_payload(
        db: Session,
        *,
        company: Company,
        previous_snapshot: CompanyPulseSnapshot | None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        today = date.today()
        today_start = datetime.combine(today, time.min, tzinfo=timezone.utc)
        tomorrow_start = today_start + timedelta(days=1)
        seven_days_ago = now - timedelta(days=7)
        stale_cutoff = now - timedelta(minutes=STALE_AI_LOCK_MINUTES)
        company_id = company.id

        employee_counts = CompanyPulseService.employee_counts(db, company_id=company_id)
        work_counts = CompanyPulseService.work_counts(db, company_id=company_id, today_start=today_start, tomorrow_start=tomorrow_start)
        project_counts = CompanyPulseService.project_counts(db, company_id=company_id)
        leave_counts = CompanyPulseService.leave_counts(db, company_id=company_id, today=today)
        notification_counts = CompanyPulseService.notification_counts(db, company_id=company_id)
        event_counts = CompanyPulseService.event_counts(db, company_id=company_id, since=seven_days_ago)
        ai_counts = CompanyPulseService.ai_counts(db, company_id=company_id, stale_cutoff=stale_cutoff)
        memory_counts = CompanyPulseService.memory_counts(db, company_id=company_id)
        file_counts = CompanyPulseService.file_counts(db, company_id=company_id)

        section_scores = {
            "work_health": CompanyPulseService.score_work(work_counts),
            "project_health": CompanyPulseService.score_projects(project_counts),
            "people_health": CompanyPulseService.score_people(employee_counts),
            "leave_health": CompanyPulseService.score_leave(leave_counts),
            "communication_health": CompanyPulseService.score_communication(notification_counts, event_counts),
            "ai_system_health": CompanyPulseService.score_ai_system(ai_counts),
            "memory_health": CompanyPulseService.score_memory(memory_counts),
        }
        overall_score = clamp_score(
            sum(section_scores[key] * weight for key, weight in SECTION_WEIGHTS.items())
        )
        pulse_status = CompanyPulseService.status_for_score(overall_score)
        trend = CompanyPulseService.trend_for_score(overall_score, previous_snapshot)
        source_counts = {
            "employees": employee_counts,
            "work": work_counts,
            "projects": project_counts,
            "leaves": leave_counts,
            "notifications": notification_counts,
            "events": event_counts,
            "ai_jobs": ai_counts,
            "company_memory": memory_counts,
            "files": file_counts,
        }
        key_signals = CompanyPulseService.key_signals(section_scores, source_counts)
        risks = CompanyPulseService.risks(source_counts)
        recommended_actions = CompanyPulseService.recommended_actions(source_counts, section_scores)
        summary = CompanyPulseService.summary_text(
            company_name=company.name,
            score=overall_score,
            pulse_status=pulse_status,
            trend=trend,
            section_scores=section_scores,
            risks=risks,
        )
        return {
            "company_id": company_id,
            "overall_score": overall_score,
            "pulse_status": pulse_status,
            "trend": trend,
            "summary": summary,
            "section_scores": section_scores,
            "key_signals": key_signals,
            "risks": risks,
            "recommended_actions": recommended_actions,
            "source_counts": source_counts,
            "generated_at": now,
            "is_rule_based": True,
            "metadata": {
                "scoring_version": "company_pulse_rule_v1",
                "scoring_method": "deterministic_weighted_sections",
                "section_weights": SECTION_WEIGHTS,
                "ai_required": False,
                "external_ai_used": False,
                "stale_ai_lock_minutes": STALE_AI_LOCK_MINUTES,
            },
        }

    @staticmethod
    def employee_counts(db: Session, *, company_id: UUID) -> dict[str, int]:
        total = count_rows(db, Employee, Employee.company_id == company_id)
        active = count_rows(db, Employee, Employee.company_id == company_id, Employee.is_active.is_(True))
        available = count_rows(db, Employee, Employee.company_id == company_id, Employee.is_active.is_(True), Employee.status == "available")
        busy = count_rows(db, Employee, Employee.company_id == company_id, Employee.is_active.is_(True), Employee.status == "busy")
        on_leave = count_rows(db, Employee, Employee.company_id == company_id, Employee.is_active.is_(True), Employee.status == "on_leave")
        inactive = count_rows(db, Employee, Employee.company_id == company_id, Employee.is_active.is_(False))
        return {
            "total": total,
            "active": active,
            "available": available,
            "busy": busy,
            "on_leave": on_leave,
            "inactive": inactive,
        }

    @staticmethod
    def work_counts(db: Session, *, company_id: UUID, today_start: datetime, tomorrow_start: datetime) -> dict[str, int]:
        active_work = WorkObject.is_active.is_(True)
        open_work = WorkObject.status.in_(OPEN_WORK_STATUSES)
        completed = count_rows(db, WorkObject, WorkObject.company_id == company_id, active_work, WorkObject.status == "completed")
        total = count_rows(db, WorkObject, WorkObject.company_id == company_id, active_work)
        blocked = count_rows(db, WorkObject, WorkObject.company_id == company_id, active_work, WorkObject.status == "blocked")
        overdue = count_rows(
            db,
            WorkObject,
            WorkObject.company_id == company_id,
            active_work,
            open_work,
            WorkObject.due_date.is_not(None),
            WorkObject.due_date < today_start,
        )
        due_today = count_rows(
            db,
            WorkObject,
            WorkObject.company_id == company_id,
            active_work,
            open_work,
            WorkObject.due_date >= today_start,
            WorkObject.due_date < tomorrow_start,
        )
        high_critical_open = count_rows(
            db,
            WorkObject,
            WorkObject.company_id == company_id,
            active_work,
            open_work,
            WorkObject.priority.in_(["high", "critical"]),
        )
        open_count = count_rows(db, WorkObject, WorkObject.company_id == company_id, active_work, open_work)
        return {
            "total": total,
            "open": open_count,
            "completed": completed,
            "blocked": blocked,
            "overdue": overdue,
            "due_today": due_today,
            "high_critical_open": high_critical_open,
        }

    @staticmethod
    def project_counts(db: Session, *, company_id: UUID) -> dict[str, int | float]:
        active_project = Project.is_active.is_(True)
        total_active = count_rows(db, Project, Project.company_id == company_id, active_project)
        active = count_rows(db, Project, Project.company_id == company_id, active_project, Project.status == "active")
        on_hold = count_rows(db, Project, Project.company_id == company_id, active_project, Project.status == "on_hold")
        delayed = count_rows(db, Project, Project.company_id == company_id, active_project, Project.status == "delayed")
        completed = count_rows(db, Project, Project.company_id == company_id, active_project, Project.status == "completed")
        high_priority = count_rows(db, Project, Project.company_id == company_id, active_project, Project.priority.in_(["high", "critical"]))
        high_risk = count_rows(
            db,
            Project,
            Project.company_id == company_id,
            active_project,
            or_(
                Project.status.in_(list(RISKY_PROJECT_STATUSES)),
                Project.risk_level.in_(list(RISKY_PROJECT_LEVELS)),
            ),
        )
        low_progress_active = count_rows(
            db,
            Project,
            Project.company_id == company_id,
            active_project,
            Project.status == "active",
            Project.progress_percent < 25,
        )
        average_progress = float(
            db.scalar(
                select(func.coalesce(func.avg(Project.progress_percent), 0)).where(
                    Project.company_id == company_id,
                    active_project,
                )
            )
            or 0
        )
        return {
            "total_active": total_active,
            "active": active,
            "on_hold": on_hold,
            "delayed": delayed,
            "completed": completed,
            "high_priority": high_priority,
            "high_risk": high_risk,
            "low_progress_active": low_progress_active,
            "average_progress": round(average_progress, 1),
        }

    @staticmethod
    def leave_counts(db: Session, *, company_id: UUID, today: date) -> dict[str, int]:
        active_leave = LeaveRequest.is_active.is_(True)
        pending = count_rows(db, LeaveRequest, LeaveRequest.company_id == company_id, active_leave, LeaveRequest.status == "pending")
        approved = count_rows(db, LeaveRequest, LeaveRequest.company_id == company_id, active_leave, LeaveRequest.status == "approved")
        rejected = count_rows(db, LeaveRequest, LeaveRequest.company_id == company_id, active_leave, LeaveRequest.status == "rejected")
        cancelled = count_rows(db, LeaveRequest, LeaveRequest.company_id == company_id, active_leave, LeaveRequest.status == "cancelled")
        upcoming = count_rows(
            db,
            LeaveRequest,
            LeaveRequest.company_id == company_id,
            active_leave,
            LeaveRequest.status == "approved",
            LeaveRequest.start_date >= today,
        )
        return {
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "cancelled": cancelled,
            "upcoming_approved": upcoming,
        }

    @staticmethod
    def notification_counts(db: Session, *, company_id: UUID) -> dict[str, int]:
        unread = count_rows(
            db,
            Notification,
            Notification.company_id == company_id,
            Notification.is_read.is_(False),
            Notification.is_dismissed.is_(False),
        )
        important_unread = count_rows(
            db,
            Notification,
            Notification.company_id == company_id,
            Notification.is_read.is_(False),
            Notification.is_dismissed.is_(False),
            Notification.priority.in_(["high", "urgent"]),
        )
        dismissed = count_rows(db, Notification, Notification.company_id == company_id, Notification.is_dismissed.is_(True))
        return {
            "unread": unread,
            "important_unread": important_unread,
            "dismissed": dismissed,
        }

    @staticmethod
    def event_counts(db: Session, *, company_id: UUID, since: datetime) -> dict[str, int]:
        recent = count_rows(db, Event, Event.company_id == company_id, Event.created_at >= since)
        failure_like = count_rows(
            db,
            Event,
            Event.company_id == company_id,
            Event.created_at >= since,
            or_(
                Event.event_type.ilike("%failed%"),
                Event.event_type.ilike("%rejected%"),
                Event.event_type.ilike("%critical%"),
                Event.event_type.ilike("%blocked%"),
            ),
        )
        return {
            "recent_7d": recent,
            "failure_like_7d": failure_like,
        }

    @staticmethod
    def ai_counts(db: Session, *, company_id: UUID, stale_cutoff: datetime) -> dict[str, int]:
        statuses = {
            status_name: count_rows(db, AIJob, AIJob.company_id == company_id, AIJob.status == status_name)
            for status_name in ("queued", "running", "succeeded", "failed", "cancelled", "skipped")
        }
        retryable_failed = count_rows(
            db,
            AIJob,
            AIJob.company_id == company_id,
            AIJob.status == "failed",
            AIJob.retryable.is_(True),
        )
        stale_running = count_rows(
            db,
            AIJob,
            AIJob.company_id == company_id,
            AIJob.status == "running",
            AIJob.locked_at.is_not(None),
            AIJob.locked_at < stale_cutoff,
        )
        statuses["retryable_failed"] = retryable_failed
        statuses["stale_running"] = stale_running
        return statuses

    @staticmethod
    def memory_counts(db: Session, *, company_id: UUID) -> dict[str, int]:
        approved = count_rows(db, CompanyMemory, CompanyMemory.company_id == company_id, CompanyMemory.status == "approved")
        suggested = count_rows(db, CompanyMemory, CompanyMemory.company_id == company_id, CompanyMemory.status == "suggested")
        archived = count_rows(db, CompanyMemory, CompanyMemory.company_id == company_id, CompanyMemory.status == "archived")
        important = count_rows(
            db,
            CompanyMemory,
            CompanyMemory.company_id == company_id,
            CompanyMemory.status == "approved",
            CompanyMemory.importance.in_(["high", "critical"]),
        )
        return {
            "approved": approved,
            "suggested": suggested,
            "archived": archived,
            "important_approved": important,
        }

    @staticmethod
    def file_counts(db: Session, *, company_id: UUID) -> dict[str, int | float]:
        active_files = Attachment.is_active.is_(True)
        total = count_rows(db, Attachment, Attachment.company_id == company_id, active_files, Attachment.is_deleted.is_(False))
        archived = count_rows(db, Attachment, Attachment.company_id == company_id, Attachment.is_deleted.is_(False), Attachment.archived_at.is_not(None))
        deleted = count_rows(db, Attachment, Attachment.company_id == company_id, Attachment.is_deleted.is_(True))
        total_bytes = int(
            db.scalar(
                select(func.coalesce(func.sum(Attachment.file_size), 0)).where(
                    Attachment.company_id == company_id,
                    active_files,
                    Attachment.is_deleted.is_(False),
                )
            )
            or 0
        )
        return {
            "active": total,
            "archived": archived,
            "deleted": deleted,
            "storage_mb": round(total_bytes / (1024 * 1024), 2),
        }

    @staticmethod
    def score_work(counts: dict[str, int]) -> int:
        score = 100
        score -= min(counts["overdue"] * 6, 30)
        score -= min(counts["blocked"] * 8, 32)
        score -= min(counts["high_critical_open"] * 4, 20)
        score -= min(counts["due_today"] * 1, 8)
        total = counts["total"]
        if total >= 5 and counts["completed"] / max(total, 1) < 0.2:
            score -= 8
        return clamp_score(score)

    @staticmethod
    def score_projects(counts: dict[str, int | float]) -> int:
        score = 100
        score -= min(int(counts["delayed"]) * 10, 30)
        score -= min(int(counts["on_hold"]) * 6, 18)
        score -= min(int(counts["high_risk"]) * 12, 36)
        score -= min(int(counts["high_priority"]) * 3, 12)
        score -= min(int(counts["low_progress_active"]) * 5, 20)
        if int(counts["active"]) > 0 and float(counts["average_progress"]) < 25:
            score -= 10
        return clamp_score(score)

    @staticmethod
    def score_people(counts: dict[str, int]) -> int:
        total = counts["total"]
        if total == 0:
            return 60
        score = 100
        score -= min((counts["inactive"] / total) * 35, 35)
        score -= min((counts["on_leave"] / total) * 12, 12)
        score -= min((counts["busy"] / total) * 10, 10)
        if counts["active"] == 0:
            score -= 30
        return clamp_score(score)

    @staticmethod
    def score_leave(counts: dict[str, int]) -> int:
        score = 100
        score -= min(counts["pending"] * 8, 40)
        score -= min(counts["upcoming_approved"] * 2, 10)
        return clamp_score(score)

    @staticmethod
    def score_communication(notification_counts: dict[str, int], event_counts: dict[str, int]) -> int:
        score = 100
        score -= min(notification_counts["important_unread"] * 8, 40)
        score -= min(notification_counts["unread"] * 2, 25)
        score -= min(event_counts["failure_like_7d"] * 4, 20)
        return clamp_score(score)

    @staticmethod
    def score_ai_system(counts: dict[str, int]) -> int:
        score = 100
        score -= min(counts["failed"] * 8, 40)
        score -= min(counts["stale_running"] * 15, 30)
        score -= min(counts["retryable_failed"] * 4, 12)
        score -= min(counts["queued"] * 1, 10)
        return clamp_score(score)

    @staticmethod
    def score_memory(counts: dict[str, int]) -> int:
        score = 95 if counts["approved"] > 0 else 75
        score -= min(counts["suggested"] * 5, 25)
        if counts["important_approved"] > 0:
            score += 5
        return clamp_score(score)

    @staticmethod
    def status_for_score(score: int) -> str:
        if score >= 85:
            return "excellent"
        if score >= 70:
            return "healthy"
        if score >= 50:
            return "watch"
        if score >= 30:
            return "at_risk"
        return "critical"

    @staticmethod
    def trend_for_score(score: int, previous_snapshot: CompanyPulseSnapshot | None) -> str:
        if previous_snapshot is None:
            return "unknown"
        delta = score - previous_snapshot.overall_score
        if delta >= 4:
            return "improving"
        if delta <= -4:
            return "declining"
        return "stable"

    @staticmethod
    def key_signals(section_scores: dict[str, int], source_counts: dict[str, Any]) -> list[str]:
        signals: list[str] = []
        work = source_counts["work"]
        projects = source_counts["projects"]
        people = source_counts["employees"]
        ai_jobs = source_counts["ai_jobs"]
        memory = source_counts["company_memory"]
        if work["completed"] > 0:
            signals.append(f"{work['completed']} completed work object(s) are contributing positively.")
        if work["blocked"] == 0 and work["overdue"] == 0:
            signals.append("No blocked or overdue open work is currently visible.")
        if projects["active"] > 0:
            signals.append(f"{projects['active']} active project(s) with {projects['average_progress']}% average progress.")
        if people["active"] > 0:
            signals.append(f"{people['active']} active employee(s); {people['available']} currently available.")
        if ai_jobs["succeeded"] > 0:
            signals.append(f"{ai_jobs['succeeded']} AI job(s) have completed successfully.")
        if memory["approved"] > 0:
            signals.append(f"{memory['approved']} approved Company Memory item(s) are available.")
        strongest_section = max(section_scores.items(), key=lambda item: item[1])
        signals.append(f"Strongest section: {strongest_section[0].replace('_', ' ')} at {strongest_section[1]}/100.")
        return signals[:8]

    @staticmethod
    def risks(source_counts: dict[str, Any]) -> list[str]:
        risks: list[str] = []
        work = source_counts["work"]
        projects = source_counts["projects"]
        leaves = source_counts["leaves"]
        notifications = source_counts["notifications"]
        events = source_counts["events"]
        ai_jobs = source_counts["ai_jobs"]
        memory = source_counts["company_memory"]
        people = source_counts["employees"]
        if work["overdue"] > 0:
            risks.append(f"{work['overdue']} open work object(s) are overdue.")
        if work["blocked"] > 0:
            risks.append(f"{work['blocked']} work object(s) are blocked.")
        if work["high_critical_open"] > 0:
            risks.append(f"{work['high_critical_open']} high or critical open work item(s) need attention.")
        if projects["high_risk"] > 0:
            risks.append(f"{projects['high_risk']} active project(s) are risky, blocked, delayed, or on hold.")
        if projects["low_progress_active"] > 0:
            risks.append(f"{projects['low_progress_active']} active project(s) have progress below 25%.")
        if leaves["pending"] > 0:
            risks.append(f"{leaves['pending']} leave request(s) are waiting for action.")
        if notifications["important_unread"] > 0:
            risks.append(f"{notifications['important_unread']} important unread notification(s) are open.")
        if events["failure_like_7d"] > 0:
            risks.append(f"{events['failure_like_7d']} failure/rejection/critical event(s) happened in the last 7 days.")
        if ai_jobs["failed"] > 0 or ai_jobs["stale_running"] > 0:
            risks.append(f"{ai_jobs['failed']} failed AI job(s) and {ai_jobs['stale_running']} stale running job(s) need cleanup.")
        if memory["suggested"] > 0:
            risks.append(f"{memory['suggested']} Company Memory suggestion(s) are pending review.")
        if people["total"] > 0 and people["active"] == 0:
            risks.append("No active employees are currently available in the company profile.")
        return risks[:10]

    @staticmethod
    def recommended_actions(source_counts: dict[str, Any], section_scores: dict[str, int]) -> list[str]:
        actions: list[str] = []
        work = source_counts["work"]
        projects = source_counts["projects"]
        leaves = source_counts["leaves"]
        notifications = source_counts["notifications"]
        ai_jobs = source_counts["ai_jobs"]
        memory = source_counts["company_memory"]
        people = source_counts["employees"]
        if work["overdue"] or work["blocked"]:
            actions.append("Review overdue and blocked work first, then update owners or due dates.")
        if work["high_critical_open"]:
            actions.append("Triage high and critical work objects before creating new operational load.")
        if projects["high_risk"] or projects["low_progress_active"]:
            actions.append("Open risky projects and confirm progress, blockers, and next accountable action.")
        if leaves["pending"]:
            actions.append("Clear pending leave decisions so availability stays reliable.")
        if notifications["important_unread"]:
            actions.append("Resolve important unread notifications from the action stream.")
        if ai_jobs["failed"] or ai_jobs["stale_running"]:
            actions.append("Use AI Foundation queue controls to retry or recover failed/stale AI jobs.")
        if memory["suggested"]:
            actions.append("Review Company Memory suggestions and approve only durable company knowledge.")
        if people["total"] == 0:
            actions.append("Add employees to make people health and assignment signals meaningful.")
        weakest_section = min(section_scores.items(), key=lambda item: item[1])
        actions.append(f"Focus next on {weakest_section[0].replace('_', ' ')}; it is the weakest section at {weakest_section[1]}/100.")
        return actions[:8]

    @staticmethod
    def summary_text(
        *,
        company_name: str,
        score: int,
        pulse_status: str,
        trend: str,
        section_scores: dict[str, int],
        risks: list[str],
    ) -> str:
        weakest = min(section_scores.items(), key=lambda item: item[1])
        strongest = max(section_scores.items(), key=lambda item: item[1])
        risk_sentence = risks[0] if risks else "No major operational risk is visible from the current rule-based signals."
        return (
            f"{company_name} is {pulse_status.replace('_', ' ')} at {score}/100 with a {trend} trend. "
            f"Strongest signal: {strongest[0].replace('_', ' ')} ({strongest[1]}/100). "
            f"Main attention area: {weakest[0].replace('_', ' ')} ({weakest[1]}/100). {risk_sentence}"
        )

    @staticmethod
    def record_generated_event(db: Session, *, snapshot: CompanyPulseSnapshot, current_user: User | None) -> None:
        EventService.record_event(
            db,
            company_id=snapshot.company_id,
            actor_user_id=current_user.id if current_user is not None else None,
            actor_employee_id=linked_employee_id(db, current_user),
            event_type="company_pulse.generated",
            title="Company Pulse generated",
            description=f"Company Pulse is {snapshot.overall_score}/100 ({snapshot.pulse_status}).",
            target_entity_type="company_pulse_snapshot",
            target_entity_id=snapshot.id,
            metadata={
                "pulse_snapshot_id": str(snapshot.id),
                "overall_score": snapshot.overall_score,
                "pulse_status": snapshot.pulse_status,
                "trend": snapshot.trend,
                "section_scores": snapshot.section_scores,
                "is_rule_based": snapshot.is_rule_based,
            },
        )

    @staticmethod
    def notify_requester(db: Session, *, snapshot: CompanyPulseSnapshot, current_user: User | None) -> None:
        if current_user is None:
            return
        NotificationService.create_notification(
            db,
            company_id=snapshot.company_id,
            recipient_user_id=current_user.id,
            actor_user_id=current_user.id,
            actor_employee_id=linked_employee_id(db, current_user),
            title="Company Pulse generated",
            message=f"Company Pulse is {snapshot.overall_score}/100 ({snapshot.pulse_status.replace('_', ' ')}).",
            notification_type="company_pulse.generated",
            target_entity_type="company_pulse_snapshot",
            target_entity_id=snapshot.id,
            priority="normal",
            action_url="#/dashboard",
            metadata={
                "pulse_snapshot_id": str(snapshot.id),
                "overall_score": snapshot.overall_score,
                "pulse_status": snapshot.pulse_status,
                "trend": snapshot.trend,
            },
        )
