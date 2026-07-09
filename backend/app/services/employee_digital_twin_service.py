from collections import Counter
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.permissions import OWNER_ADMIN_ROLES, ROLE_EMPLOYEE, ROLE_MANAGER, ensure_company_access
from app.models.common import utc_now
from app.models.employee import Employee
from app.models.employee_digital_twin import EmployeeDigitalTwinSnapshot
from app.models.event import Event
from app.models.leave_request import LeaveRequest
from app.models.project import Project, ProjectMember
from app.models.user import User
from app.models.work_object import WorkObject
from app.schemas.employee_digital_twin import EMPLOYEE_TWIN_PERIODS
from app.services.event_service import EventService
from app.services.notification_service import NotificationService

OPEN_WORK_STATUSES = {"assigned", "pending", "in_progress", "under_review", "blocked"}
COMPLETED_WORK_STATUSES = {"completed", "done", "closed"}
HIGH_PRIORITIES = {"high", "critical", "urgent"}


def safe_text(value: Any, max_chars: int = 220) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text[:max_chars]


def linked_employee(db: Session, current_user: User | None) -> Employee | None:
    if current_user is None:
        return None
    return db.scalar(
        select(Employee).where(
            Employee.company_id == current_user.company_id,
            Employee.user_id == current_user.id,
            Employee.is_active.is_(True),
        )
    )


def normalized(value: str | None) -> str:
    return (value or "unknown").strip().lower().replace(" ", "_")


