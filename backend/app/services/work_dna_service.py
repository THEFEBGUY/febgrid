import re
from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.permissions import OWNER_ADMIN_ROLES, ROLE_MANAGER, ensure_company_access
from app.models.attachment import Attachment
from app.models.common import utc_now
from app.models.company import Company
from app.models.company_memory import CompanyMemory
from app.models.department import Department
from app.models.employee import Employee
from app.models.event import Event
from app.models.project import Project, ProjectMember
from app.models.team import Team
from app.models.user import User
from app.models.work_dna import WorkDNASnapshot
from app.models.work_object import WorkObject
from app.schemas.work_dna import WORK_DNA_PERIODS, WORK_DNA_SCOPE_TYPES
from app.services.event_service import EventService
from app.services.notification_service import NotificationService

OPEN_WORK_STATUSES = {"assigned", "pending", "in_progress", "under_review", "blocked"}
COMPLETED_WORK_STATUSES = {"completed", "done", "closed"}
HIGH_PRIORITIES = {"high", "critical", "urgent"}
BOTTLENECK_STATUSES = {"assigned", "in_progress", "under_review"}
MAX_WORK_ITEMS = 1200


def safe_text(value: Any, max_chars: int = 220, *, fallback: str | None = None) -> str | None:
    if value is None:
        return fallback
    text = str(value).strip()
    if not text:
        return fallback
    return text[:max_chars]


def normalized(value: str | None) -> str:
    text = (value or "unknown").strip().lower()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_") or "unknown"


def display_label(value: str | None) -> str:
    return normalized(value).replace("_", " ").title()


def percent(count: int, total: int) -> int:
    if total <= 0:
        return 0
    return int(round((count / total) * 100))


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


def actor_employee_id(db: Session, current_user: User | None) -> UUID | None:
    employee = linked_employee(db, current_user)
    return employee.id if employee is not None else None


def title_signature(value: str | None) -> str:
    words = re.findall(r"[a-z0-9]+", (value or "").lower())
    stop_words = {"the", "a", "an", "to", "for", "and", "or", "of", "in", "on", "with"}
    compact = [word for word in words if word not in stop_words]
    return " ".join(compact[:5]) or "untitled work"


