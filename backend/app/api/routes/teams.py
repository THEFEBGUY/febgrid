from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session
from app.api.utils import ensure_company, get_or_404, update_model
from app.models.company import Company
from app.models.employee import Employee
from app.models.team import Team, TeamMember
from app.schemas.team import TeamCreate, TeamMemberCreate, TeamMemberRead, TeamRead, TeamUpdate
from app.services.event_service import EventService

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
def create_team(payload: TeamCreate, db: Session = Depends(db_session)) -> Team:
    get_or_404(db, Company, payload.company_id, label="Company")
    if payload.lead_employee_id:
        lead = get_or_404(db, Employee, payload.lead_employee_id, label="Team lead")
        ensure_company(lead, payload.company_id, label="Team lead")

    team = Team(
        company_id=payload.company_id,
        lead_employee_id=payload.lead_employee_id,
        name=payload.name,
        department=payload.department,
        description=payload.description,
    )
    db.add(team)
    db.flush()
    EventService.record_event(
        db,
        company_id=team.company_id,
        actor_employee_id=team.lead_employee_id,
        event_type="team.created",
        title=f"{team.name} created",
        target_entity_type="team",
        target_entity_id=team.id,
        metadata={"department": team.department},
    )
    db.commit()
    db.refresh(team)
    return team


@router.get("", response_model=list[TeamRead])
def list_teams(
    company_id: UUID,
    db: Session = Depends(db_session),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[Team]:
    statement = (
        select(Team)
        .where(Team.company_id == company_id)
        .order_by(Team.name.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.scalars(statement).all())


@router.get("/{team_id}", response_model=TeamRead)
def get_team(team_id: UUID, company_id: UUID, db: Session = Depends(db_session)) -> Team:
    team = get_or_404(db, Team, team_id, label="Team")
    ensure_company(team, company_id, label="Team")
    return team


@router.put("/{team_id}", response_model=TeamRead)
def update_team(team_id: UUID, company_id: UUID, payload: TeamUpdate, db: Session = Depends(db_session)) -> Team:
    team = get_or_404(db, Team, team_id, label="Team")
    ensure_company(team, company_id, label="Team")
    if payload.lead_employee_id:
        lead = get_or_404(db, Employee, payload.lead_employee_id, label="Team lead")
        ensure_company(lead, company_id, label="Team lead")
    changed = update_model(team, payload)
    if changed:
        EventService.record_event(
            db,
            company_id=company_id,
            actor_employee_id=team.lead_employee_id,
            event_type="team.updated",
            title=f"{team.name} updated",
            target_entity_type="team",
            target_entity_id=team.id,
            metadata={"changed_fields": sorted(changed.keys())},
        )
    db.commit()
    db.refresh(team)
    return team


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_team(
    team_id: UUID,
    company_id: UUID,
    actor_employee_id: UUID | None = None,
    db: Session = Depends(db_session),
) -> Response:
    team = get_or_404(db, Team, team_id, label="Team")
    ensure_company(team, company_id, label="Team")
    EventService.record_event(
        db,
        company_id=company_id,
        actor_employee_id=actor_employee_id,
        event_type="team.deleted",
        title=f"{team.name} deleted",
        target_entity_type="team",
        target_entity_id=team.id,
    )
    db.delete(team)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{team_id}/members", response_model=TeamMemberRead, status_code=status.HTTP_201_CREATED)
def add_team_member(team_id: UUID, payload: TeamMemberCreate, db: Session = Depends(db_session)) -> TeamMember:
    team = get_or_404(db, Team, team_id, label="Team")
    ensure_company(team, payload.company_id, label="Team")
    employee = get_or_404(db, Employee, payload.employee_id, label="Employee")
    ensure_company(employee, payload.company_id, label="Employee")

    member = TeamMember(company_id=payload.company_id, team_id=team_id, employee_id=payload.employee_id)
    db.add(member)
    db.flush()
    EventService.record_event(
        db,
        company_id=payload.company_id,
        actor_employee_id=team.lead_employee_id,
        event_type="team.member_added",
        title=f"{employee.full_name} added to {team.name}",
        target_entity_type="team",
        target_entity_id=team.id,
        metadata={"employee_id": str(employee.id)},
    )
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{team_id}/members/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_team_member(
    team_id: UUID,
    employee_id: UUID,
    company_id: UUID,
    actor_employee_id: UUID | None = None,
    db: Session = Depends(db_session),
) -> Response:
    team = get_or_404(db, Team, team_id, label="Team")
    ensure_company(team, company_id, label="Team")
    statement = select(TeamMember).where(
        TeamMember.company_id == company_id,
        TeamMember.team_id == team_id,
        TeamMember.employee_id == employee_id,
    )
    member = db.scalar(statement)
    if member is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    EventService.record_event(
        db,
        company_id=company_id,
        actor_employee_id=actor_employee_id,
        event_type="team.member_removed",
        title=f"Employee removed from {team.name}",
        target_entity_type="team",
        target_entity_id=team.id,
        metadata={"employee_id": str(employee_id)},
    )
    db.delete(member)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