class EmployeeDigitalTwinService:
    @staticmethod
    def validate_period(period_days: int) -> int:
        if period_days not in EMPLOYEE_TWIN_PERIODS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="period_days must be one of 7, 30, or 90")
        return period_days

    @staticmethod
    def get_employee_or_404(db: Session, *, company_id: UUID, employee_id: UUID) -> Employee:
        employee = db.get(Employee, employee_id)
        if employee is None or employee.company_id != company_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        return employee

    @staticmethod
    def ensure_visible(db: Session, *, current_user: User, employee: Employee) -> None:
        ensure_company_access(current_user, employee.company_id)
        if current_user.role in OWNER_ADMIN_ROLES:
            return
        current_employee = linked_employee(db, current_user)
        if current_user.role == ROLE_EMPLOYEE:
            if employee.user_id == current_user.id or (current_employee is not None and employee.id == current_employee.id):
                return
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")
        if current_user.role == ROLE_MANAGER and current_employee is not None:
            if employee.manager_id == current_employee.id:
                return
            if EmployeeDigitalTwinService.has_shared_project_visibility(db, viewer=current_employee, target=employee):
                return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission for this employee Digital Twin")

    @staticmethod
    def has_shared_project_visibility(db: Session, *, viewer: Employee, target: Employee) -> bool:
        if viewer.company_id != target.company_id:
            return False
        viewer_project_ids = {
            project_id
            for (project_id,) in db.execute(
                select(ProjectMember.project_id).where(
                    ProjectMember.company_id == viewer.company_id,
                    ProjectMember.employee_id == viewer.id,
                    ProjectMember.is_active.is_(True),
                )
            ).all()
        }
        owned_project_ids = {
            project_id
            for (project_id,) in db.execute(
                select(Project.id).where(Project.company_id == viewer.company_id, Project.owner_employee_id == viewer.id, Project.is_active.is_(True))
            ).all()
        }
        viewer_project_ids.update(owned_project_ids)
        if not viewer_project_ids:
            return False
        target_membership = db.scalar(
            select(ProjectMember.id).where(
                ProjectMember.company_id == target.company_id,
                ProjectMember.employee_id == target.id,
                ProjectMember.project_id.in_(viewer_project_ids),
                ProjectMember.is_active.is_(True),
            )
        )
        return target_membership is not None

    @classmethod
    def latest_snapshot(
        cls,
        db: Session,
        *,
        company_id: UUID,
        employee_id: UUID,
        current_user: User,
    ) -> EmployeeDigitalTwinSnapshot | None:
        employee = cls.get_employee_or_404(db, company_id=company_id, employee_id=employee_id)
        cls.ensure_visible(db, current_user=current_user, employee=employee)
        return db.scalar(
            select(EmployeeDigitalTwinSnapshot)
            .where(EmployeeDigitalTwinSnapshot.company_id == company_id, EmployeeDigitalTwinSnapshot.employee_id == employee_id)
            .order_by(EmployeeDigitalTwinSnapshot.created_at.desc())
            .limit(1)
        )

    @classmethod
    def history(
        cls,
        db: Session,
        *,
        company_id: UUID,
        employee_id: UUID,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> list[EmployeeDigitalTwinSnapshot]:
        employee = cls.get_employee_or_404(db, company_id=company_id, employee_id=employee_id)
        cls.ensure_visible(db, current_user=current_user, employee=employee)
        return list(
            db.scalars(
                select(EmployeeDigitalTwinSnapshot)
                .where(EmployeeDigitalTwinSnapshot.company_id == company_id, EmployeeDigitalTwinSnapshot.employee_id == employee_id)
                .order_by(EmployeeDigitalTwinSnapshot.created_at.desc())
                .offset(max(offset, 0))
                .limit(min(max(limit, 1), 100))
            ).all()
        )

    @classmethod
    def signals(
        cls,
        db: Session,
        *,
        company_id: UUID,
        employee_id: UUID,
        current_user: User,
        period_days: int,
    ) -> dict[str, Any]:
        period_days = cls.validate_period(period_days)
        employee = cls.get_employee_or_404(db, company_id=company_id, employee_id=employee_id)
        cls.ensure_visible(db, current_user=current_user, employee=employee)
        return cls.build_snapshot_payload(db, employee=employee, current_user=current_user, period_days=period_days)

    @classmethod
    def generate_snapshot(
        cls,
        db: Session,
        *,
        company_id: UUID,
        employee_id: UUID,
        current_user: User,
        period_days: int,
    ) -> EmployeeDigitalTwinSnapshot:
        payload = cls.signals(db, company_id=company_id, employee_id=employee_id, current_user=current_user, period_days=period_days)
        snapshot = EmployeeDigitalTwinSnapshot(
            company_id=company_id,
            employee_id=employee_id,
            generated_by_user_id=current_user.id,
            period_days=payload["period_days"],
            period_start=payload["period_start"],
            period_end=payload["period_end"],
            workload_level=payload["workload_level"],
            summary=payload["summary"],
            profile_json=payload["profile"],
            work_metrics_json=payload["work_metrics"],
            project_metrics_json=payload["project_metrics"],
            availability_json=payload["availability"],
            skills_json=payload["skills"],
            strengths_json=payload["strengths"],
            attention_areas_json=payload["attention_areas"],
            risks_json=payload["risks"],
            recommended_actions_json=payload["recommended_actions"],
            source_counts_json=payload["source_counts"],
            data_coverage_json=payload["data_coverage"],
            limitations_json=payload["limitations"],
            is_rule_based=True,
            ai_narrative_used=False,
            metadata_json=payload["metadata"],
        )
        db.add(snapshot)
        db.flush()
        cls.record_generated_event(db, snapshot=snapshot, current_user=current_user)
        cls.notify_requester(db, snapshot=snapshot, current_user=current_user)
        return snapshot

    @classmethod
    def build_snapshot_payload(
        cls,
        db: Session,
        *,
        employee: Employee,
        current_user: User,
        period_days: int,
    ) -> dict[str, Any]:
        now = utc_now()
        period_start = now - timedelta(days=period_days)
        work_items = list(
            db.scalars(
                select(WorkObject)
                .where(
                    WorkObject.company_id == employee.company_id,
                    WorkObject.assignee_employee_id == employee.id,
                    WorkObject.is_active.is_(True),
                )
                .order_by(WorkObject.updated_at.desc())
            ).all()
        )
        recent_work = [item for item in work_items if item.updated_at >= period_start or (item.completed_at is not None and item.completed_at >= period_start)]
        open_work = [item for item in work_items if normalized(item.status) in OPEN_WORK_STATUSES]
        completed_recent = [
            item
            for item in work_items
            if (item.completed_at is not None and item.completed_at >= period_start)
            or (normalized(item.status) in COMPLETED_WORK_STATUSES and item.updated_at >= period_start)
        ]
        overdue = [item for item in open_work if item.due_date is not None and item.due_date < now]
        blocked = [item for item in open_work if normalized(item.status) == "blocked"]
        high_priority_open = [item for item in open_work if normalized(item.priority) in HIGH_PRIORITIES]
        upcoming_due = [item for item in open_work if item.due_date is not None and now <= item.due_date <= now + timedelta(days=7)]
        status_counts = Counter(normalized(item.status) for item in work_items)
        priority_counts = Counter(normalized(item.priority) for item in work_items)
        skills = cls.collect_skills(employee, work_items)
        project_metrics = cls.project_metrics(db, employee=employee, work_items=work_items)
        leave_metrics = cls.leave_metrics(db, employee=employee, now=now, period_start=period_start)
        activity_summary = cls.recent_activity_summary(db, employee=employee, since=period_start)
        workload_level, workload_explanation = cls.workload_level(
            open_count=len(open_work),
            overdue_count=len(overdue),
            blocked_count=len(blocked),
            high_priority_open_count=len(high_priority_open),
            upcoming_due_count=len(upcoming_due),
            active_project_count=project_metrics["active_project_count"],
            availability_status=employee.status,
            upcoming_leave_count=leave_metrics["upcoming_approved"],
        )
        strengths = cls.strengths(
            completed_count=len(completed_recent),
            active_project_count=project_metrics["active_project_count"],
            overdue_count=len(overdue),
            high_priority_completed=len([item for item in completed_recent if normalized(item.priority) in HIGH_PRIORITIES]),
            skills=skills,
        )
        attention_areas = cls.attention_areas(
            open_count=len(open_work),
            overdue_count=len(overdue),
            blocked_count=len(blocked),
            high_priority_open_count=len(high_priority_open),
            upcoming_due_count=len(upcoming_due),
            missing_due_dates=len([item for item in open_work if item.due_date is None]),
            upcoming_leave_count=leave_metrics["upcoming_approved"],
        )
        risks = cls.risks(attention_areas=attention_areas, workload_level=workload_level)
        recommendations = cls.recommended_actions(
            workload_level=workload_level,
            overdue_count=len(overdue),
            blocked_count=len(blocked),
            high_priority_open_count=len(high_priority_open),
            upcoming_due_count=len(upcoming_due),
            skills=skills,
        )
        profile = {
            "employee_id": str(employee.id),
            "employee_display_name": safe_text(employee.full_name),
            "role": safe_text(employee.role),
            "department": safe_text(employee.department_ref.name if employee.department_ref else employee.department),
            "team": safe_text(employee.team_ref.name if employee.team_ref else None),
            "manager": safe_text(employee.manager.full_name if employee.manager else None),
            "employment_type": safe_text(employee.employment_type),
            "work_status": safe_text(employee.status),
            "availability_status": safe_text(employee.status),
            "account_status": safe_text(employee.account_status),
            "profile_completion_status": safe_text(employee.profile_completion_status),
        }
        work_metrics = {
            "assigned_work_count": len(work_items),
            "current_open_work_count": len(open_work),
            "in_progress_work_count": status_counts.get("in_progress", 0),
            "completed_work_count": len(completed_recent),
            "overdue_work_count": len(overdue),
            "blocked_work_count": len(blocked),
            "high_priority_open_work_count": len(high_priority_open),
            "upcoming_due_work_count": len(upcoming_due),
            "work_status_breakdown": dict(status_counts),
            "work_priority_breakdown": dict(priority_counts),
            "recent_completion_pattern": f"{len(completed_recent)} assigned work item(s) completed or marked complete in the last {period_days} days.",
            "current_priorities": [
                {
                    "title": safe_text(item.title),
                    "status": safe_text(item.status),
                    "priority": safe_text(item.priority),
                    "due_date": item.due_date.isoformat() if item.due_date else None,
                }
                for item in sorted(open_work, key=lambda item: (item.due_date is None, item.due_date or now, item.priority), reverse=False)[:5]
            ],
        }
        availability = {
            "availability_signal": cls.availability_signal(employee.status, leave_metrics),
            "current_status": safe_text(employee.status),
            "leave_counts": leave_metrics,
            "note": "Leave is used only as safe availability context and is not treated as negative performance evidence.",
        }
        source_counts = {
            "assigned_work": len(work_items),
            "recent_work": len(recent_work),
            "projects": project_metrics["active_project_count"],
            "leave_requests": leave_metrics["total"],
            "recent_events": activity_summary["event_count"],
            "skills": len(skills),
        }
        coverage = {
            "period_days": period_days,
            "source_categories": ["employee_profile", "assigned_work", "projects", "leave_availability", "events", "skills_and_tags"],
            "has_work_data": bool(work_items),
            "has_project_data": bool(project_metrics["projects"]),
            "has_recent_activity": bool(activity_summary["event_count"]),
            "coverage_level": cls.coverage_level(source_counts),
        }
        limitations = cls.limitations(source_counts, employee)
        summary = cls.summary_text(employee.full_name, workload_level, work_metrics, project_metrics, len(attention_areas))
        return {
            "company_id": employee.company_id,
            "employee_id": employee.id,
            "period_days": period_days,
            "period_start": period_start,
            "period_end": now,
            "workload_level": workload_level,
            "summary": summary,
            "profile": profile,
            "work_metrics": work_metrics,
            "project_metrics": project_metrics,
            "availability": availability,
            "skills": skills,
            "strengths": strengths,
            "attention_areas": attention_areas,
            "risks": risks,
            "recommended_actions": recommendations,
            "source_counts": source_counts,
            "data_coverage": coverage,
            "limitations": limitations,
            "is_rule_based": True,
            "ai_narrative_used": False,
            "generated_at": now,
            "metadata": {
                "methodology": "Rule-based operational snapshot from assigned work, project involvement, due dates, priorities, availability, approved leave state, safe event counts, and skill/tag metadata.",
                "privacy_notice": "This is not an employee score, ranking, performance rating, or automated employment decision.",
                "generated_by_user_id": str(current_user.id),
                "ai_required": False,
                "external_ai_used": False,
                "scoring_absent_by_design": True,
            },
        }

    @staticmethod
    def collect_skills(employee: Employee, work_items: list[WorkObject]) -> list[str]:
        skills = [safe_text(skill, 80) for skill in (employee.skills if isinstance(employee.skills, list) else [])]
        for item in work_items:
            for tag in item.tags if isinstance(item.tags, list) else []:
                skills.append(safe_text(tag, 80))
        return sorted({skill for skill in skills if skill})[:20]

    @staticmethod
    def project_metrics(db: Session, *, employee: Employee, work_items: list[WorkObject]) -> dict[str, Any]:
        member_projects = list(
            db.scalars(
                select(Project)
                .join(ProjectMember, ProjectMember.project_id == Project.id)
                .where(
                    Project.company_id == employee.company_id,
                    Project.is_active.is_(True),
                    ProjectMember.employee_id == employee.id,
                    ProjectMember.is_active.is_(True),
                )
            ).all()
        )
        owned_projects = list(
            db.scalars(
                select(Project).where(Project.company_id == employee.company_id, Project.owner_employee_id == employee.id, Project.is_active.is_(True))
            ).all()
        )
        work_project_ids = {item.project_id for item in work_items if item.project_id is not None}
        work_projects = list(
            db.scalars(select(Project).where(Project.company_id == employee.company_id, Project.id.in_(work_project_ids), Project.is_active.is_(True))).all()
        ) if work_project_ids else []
        projects_by_id = {project.id: project for project in [*member_projects, *owned_projects, *work_projects]}
        projects = list(projects_by_id.values())
        return {
            "active_project_count": len(projects),
            "owned_project_count": len([project for project in projects if project.owner_employee_id == employee.id]),
            "project_involvement": [
                {
                    "project_id": str(project.id),
                    "name": safe_text(project.name),
                    "status": safe_text(project.status),
                    "priority": safe_text(project.priority),
                    "risk_level": safe_text(project.risk_level),
                    "progress_percent": project.progress_percent,
                }
                for project in projects[:8]
            ],
            "projects": [safe_text(project.name) for project in projects[:8] if safe_text(project.name)],
        }

    @staticmethod
    def leave_metrics(db: Session, *, employee: Employee, now: datetime, period_start: datetime) -> dict[str, int]:
        today = now.date()
        leaves = list(
            db.scalars(
                select(LeaveRequest).where(
                    LeaveRequest.company_id == employee.company_id,
                    LeaveRequest.employee_id == employee.id,
                    LeaveRequest.is_active.is_(True),
                    LeaveRequest.submitted_at >= period_start,
                )
            ).all()
        )
        upcoming = list(
            db.scalars(
                select(LeaveRequest).where(
                    LeaveRequest.company_id == employee.company_id,
                    LeaveRequest.employee_id == employee.id,
                    LeaveRequest.is_active.is_(True),
                    LeaveRequest.status == "approved",
                    LeaveRequest.start_date >= today,
                )
            ).all()
        )
        by_status = Counter(normalized(item.status) for item in leaves)
        return {
            "total": len(leaves),
            "pending": by_status.get("pending", 0),
            "approved": by_status.get("approved", 0),
            "rejected": by_status.get("rejected", 0),
            "cancelled": by_status.get("cancelled", 0),
            "upcoming_approved": len(upcoming),
        }

    @staticmethod
    def recent_activity_summary(db: Session, *, employee: Employee, since: datetime) -> dict[str, Any]:
        events = list(
            db.scalars(
                select(Event)
                .where(
                    Event.company_id == employee.company_id,
                    Event.created_at >= since,
                    or_(
                        Event.actor_employee_id == employee.id,
                        (Event.target_entity_type == "employee") & (Event.target_entity_id == employee.id),
                        (Event.target_entity_type == "work_object")
                        & (
                            Event.target_entity_id.in_(
                                select(WorkObject.id).where(
                                    WorkObject.company_id == employee.company_id,
                                    WorkObject.assignee_employee_id == employee.id,
                                )
                            )
                        ),
                    ),
                )
                .order_by(Event.created_at.desc())
                .limit(20)
            ).all()
        )
        return {
            "event_count": len(events),
            "recent_activity_summary": [
                {
                    "event_type": safe_text(event.event_type, 120),
                    "title": safe_text(event.title, 220),
                    "created_at": event.created_at.isoformat() if event.created_at else None,
                }
                for event in events[:8]
            ],
        }

    @staticmethod
    def workload_level(
        *,
        open_count: int,
        overdue_count: int,
        blocked_count: int,
        high_priority_open_count: int,
        upcoming_due_count: int,
        active_project_count: int,
        availability_status: str,
        upcoming_leave_count: int,
    ) -> tuple[str, str]:
        if open_count == 0 and active_project_count == 0:
            return "unknown", "There is not enough assigned work or project involvement to determine workload."
        pressure = overdue_count * 3 + blocked_count * 3 + high_priority_open_count * 2 + upcoming_due_count + max(0, open_count - 5)
        if pressure >= 10 or overdue_count >= 4 or blocked_count >= 3:
            level = "overloaded"
        elif pressure >= 5 or open_count >= 6 or high_priority_open_count >= 3:
            level = "elevated"
        elif open_count <= 2 and overdue_count == 0 and blocked_count == 0:
            level = "light"
        else:
            level = "balanced"
        explanation = (
            f"Workload is {level} based on {open_count} open assignment(s), {overdue_count} overdue item(s), "
            f"{blocked_count} blocked item(s), {high_priority_open_count} high-priority open item(s), and {upcoming_due_count} due in the next 7 days."
        )
        if normalized(availability_status) in {"on_leave", "offline"} or upcoming_leave_count:
            explanation += " Availability is included only for planning context, not as negative performance evidence."
        return level, explanation

    @staticmethod
    def strengths(*, completed_count: int, active_project_count: int, overdue_count: int, high_priority_completed: int, skills: list[str]) -> list[str]:
        strengths: list[str] = []
        if completed_count:
            strengths.append(f"Completed {completed_count} assigned work item(s) during the selected period.")
        if active_project_count:
            strengths.append(f"Contributing to {active_project_count} active project(s).")
        if overdue_count == 0:
            strengths.append("No overdue assigned work is visible in the current snapshot.")
        if high_priority_completed:
            strengths.append(f"Recently completed {high_priority_completed} high-priority work item(s).")
        if skills:
            strengths.append(f"Current work/profile tags include {', '.join(skills[:5])}.")
        return strengths[:6] or ["Not enough operational data yet to identify evidence-based strengths."]

    @staticmethod
    def attention_areas(
        *,
        open_count: int,
        overdue_count: int,
        blocked_count: int,
        high_priority_open_count: int,
        upcoming_due_count: int,
        missing_due_dates: int,
        upcoming_leave_count: int,
    ) -> list[str]:
        areas: list[str] = []
        if overdue_count:
            areas.append(f"{overdue_count} assigned work item(s) are overdue; review priority and dependencies.")
        if blocked_count:
            areas.append(f"{blocked_count} assigned work item(s) are blocked; clarify the dependency or next accountable action.")
        if high_priority_open_count >= 2:
            areas.append(f"{high_priority_open_count} high-priority assigned item(s) are open at the same time.")
        if upcoming_due_count:
            areas.append(f"{upcoming_due_count} open item(s) are due in the next 7 days.")
        if open_count >= 6:
            areas.append("Several active assignments are open simultaneously; confirm the workload is still realistic.")
        if missing_due_dates:
            areas.append(f"{missing_due_dates} open item(s) do not have due dates; update planning metadata where useful.")
        if upcoming_leave_count:
            areas.append("Upcoming approved leave exists; make sure deadlines and handoffs are reflected in planning.")
        return areas[:7] or ["No major attention area is visible from current operational signals."]

    @staticmethod
    def risks(*, attention_areas: list[str], workload_level: str) -> list[str]:
        risks: list[str] = []
        if workload_level in {"elevated", "overloaded"}:
            risks.append(f"Workload is {workload_level}; review assignments before adding more high-priority work.")
        for area in attention_areas:
            if "overdue" in area.lower() or "blocked" in area.lower() or "due in the next 7 days" in area.lower():
                risks.append(area)
        return risks[:5] or ["No major operational risk is visible from current evidence."]

    @staticmethod
    def recommended_actions(
        *,
        workload_level: str,
        overdue_count: int,
        blocked_count: int,
        high_priority_open_count: int,
        upcoming_due_count: int,
        skills: list[str],
    ) -> list[str]:
        actions: list[str] = []
        if overdue_count:
            actions.append("Review overdue assigned work and agree on the next realistic due dates.")
        if blocked_count:
            actions.append("Clarify blocked dependencies with the project owner or manager.")
        if high_priority_open_count >= 2:
            actions.append("Reduce simultaneous high-priority assignments or clarify which item comes first.")
        if upcoming_due_count:
            actions.append("Review upcoming deadlines and confirm handoff or delivery expectations.")
        if workload_level == "overloaded":
            actions.append("Hold a workload review before assigning additional urgent work.")
        if not skills:
            actions.append("Add safe skill or work tags to improve future assignment context.")
        actions.append("Use this Digital Twin as operational planning assistance only, not as a performance rating.")
        return actions[:7]

    @staticmethod
    def availability_signal(status_value: str, leave_metrics: dict[str, int]) -> str:
        status_label = normalized(status_value).replace("_", " ")
        if leave_metrics.get("upcoming_approved", 0):
            return f"Currently marked {status_label}; upcoming approved leave should be considered for planning."
        return f"Currently marked {status_label}."

    @staticmethod
    def coverage_level(source_counts: dict[str, int]) -> str:
        signals = int(bool(source_counts["assigned_work"])) + int(bool(source_counts["projects"])) + int(bool(source_counts["recent_events"])) + int(bool(source_counts["skills"]))
        if signals >= 3:
            return "good"
        if signals >= 1:
            return "limited"
        return "minimal"

    @staticmethod
    def limitations(source_counts: dict[str, int], employee: Employee) -> list[str]:
        limitations = [
            "This is an operational assistance profile, not an employee performance score or employment decision tool.",
            "FebGrid does not compare this employee against peers or create rankings in v1.",
        ]
        if source_counts["assigned_work"] == 0:
            limitations.append("No assigned work is visible, so workload and strengths are limited.")
        if source_counts["recent_events"] == 0:
            limitations.append("Recent activity data is limited for the selected period.")
        if not employee.skills:
            limitations.append("Skill/tag metadata is limited.")
        return limitations

    @staticmethod
    def summary_text(employee_name: str, workload_level: str, work_metrics: dict[str, Any], project_metrics: dict[str, Any], attention_count: int) -> str:
        return (
            f"{employee_name}'s Digital Twin is {workload_level} from rule-based operational signals: "
            f"{work_metrics['current_open_work_count']} open assignment(s), {work_metrics['overdue_work_count']} overdue item(s), "
            f"{work_metrics['blocked_work_count']} blocked item(s), and {project_metrics['active_project_count']} active project(s). "
            f"{attention_count} planning attention area(s) are visible."
        )

    @staticmethod
    def record_generated_event(db: Session, *, snapshot: EmployeeDigitalTwinSnapshot, current_user: User) -> None:
        current_employee = linked_employee(db, current_user)
        EventService.record_event(
            db,
            company_id=snapshot.company_id,
            actor_user_id=current_user.id,
            actor_employee_id=current_employee.id if current_employee else None,
            event_type="employee_digital_twin.generated",
            title="Employee Digital Twin generated",
            description="A safe rule-based Employee Digital Twin snapshot was generated.",
            target_entity_type="employee_digital_twin_snapshot",
            target_entity_id=snapshot.id,
            related_entity_type="employee",
            related_entity_id=snapshot.employee_id,
            metadata={
                "company_id": str(snapshot.company_id),
                "employee_id": str(snapshot.employee_id),
                "actor_user_id": str(current_user.id),
                "snapshot_id": str(snapshot.id),
                "period_days": snapshot.period_days,
                "workload_level": snapshot.workload_level,
                "ai_narrative_used": snapshot.ai_narrative_used,
                "status": "generated",
            },
        )

    @staticmethod
    def notify_requester(db: Session, *, snapshot: EmployeeDigitalTwinSnapshot, current_user: User) -> None:
        current_employee = linked_employee(db, current_user)
        NotificationService.create_notification(
            db,
            company_id=snapshot.company_id,
            recipient_user_id=current_user.id,
            actor_user_id=current_user.id,
            actor_employee_id=current_employee.id if current_employee else None,
            title="Digital Twin generated",
            message=f"Employee Digital Twin snapshot is ready with {snapshot.workload_level} workload.",
            notification_type="employee_digital_twin.generated",
            target_entity_type="employee_digital_twin_snapshot",
            target_entity_id=snapshot.id,
            related_entity_type="employee",
            related_entity_id=snapshot.employee_id,
            priority="normal",
            action_url="#/my-digital-twin" if current_user.role == ROLE_EMPLOYEE else "#/employees",
            metadata={
                "snapshot_id": str(snapshot.id),
                "employee_id": str(snapshot.employee_id),
                "workload_level": snapshot.workload_level,
            },
        )