class WorkDNAService:
    @staticmethod
    def validate_period(period_days: int) -> int:
        if period_days not in WORK_DNA_PERIODS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="period_days must be one of 7, 30, or 90")
        return period_days

    @staticmethod
    def validate_scope_type(scope_type: str) -> str:
        scope = normalized(scope_type)
        if scope not in WORK_DNA_SCOPE_TYPES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid Work DNA scope")
        return scope

    @classmethod
    def ensure_scope_access(
        cls,
        db: Session,
        *,
        company_id: UUID,
        scope_type: str,
        scope_id: UUID | None,
        current_user: User,
    ) -> dict[str, Any]:
        ensure_company_access(current_user, company_id)
        scope_type = cls.validate_scope_type(scope_type)
        employee = linked_employee(db, current_user)
        if scope_type == "company":
            if current_user.role not in OWNER_ADMIN_ROLES:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company-wide Work DNA requires owner or admin access")
            company = db.get(Company, company_id)
            if company is None or not company.is_active:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
            return {"scope_type": scope_type, "scope_id": None, "scope_label": company.name}

        if scope_id is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="scope_id is required for this Work DNA scope")

        if scope_type == "project":
            project = db.get(Project, scope_id)
            if project is None or project.company_id != company_id or not project.is_active:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
            if current_user.role in OWNER_ADMIN_ROLES or project.owner_user_id == current_user.id:
                return {"scope_type": scope_type, "scope_id": scope_id, "scope_label": project.name}
            if employee is not None:
                member = db.scalar(
                    select(ProjectMember).where(
                        ProjectMember.company_id == company_id,
                        ProjectMember.project_id == scope_id,
                        ProjectMember.employee_id == employee.id,
                        ProjectMember.is_active.is_(True),
                    )
                )
                if project.owner_employee_id == employee.id or member is not None:
                    return {"scope_type": scope_type, "scope_id": scope_id, "scope_label": project.name}
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Project Work DNA is not visible")

        if scope_type == "team":
            team = db.get(Team, scope_id)
            if team is None or team.company_id != company_id or not team.is_active:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found")
            if current_user.role in OWNER_ADMIN_ROLES:
                return {"scope_type": scope_type, "scope_id": scope_id, "scope_label": team.name}
            if current_user.role == ROLE_MANAGER and employee is not None and team.lead_employee_id == employee.id:
                return {"scope_type": scope_type, "scope_id": scope_id, "scope_label": team.name}
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Team Work DNA is not visible")

        department = db.get(Department, scope_id)
        if department is None or department.company_id != company_id or not department.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
        if current_user.role not in OWNER_ADMIN_ROLES:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Department Work DNA requires owner or admin access")
        return {"scope_type": scope_type, "scope_id": scope_id, "scope_label": department.name}

    @classmethod
    def latest_snapshot(
        cls,
        db: Session,
        *,
        company_id: UUID,
        scope_type: str,
        scope_id: UUID | None,
        current_user: User,
    ) -> WorkDNASnapshot | None:
        scope = cls.ensure_scope_access(db, company_id=company_id, scope_type=scope_type, scope_id=scope_id, current_user=current_user)
        statement = select(WorkDNASnapshot).where(
            WorkDNASnapshot.company_id == company_id,
            WorkDNASnapshot.scope_type == scope["scope_type"],
        )
        if scope["scope_id"] is None:
            statement = statement.where(WorkDNASnapshot.scope_id.is_(None))
        else:
            statement = statement.where(WorkDNASnapshot.scope_id == scope["scope_id"])
        return db.scalar(statement.order_by(WorkDNASnapshot.created_at.desc()).limit(1))

    @classmethod
    def history(
        cls,
        db: Session,
        *,
        company_id: UUID,
        scope_type: str,
        scope_id: UUID | None,
        current_user: User,
        limit: int = 20,
        offset: int = 0,
    ) -> list[WorkDNASnapshot]:
        scope = cls.ensure_scope_access(db, company_id=company_id, scope_type=scope_type, scope_id=scope_id, current_user=current_user)
        statement = select(WorkDNASnapshot).where(
            WorkDNASnapshot.company_id == company_id,
            WorkDNASnapshot.scope_type == scope["scope_type"],
        )
        if scope["scope_id"] is None:
            statement = statement.where(WorkDNASnapshot.scope_id.is_(None))
        else:
            statement = statement.where(WorkDNASnapshot.scope_id == scope["scope_id"])
        return list(
            db.scalars(
                statement.order_by(WorkDNASnapshot.created_at.desc())
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
        scope_type: str,
        scope_id: UUID | None,
        current_user: User,
        period_days: int,
    ) -> dict[str, Any]:
        period_days = cls.validate_period(period_days)
        scope = cls.ensure_scope_access(db, company_id=company_id, scope_type=scope_type, scope_id=scope_id, current_user=current_user)
        return cls.build_payload(db, company_id=company_id, scope=scope, current_user=current_user, period_days=period_days)

    @classmethod
    def generate_snapshot(
        cls,
        db: Session,
        *,
        company_id: UUID,
        scope_type: str,
        scope_id: UUID | None,
        current_user: User,
        period_days: int,
    ) -> WorkDNASnapshot:
        payload = cls.signals(
            db,
            company_id=company_id,
            scope_type=scope_type,
            scope_id=scope_id,
            current_user=current_user,
            period_days=period_days,
        )
        snapshot = WorkDNASnapshot(
            company_id=company_id,
            scope_type=payload["scope_type"],
            scope_id=payload["scope_id"],
            generated_by_user_id=current_user.id,
            period_days=payload["period_days"],
            period_start=payload["period_start"],
            period_end=payload["period_end"],
            overall_summary=payload["overall_summary"],
            work_volume_json=payload["work_volume"],
            work_type_distribution_json=payload["work_type_distribution"],
            status_distribution_json=payload["status_distribution"],
            priority_distribution_json=payload["priority_distribution"],
            completion_patterns_json=payload["completion_patterns"],
            overdue_patterns_json=payload["overdue_patterns"],
            blocked_patterns_json=payload["blocked_patterns"],
            workflow_patterns_json=payload["workflow_patterns"],
            project_patterns_json=payload["project_patterns"],
            department_patterns_json=payload["department_patterns"],
            team_patterns_json=payload["team_patterns"],
            tag_patterns_json=payload["tag_patterns"],
            recurring_patterns_json=payload["recurring_patterns"],
            deadline_patterns_json=payload["deadline_patterns"],
            bottlenecks_json=payload["bottlenecks"],
            operational_strengths_json=payload["operational_strengths"],
            attention_areas_json=payload["attention_areas"],
            risks_json=payload["risks"],
            recommended_improvements_json=payload["recommended_improvements"],
            template_candidates_json=payload["template_candidates"],
            automation_candidates_json=payload["automation_candidates"],
            source_counts_json=payload["source_counts"],
            data_coverage_json=payload["data_coverage"],
            limitations_json=payload["limitations"],
            is_rule_based=True,
            ai_narrative_used=False,
            provider_mode=payload.get("provider_mode"),
            provider_key=payload.get("provider_key"),
            model_name=payload.get("model_name"),
            metadata_json=payload["metadata"],
        )
        db.add(snapshot)
        db.flush()
        cls.record_generated_event(db, snapshot=snapshot, current_user=current_user)
        cls.notify_requester(db, snapshot=snapshot, current_user=current_user)
        return snapshot

    @classmethod
    def build_payload(
        cls,
        db: Session,
        *,
        company_id: UUID,
        scope: dict[str, Any],
        current_user: User,
        period_days: int,
    ) -> dict[str, Any]:
        now = utc_now()
        period_start = now - timedelta(days=period_days)
        projects = cls.map_projects(db, company_id=company_id)
        departments = cls.map_departments(db, company_id=company_id)
        teams = cls.map_teams(db, company_id=company_id)
        work_items = cls.collect_work_items(db, company_id=company_id, scope=scope, period_start=period_start)
        current_open = [item for item in work_items if normalized(item.status) in OPEN_WORK_STATUSES]
        completed_recent = [
            item
            for item in work_items
            if (item.completed_at is not None and item.completed_at >= period_start)
            or (normalized(item.status) in COMPLETED_WORK_STATUSES and item.updated_at >= period_start)
        ]
        overdue = [item for item in current_open if item.due_date is not None and item.due_date < now]
        blocked = [item for item in current_open if normalized(item.status) == "blocked"]
        high_priority_open = [item for item in current_open if normalized(item.priority) in HIGH_PRIORITIES]
        missing_due = [item for item in current_open if item.due_date is None]
        missing_project = [item for item in current_open if item.project_id is None]
        missing_tags = [item for item in current_open if not (item.tags if isinstance(item.tags, list) else [])]
        distributions = cls.distributions(work_items, projects, departments, teams)
        recurring_patterns = cls.recurring_patterns(work_items, projects, departments, teams)
        deadline_patterns = cls.deadline_patterns(current_open, now=now)
        completion_patterns = cls.completion_patterns(work_items, completed_recent)
        overdue_patterns = cls.overdue_patterns(distributions, overdue)
        blocked_patterns = cls.blocked_patterns(distributions, blocked)
        workflow_patterns = cls.workflow_patterns(current_open, now=now, missing_due_count=len(missing_due))
        bottlenecks = cls.bottlenecks(
            overdue_count=len(overdue),
            blocked_count=len(blocked),
            high_priority_open_count=len(high_priority_open),
            missing_due_count=len(missing_due),
            missing_project_count=len(missing_project),
            deadline_patterns=deadline_patterns,
            workflow_patterns=workflow_patterns,
            project_patterns=distributions["projects"],
        )
        strengths = cls.operational_strengths(
            total=len(work_items),
            completed_count=len(completed_recent),
            overdue_count=len(overdue),
            blocked_count=len(blocked),
            missing_due_count=len(missing_due),
            project_linked_count=len([item for item in current_open if item.project_id is not None]),
        )
        attention = cls.attention_areas(
            bottlenecks=bottlenecks,
            missing_tags_count=len(missing_tags),
            recurring_patterns=recurring_patterns,
        )
        risks = cls.risks(bottlenecks, overdue_count=len(overdue), blocked_count=len(blocked))
        recommended = cls.recommended_improvements(
            bottlenecks=bottlenecks,
            recurring_patterns=recurring_patterns,
            missing_due_count=len(missing_due),
            missing_project_count=len(missing_project),
            missing_tags_count=len(missing_tags),
        )
        template_candidates = cls.template_candidates(recurring_patterns, completion_patterns)
        automation_candidates = cls.automation_candidates(recurring_patterns, distributions["tags"])
        source_counts = cls.source_counts(db, company_id=company_id, scope=scope, work_items=work_items, period_start=period_start)
        coverage = cls.data_coverage(
            work_items=work_items,
            current_open=current_open,
            completed_recent=completed_recent,
            source_counts=source_counts,
            missing_due_count=len(missing_due),
            missing_project_count=len(missing_project),
            missing_tags_count=len(missing_tags),
        )
        limitations = cls.limitations(scope=scope, source_counts=source_counts, coverage=coverage)
        work_volume = {
            "total_analyzed": len(work_items),
            "current_open": len(current_open),
            "completed_in_period": len(completed_recent),
            "overdue": len(overdue),
            "blocked": len(blocked),
            "high_priority_open": len(high_priority_open),
            "missing_due_dates": len(missing_due),
            "missing_project_links": len(missing_project),
            "missing_tags": len(missing_tags),
            "period_days": period_days,
        }
        overall_summary = cls.summary_text(
            scope_label=scope["scope_label"],
            total=len(work_items),
            open_count=len(current_open),
            completed_count=len(completed_recent),
            bottleneck_count=len(bottlenecks),
            recurring_count=len(recurring_patterns),
            period_days=period_days,
        )
        return {
            "company_id": company_id,
            "scope_type": scope["scope_type"],
            "scope_id": scope["scope_id"],
            "period_days": period_days,
            "period_start": period_start,
            "period_end": now,
            "overall_summary": overall_summary,
            "work_volume": work_volume,
            "work_type_distribution": distributions["types"],
            "status_distribution": distributions["statuses"],
            "priority_distribution": distributions["priorities"],
            "completion_patterns": completion_patterns,
            "overdue_patterns": overdue_patterns,
            "blocked_patterns": blocked_patterns,
            "workflow_patterns": workflow_patterns,
            "project_patterns": distributions["projects"],
            "department_patterns": distributions["departments"],
            "team_patterns": distributions["teams"],
            "tag_patterns": distributions["tags"],
            "recurring_patterns": recurring_patterns,
            "deadline_patterns": deadline_patterns,
            "bottlenecks": bottlenecks,
            "operational_strengths": strengths,
            "attention_areas": attention,
            "risks": risks,
            "recommended_improvements": recommended,
            "template_candidates": template_candidates,
            "automation_candidates": automation_candidates,
            "source_counts": source_counts,
            "data_coverage": coverage,
            "limitations": limitations,
            "generated_at": now,
            "is_rule_based": True,
            "ai_narrative_used": False,
            "provider_mode": "rule_based",
            "provider_key": "rule_based",
            "model_name": None,
            "metadata": {
                "methodology": "Rule-based work-system pattern analysis from work objects, safe project/team/department links, event counts, files, and approved Company Memory counts.",
                "privacy_notice": "Work DNA analyzes work patterns only. It does not score, rank, compare, profile, or judge employees.",
                "scope_label": scope["scope_label"],
                "external_ai_used": False,
                "generated_by_user_id": str(current_user.id),
                "max_work_items": MAX_WORK_ITEMS,
            },
        }

    @staticmethod
    def collect_work_items(db: Session, *, company_id: UUID, scope: dict[str, Any], period_start: Any) -> list[WorkObject]:
        criteria: list[Any] = [WorkObject.company_id == company_id, WorkObject.is_active.is_(True)]
        if scope["scope_type"] == "project":
            criteria.append(WorkObject.project_id == scope["scope_id"])
        elif scope["scope_type"] == "department":
            criteria.append(WorkObject.department_id == scope["scope_id"])
        elif scope["scope_type"] == "team":
            criteria.append(WorkObject.team_id == scope["scope_id"])
        criteria.append(
            or_(
                WorkObject.status.in_(list(OPEN_WORK_STATUSES)),
                WorkObject.created_at >= period_start,
                WorkObject.updated_at >= period_start,
                WorkObject.completed_at >= period_start,
                WorkObject.due_date >= period_start,
            )
        )
        return list(
            db.scalars(select(WorkObject).where(*criteria).order_by(WorkObject.updated_at.desc()).limit(MAX_WORK_ITEMS)).all()
        )

    @staticmethod
    def map_projects(db: Session, *, company_id: UUID) -> dict[UUID, Project]:
        return {item.id: item for item in db.scalars(select(Project).where(Project.company_id == company_id)).all()}

    @staticmethod
    def map_departments(db: Session, *, company_id: UUID) -> dict[UUID, Department]:
        return {item.id: item for item in db.scalars(select(Department).where(Department.company_id == company_id)).all()}

    @staticmethod
    def map_teams(db: Session, *, company_id: UUID) -> dict[UUID, Team]:
        return {item.id: item for item in db.scalars(select(Team).where(Team.company_id == company_id)).all()}

    @classmethod
    def distributions(
        cls,
        work_items: list[WorkObject],
        projects: dict[UUID, Project],
        departments: dict[UUID, Department],
        teams: dict[UUID, Team],
    ) -> dict[str, list[dict[str, Any]]]:
        def linked_name(key: str, records: dict[UUID, Any], fallback: str) -> str:
            if not key or key.startswith("unlinked_"):
                return fallback
            try:
                record = records.get(UUID(key))
            except (TypeError, ValueError):
                return fallback
            return safe_text(getattr(record, "name", None), fallback=fallback)

        return {
            "types": cls.distribution(work_items, key=lambda item: normalized(item.object_type), label=lambda key: display_label(key)),
            "statuses": cls.distribution(work_items, key=lambda item: normalized(item.status), label=lambda key: display_label(key)),
            "priorities": cls.distribution(work_items, key=lambda item: normalized(item.priority), label=lambda key: display_label(key)),
            "projects": cls.distribution(
                work_items,
                key=lambda item: str(item.project_id) if item.project_id else "unlinked_project",
                label=lambda key: linked_name(key, projects, "No linked project"),
            ),
            "departments": cls.distribution(
                work_items,
                key=lambda item: str(item.department_id) if item.department_id else "unlinked_department",
                label=lambda key: linked_name(key, departments, "No linked department"),
            ),
            "teams": cls.distribution(
                work_items,
                key=lambda item: str(item.team_id) if item.team_id else "unlinked_team",
                label=lambda key: linked_name(key, teams, "No linked team"),
            ),
            "tags": cls.tag_distribution(work_items),
        }

    @staticmethod
    def distribution(work_items: list[WorkObject], *, key: Any, label: Any) -> list[dict[str, Any]]:
        total = len(work_items)
        groups: dict[str, list[WorkObject]] = defaultdict(list)
        for item in work_items:
            groups[str(key(item))].append(item)
        rows = []
        for group_key, items in groups.items():
            open_items = [item for item in items if normalized(item.status) in OPEN_WORK_STATUSES]
            completed_items = [item for item in items if normalized(item.status) in COMPLETED_WORK_STATUSES or item.completed_at is not None]
            overdue_items = [item for item in open_items if item.due_date is not None and item.due_date < utc_now()]
            blocked_items = [item for item in open_items if normalized(item.status) == "blocked"]
            rows.append(
                {
                    "key": group_key,
                    "label": safe_text(label(group_key), 120) or "Unknown",
                    "count": len(items),
                    "percentage": percent(len(items), total),
                    "completed_count": len(completed_items),
                    "open_count": len(open_items),
                    "overdue_count": len(overdue_items),
                    "blocked_count": len(blocked_items),
                }
            )
        return sorted(rows, key=lambda row: (-row["count"], row["label"]))[:20]

    @staticmethod
    def tag_distribution(work_items: list[WorkObject]) -> list[dict[str, Any]]:
        tag_items: dict[str, list[WorkObject]] = defaultdict(list)
        for item in work_items:
            for tag in item.tags if isinstance(item.tags, list) else []:
                tag_items[normalized(str(tag))].append(item)
        total_tags = sum(len(items) for items in tag_items.values())
        rows = []
        for tag, items in tag_items.items():
            open_items = [item for item in items if normalized(item.status) in OPEN_WORK_STATUSES]
            rows.append(
                {
                    "key": tag,
                    "label": display_label(tag),
                    "count": len(items),
                    "percentage": percent(len(items), total_tags),
                    "open_count": len(open_items),
                    "overdue_count": len([item for item in open_items if item.due_date is not None and item.due_date < utc_now()]),
                    "blocked_count": len([item for item in open_items if normalized(item.status) == "blocked"]),
                }
            )
        return sorted(rows, key=lambda row: (-row["count"], row["label"]))[:20]

    @staticmethod
    def recurring_patterns(
        work_items: list[WorkObject],
        projects: dict[UUID, Project],
        departments: dict[UUID, Department],
        teams: dict[UUID, Team],
    ) -> list[dict[str, Any]]:
        groups: dict[str, list[WorkObject]] = defaultdict(list)
        for item in work_items:
            groups[f"{normalized(item.object_type)}:{title_signature(item.title)}"].append(item)
        patterns = []
        for signature, items in groups.items():
            if len(items) < 2:
                continue
            common_tags = Counter(tag for item in items for tag in (item.tags if isinstance(item.tags, list) else [])).most_common(5)
            project = projects.get(items[0].project_id) if items[0].project_id else None
            department = departments.get(items[0].department_id) if items[0].department_id else None
            team = teams.get(items[0].team_id) if items[0].team_id else None
            patterns.append(
                {
                    "pattern_name": display_label(signature.split(":", 1)[1]),
                    "occurrence_count": len(items),
                    "common_type": display_label(items[0].object_type),
                    "common_tags": [safe_text(tag, 80) for tag, _ in common_tags],
                    "common_project": safe_text(project.name) if project else None,
                    "common_department": safe_text(department.name) if department else None,
                    "common_team": safe_text(team.name) if team else None,
                    "evidence": f"{len(items)} similar work object(s) share type/title structure.",
                    "suggested_template_action": "Review this repeated pattern as a candidate reusable workflow template.",
                    "confidence": "medium" if len(items) >= 3 else "limited",
                }
            )
        return sorted(patterns, key=lambda item: -item["occurrence_count"])[:12]

    @staticmethod
    def deadline_patterns(current_open: list[WorkObject], *, now: Any) -> list[dict[str, Any]]:
        due_items = [item for item in current_open if item.due_date is not None]
        by_week: dict[str, list[WorkObject]] = defaultdict(list)
        due_next_7 = 0
        for item in due_items:
            if item.due_date <= now + timedelta(days=7):
                due_next_7 += 1
            year, week, _ = item.due_date.isocalendar()
            by_week[f"{year}-W{week:02d}"].append(item)
        patterns = []
        if due_next_7 >= 3:
            patterns.append(
                {
                    "pattern": "Near-term deadline concentration",
                    "count": due_next_7,
                    "evidence": f"{due_next_7} open work item(s) are due within the next 7 days.",
                    "recommended_action": "Review near-term deadlines and clarify which items should move first.",
                }
            )
        for week_key, items in by_week.items():
            if len(items) >= 3:
                patterns.append(
                    {
                        "pattern": f"Deadline cluster {week_key}",
                        "count": len(items),
                        "evidence": f"{len(items)} open work item(s) share the same due week.",
                        "recommended_action": "Check whether the deadline cluster needs staged reviews or workload smoothing.",
                    }
                )
        return patterns[:10]

    @staticmethod
    def completion_patterns(work_items: list[WorkObject], completed_recent: list[WorkObject]) -> list[dict[str, Any]]:
        if not work_items:
            return []
        rows: list[dict[str, Any]] = []
        by_type = Counter(normalized(item.object_type) for item in completed_recent)
        for object_type, count in by_type.most_common(8):
            rows.append(
                {
                    "pattern": f"{display_label(object_type)} completion",
                    "completed_count": count,
                    "evidence": f"{count} {display_label(object_type).lower()} item(s) were completed in the selected period.",
                }
            )
        if completed_recent:
            rows.insert(
                0,
                {
                    "pattern": "Recent completion flow",
                    "completed_count": len(completed_recent),
                    "evidence": f"{len(completed_recent)} work item(s) completed or moved to completed state in the selected period.",
                },
            )
        return rows[:10]

    @staticmethod
    def overdue_patterns(distributions: dict[str, list[dict[str, Any]]], overdue_items: list[WorkObject]) -> list[dict[str, Any]]:
        patterns: list[dict[str, Any]] = []
        for section in ("types", "projects", "teams", "tags"):
            for row in distributions[section]:
                if row.get("overdue_count", 0) >= 1 and (row["overdue_count"] >= 2 or percent(row["overdue_count"], row["open_count"] or 1) >= 30):
                    patterns.append(
                        {
                            "scope": section,
                            "label": row["label"],
                            "count": row["overdue_count"],
                            "percentage_of_open": percent(row["overdue_count"], row["open_count"] or 1),
                            "evidence": f"{row['overdue_count']} open item(s) in {row['label']} are overdue.",
                        }
                    )
        if overdue_items and not patterns:
            patterns.append({"scope": "overall", "label": "Overdue work", "count": len(overdue_items), "evidence": f"{len(overdue_items)} open item(s) are overdue."})
        return patterns[:10]

    @staticmethod
    def blocked_patterns(distributions: dict[str, list[dict[str, Any]]], blocked_items: list[WorkObject]) -> list[dict[str, Any]]:
        patterns: list[dict[str, Any]] = []
        for section in ("types", "projects", "teams", "tags"):
            for row in distributions[section]:
                if row.get("blocked_count", 0) >= 1 and (row["blocked_count"] >= 2 or percent(row["blocked_count"], row["open_count"] or 1) >= 30):
                    patterns.append(
                        {
                            "scope": section,
                            "label": row["label"],
                            "count": row["blocked_count"],
                            "percentage_of_open": percent(row["blocked_count"], row["open_count"] or 1),
                            "evidence": f"{row['blocked_count']} open item(s) in {row['label']} are blocked.",
                        }
                    )
        if blocked_items and not patterns:
            patterns.append({"scope": "overall", "label": "Blocked work", "count": len(blocked_items), "evidence": f"{len(blocked_items)} open item(s) are blocked."})
        return patterns[:10]

    @staticmethod
    def workflow_patterns(current_open: list[WorkObject], *, now: Any, missing_due_count: int) -> list[dict[str, Any]]:
        patterns: list[dict[str, Any]] = []
        for status_name in BOTTLENECK_STATUSES:
            stuck = [item for item in current_open if normalized(item.status) == status_name and item.updated_at < now - timedelta(days=7)]
            if stuck:
                patterns.append(
                    {
                        "stage": display_label(status_name),
                        "count": len(stuck),
                        "evidence": f"{len(stuck)} item(s) have stayed in {display_label(status_name).lower()} for more than 7 days without a recent update.",
                        "recommended_action": "Confirm whether these items need clearer next steps or status updates.",
                    }
                )
        if missing_due_count:
            patterns.append(
                {
                    "stage": "Planning metadata",
                    "count": missing_due_count,
                    "evidence": f"{missing_due_count} open item(s) do not have due dates.",
                    "recommended_action": "Add due dates where they help coordinate delivery expectations.",
                }
            )
        return patterns[:10]

    @staticmethod
    def bottlenecks(
        *,
        overdue_count: int,
        blocked_count: int,
        high_priority_open_count: int,
        missing_due_count: int,
        missing_project_count: int,
        deadline_patterns: list[dict[str, Any]],
        workflow_patterns: list[dict[str, Any]],
        project_patterns: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        bottlenecks: list[dict[str, Any]] = []
        if overdue_count:
            bottlenecks.append({"type": "overdue_work", "count": overdue_count, "evidence": f"{overdue_count} open work item(s) are overdue.", "severity": "medium" if overdue_count < 3 else "high"})
        if blocked_count:
            bottlenecks.append({"type": "blocked_work", "count": blocked_count, "evidence": f"{blocked_count} open work item(s) are blocked.", "severity": "medium" if blocked_count < 3 else "high"})
        if high_priority_open_count >= 3:
            bottlenecks.append({"type": "priority_concentration", "count": high_priority_open_count, "evidence": f"{high_priority_open_count} high/critical/urgent item(s) are open simultaneously.", "severity": "medium"})
        if missing_due_count >= 2:
            bottlenecks.append({"type": "missing_due_dates", "count": missing_due_count, "evidence": f"{missing_due_count} open item(s) lack due dates.", "severity": "low"})
        if missing_project_count >= 3:
            bottlenecks.append({"type": "missing_project_links", "count": missing_project_count, "evidence": f"{missing_project_count} open item(s) are not linked to a project.", "severity": "low"})
        for pattern in deadline_patterns[:3]:
            bottlenecks.append({"type": "deadline_clustering", "count": pattern["count"], "evidence": pattern["evidence"], "severity": "medium"})
        for pattern in workflow_patterns[:3]:
            if pattern.get("stage") != "Planning metadata":
                bottlenecks.append({"type": "workflow_stage", "count": pattern["count"], "evidence": pattern["evidence"], "severity": "medium"})
        for project in project_patterns[:3]:
            if project["open_count"] >= 1 and project["percentage"] >= 50:
                bottlenecks.append({"type": "project_load_concentration", "count": project["open_count"], "evidence": f"{project['label']} carries {project['percentage']}% of analyzed work.", "severity": "medium"})
        return bottlenecks[:12]

    @staticmethod
    def operational_strengths(
        *,
        total: int,
        completed_count: int,
        overdue_count: int,
        blocked_count: int,
        missing_due_count: int,
        project_linked_count: int,
    ) -> list[str]:
        strengths: list[str] = []
        if completed_count:
            strengths.append(f"{completed_count} work item(s) completed during the selected period.")
        if total and overdue_count == 0:
            strengths.append("No overdue open work is visible in the analyzed scope.")
        if total and blocked_count == 0:
            strengths.append("No blocked open work is visible in the analyzed scope.")
        if total and percent(project_linked_count, max(total, 1)) >= 70:
            strengths.append("Most analyzed open work is linked to projects, which improves operational traceability.")
        if total and percent(total - missing_due_count, total) >= 70:
            strengths.append("Due-date coverage is reasonably strong for current open work.")
        return strengths[:8] or ["Evidence is still limited; add more work history to identify durable operational strengths."]

    @staticmethod
    def attention_areas(*, bottlenecks: list[dict[str, Any]], missing_tags_count: int, recurring_patterns: list[dict[str, Any]]) -> list[str]:
        areas = [str(item["evidence"]) for item in bottlenecks[:6]]
        if missing_tags_count >= 3:
            areas.append(f"{missing_tags_count} open item(s) have no tags; standard tags would improve future pattern detection.")
        if recurring_patterns:
            areas.append(f"{len(recurring_patterns)} recurring work pattern(s) may be worth reviewing as reusable workflows.")
        return areas[:8] or ["No major work-system attention area is visible from current evidence."]

    @staticmethod
    def risks(bottlenecks: list[dict[str, Any]], *, overdue_count: int, blocked_count: int) -> list[str]:
        risks = []
        if overdue_count:
            risks.append("Overdue work may create delivery pressure if due dates are not reset or cleared.")
        if blocked_count:
            risks.append("Blocked work may hide dependency or decision delays that need a clearer next action.")
        for item in bottlenecks:
            if item.get("severity") == "high":
                risks.append(str(item["evidence"]))
        return risks[:8] or ["No major work-system risk is visible from the current rule-based analysis."]

    @staticmethod
    def recommended_improvements(
        *,
        bottlenecks: list[dict[str, Any]],
        recurring_patterns: list[dict[str, Any]],
        missing_due_count: int,
        missing_project_count: int,
        missing_tags_count: int,
    ) -> list[str]:
        actions: list[str] = []
        if any(item["type"] == "overdue_work" for item in bottlenecks):
            actions.append("Review overdue work and update the next realistic owner/date/status in FebGrid.")
        if any(item["type"] == "blocked_work" for item in bottlenecks):
            actions.append("Clarify blocked dependencies and record the next unblock decision as a comment or event.")
        if any(item["type"] == "priority_concentration" for item in bottlenecks):
            actions.append("Reduce simultaneous urgent/high-priority work by agreeing on an explicit priority order.")
        if missing_due_count:
            actions.append("Add due dates to current work where timing matters.")
        if missing_project_count:
            actions.append("Link operational work to projects when it contributes to delivery tracking.")
        if missing_tags_count:
            actions.append("Standardize tags for recurring categories like bugs, approvals, reviews, onboarding, and reports.")
        if recurring_patterns:
            actions.append("Turn repeated work patterns into reusable Work Object templates after owner/admin review.")
        actions.append("Treat Work DNA as process intelligence only; do not use it as employee evaluation or ranking.")
        return actions[:8]

    @staticmethod
    def template_candidates(recurring_patterns: list[dict[str, Any]], completion_patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        candidates = [
            {
                "name": pattern["pattern_name"],
                "occurrence_count": pattern["occurrence_count"],
                "evidence": pattern["evidence"],
                "suggested_template_action": pattern["suggested_template_action"],
                "confidence": pattern["confidence"],
            }
            for pattern in recurring_patterns[:8]
        ]
        if completion_patterns and not candidates:
            candidates.append(
                {
                    "name": "Recently completed work flow",
                    "occurrence_count": completion_patterns[0].get("completed_count", 0),
                    "evidence": completion_patterns[0].get("evidence"),
                    "suggested_template_action": "Review recently completed work to decide whether a repeatable checklist would help.",
                    "confidence": "limited",
                }
            )
        return candidates[:8]

    @staticmethod
    def automation_candidates(recurring_patterns: list[dict[str, Any]], tag_patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
        keywords = {"approval", "review", "report", "onboarding", "follow", "reminder", "checklist", "bug", "verification"}
        candidates = []
        for pattern in recurring_patterns:
            text = f"{pattern['pattern_name']} {' '.join(pattern.get('common_tags') or [])}".lower()
            if any(keyword in text for keyword in keywords):
                candidates.append(
                    {
                        "name": pattern["pattern_name"],
                        "occurrence_count": pattern["occurrence_count"],
                        "evidence": pattern["evidence"],
                        "manual_automation_idea": "Consider a saved checklist/template or reminder pattern. Do not automate status changes without human review.",
                        "confidence": pattern["confidence"],
                    }
                )
        for tag in tag_patterns[:5]:
            text = str(tag["label"]).lower()
            if tag["count"] >= 3 and any(keyword in text for keyword in keywords):
                candidates.append(
                    {
                        "name": f"{tag['label']} process",
                        "occurrence_count": tag["count"],
                        "evidence": f"{tag['count']} work item(s) use the {tag['label']} tag.",
                        "manual_automation_idea": "Consider a standardized intake or follow-up checklist.",
                        "confidence": "limited",
                    }
                )
        return candidates[:8]

    @staticmethod
    def source_counts(db: Session, *, company_id: UUID, scope: dict[str, Any], work_items: list[WorkObject], period_start: Any) -> dict[str, Any]:
        scope_filters: list[Any] = []
        if scope["scope_type"] == "project":
            scope_filters.append(WorkObject.project_id == scope["scope_id"])
        elif scope["scope_type"] == "department":
            scope_filters.append(WorkObject.department_id == scope["scope_id"])
        elif scope["scope_type"] == "team":
            scope_filters.append(WorkObject.team_id == scope["scope_id"])
        event_count = int(
            db.scalar(
                select(func.count()).select_from(Event).where(Event.company_id == company_id, Event.created_at >= period_start)
            )
            or 0
        )
        file_count = int(db.scalar(select(func.count()).select_from(Attachment).where(Attachment.company_id == company_id, Attachment.is_active.is_(True), Attachment.is_deleted.is_(False))) or 0)
        memory_count = int(
            db.scalar(
                select(func.count()).select_from(CompanyMemory).where(
                    CompanyMemory.company_id == company_id,
                    CompanyMemory.status == "approved",
                    CompanyMemory.memory_type.in_(["process", "work_context", "project_context", "operational_fact"]),
                )
            )
            or 0
        )
        return {
            "work_objects": len(work_items),
            "events_in_period": event_count,
            "active_files": file_count,
            "approved_process_memories": memory_count,
            "scope_type": scope["scope_type"],
            "scope_id": str(scope["scope_id"]) if scope["scope_id"] else None,
            "bounded_to_max_work_items": len(work_items) >= MAX_WORK_ITEMS,
        }

    @staticmethod
    def data_coverage(
        *,
        work_items: list[WorkObject],
        current_open: list[WorkObject],
        completed_recent: list[WorkObject],
        source_counts: dict[str, Any],
        missing_due_count: int,
        missing_project_count: int,
        missing_tags_count: int,
    ) -> dict[str, Any]:
        open_count = len(current_open)
        coverage_signals = int(bool(work_items)) + int(bool(completed_recent)) + int(bool(source_counts["events_in_period"])) + int(bool(source_counts["approved_process_memories"]))
        if coverage_signals >= 3:
            level = "good"
        elif coverage_signals >= 1:
            level = "limited"
        else:
            level = "minimal"
        return {
            "coverage_level": level,
            "has_work_data": bool(work_items),
            "has_completed_work": bool(completed_recent),
            "has_event_context": bool(source_counts["events_in_period"]),
            "has_process_memory_context": bool(source_counts["approved_process_memories"]),
            "due_date_coverage_percent": percent(open_count - missing_due_count, open_count) if open_count else 0,
            "project_link_coverage_percent": percent(open_count - missing_project_count, open_count) if open_count else 0,
            "tag_coverage_percent": percent(open_count - missing_tags_count, open_count) if open_count else 0,
        }

    @staticmethod
    def limitations(*, scope: dict[str, Any], source_counts: dict[str, Any], coverage: dict[str, Any]) -> list[str]:
        limitations = [
            "Work DNA v1 is rule-based operational pattern analysis, not an employee performance score.",
            "It does not rank employees, infer traits, make employment decisions, or perform autonomous actions.",
        ]
        if coverage["coverage_level"] != "good":
            limitations.append("Evidence is limited; results should be treated as directional until more work history exists.")
        if source_counts["bounded_to_max_work_items"]:
            limitations.append(f"Analysis was bounded to the latest {MAX_WORK_ITEMS} work objects for safety and performance.")
        if scope["scope_type"] == "department":
            limitations.append("Department-scope access is owner/admin-only because no dedicated department manager mapping is currently available.")
        return limitations

    @staticmethod
    def summary_text(*, scope_label: str, total: int, open_count: int, completed_count: int, bottleneck_count: int, recurring_count: int, period_days: int) -> str:
        if total == 0:
            return f"{scope_label} has no visible work objects for Work DNA in the selected {period_days}-day window."
        return (
            f"{scope_label} Work DNA reviewed {total} work item(s): {open_count} currently open, "
            f"{completed_count} completed in the selected {period_days}-day period, {bottleneck_count} process bottleneck signal(s), "
            f"and {recurring_count} recurring work pattern(s). Recommendations are advisory and focus on work-system improvements."
        )

    @staticmethod
    def record_generated_event(db: Session, *, snapshot: WorkDNASnapshot, current_user: User) -> None:
        EventService.record_event(
            db,
            company_id=snapshot.company_id,
            actor_user_id=current_user.id,
            actor_employee_id=actor_employee_id(db, current_user),
            event_type="work_dna.generated",
            title="Work DNA generated",
            description=f"Work DNA generated for {snapshot.scope_type} scope over {snapshot.period_days} days.",
            target_entity_type="work_dna_snapshot",
            target_entity_id=snapshot.id,
            related_entity_type=snapshot.scope_type,
            related_entity_id=snapshot.scope_id,
            metadata={
                "company_id": str(snapshot.company_id),
                "actor_user_id": str(current_user.id),
                "snapshot_id": str(snapshot.id),
                "scope_type": snapshot.scope_type,
                "scope_id": str(snapshot.scope_id) if snapshot.scope_id else None,
                "period_days": snapshot.period_days,
                "recurring_pattern_count": len(snapshot.recurring_patterns_json or []),
                "bottleneck_count": len(snapshot.bottlenecks_json or []),
                "template_candidate_count": len(snapshot.template_candidates_json or []),
                "ai_narrative_used": snapshot.ai_narrative_used,
                "status": "generated",
            },
        )

    @staticmethod
    def notify_requester(db: Session, *, snapshot: WorkDNASnapshot, current_user: User) -> None:
        NotificationService.create_notification(
            db,
            company_id=snapshot.company_id,
            recipient_user_id=current_user.id,
            actor_user_id=current_user.id,
            actor_employee_id=actor_employee_id(db, current_user),
            title="Work DNA generated",
            message=f"Work DNA is ready for {snapshot.scope_type} scope with {len(snapshot.bottlenecks_json or [])} bottleneck signal(s).",
            notification_type="work_dna.generated",
            target_entity_type="work_dna_snapshot",
            target_entity_id=snapshot.id,
            related_entity_type=snapshot.scope_type,
            related_entity_id=snapshot.scope_id,
            priority="normal",
            action_url="#/work-dna",
            metadata={
                "snapshot_id": str(snapshot.id),
                "scope_type": snapshot.scope_type,
                "scope_id": str(snapshot.scope_id) if snapshot.scope_id else None,
                "period_days": snapshot.period_days,
            },
        )
