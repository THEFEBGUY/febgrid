from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_company, get_current_user
from app.core.permissions import ROLE_COMPANY_OWNER
from app.core.security import create_access_token, hash_password, verify_password
from app.models.company import Company
from app.models.employee import Employee
from app.models.user import User
from app.schemas.auth import AuthMeRead, AuthSessionRead, LoginRequest, LogoutRead, RegisterRequest
from app.schemas.employee import EmployeeRead
from app.services.event_service import EventService

router = APIRouter(prefix="/auth", tags=["auth"])


def normalize_email(email: str) -> str:
    return email.strip().lower()


def build_auth_session(user: User, company: Company) -> AuthSessionRead:
    token = create_access_token(user_id=user.id, company_id=user.company_id, role=user.role)
    return AuthSessionRead(access_token=token, user=user, company=company)


def get_linked_employee(db: Session, user: User) -> Employee | None:
    return db.scalar(
        select(Employee).where(
            Employee.company_id == user.company_id,
            Employee.user_id == user.id,
            Employee.is_active.is_(True),
        )
    )


def set_employee_presence(db: Session, user: User, status_value: str, source: str) -> Employee | None:
    employee = get_linked_employee(db, user)
    if employee is None:
        return None

    previous_status = employee.status
    if previous_status == status_value:
        return employee

    employee.status = status_value
    EventService.record_event(
        db,
        company_id=user.company_id,
        actor_user_id=user.id,
        actor_employee_id=employee.id,
        event_type="employee.status_changed",
        title=f"{employee.full_name} is {status_value}",
        description=f"Employee presence changed to {status_value}.",
        target_entity_type="employee",
        target_entity_id=employee.id,
        metadata={"from": previous_status, "to": status_value, "source": source},
    )
    return employee


@router.post("/register", response_model=AuthSessionRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(db_session)) -> AuthSessionRead:
    email = normalize_email(str(payload.email))
    existing_user = db.scalar(select(User).where(User.email == email))
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this email already exists")

    existing_company = db.scalar(select(Company).where(Company.slug == payload.company_slug))
    if existing_company is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A company with this slug already exists")

    company = Company(
        name=payload.company_name.strip(),
        slug=payload.company_slug,
        industry=payload.industry,
        size=payload.size,
        timezone=payload.timezone,
        settings_json={},
    )
    db.add(company)
    db.flush()

    user = User(
        company_id=company.id,
        full_name=payload.full_name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role=ROLE_COMPANY_OWNER,
        auth_provider="local",
        is_active=True,
        last_login_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.flush()

    EventService.record_event(
        db,
        company_id=company.id,
        event_type="company.onboarded",
        title=f"{company.name} onboarded",
        target_entity_type="company",
        target_entity_id=company.id,
        metadata={"owner_user_id": str(user.id)},
    )
    db.commit()
    db.refresh(company)
    db.refresh(user)
    return build_auth_session(user, company)


@router.post("/login", response_model=AuthSessionRead)
def login(payload: LoginRequest, db: Session = Depends(db_session)) -> AuthSessionRead:
    email = normalize_email(str(payload.email))
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    company = db.get(Company, user.company_id)
    if company is None or not company.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company account is not active")

    user.last_login_at = datetime.now(timezone.utc)
    set_employee_presence(db, user, "online", "login")
    EventService.record_event(
        db,
        company_id=user.company_id,
        event_type="auth.login",
        title=f"{user.full_name} signed in",
        target_entity_type="user",
        target_entity_id=user.id,
    )
    db.commit()
    db.refresh(user)
    return build_auth_session(user, company)


@router.post("/logout", response_model=LogoutRead)
def logout(
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> LogoutRead:
    set_employee_presence(db, current_user, "offline", "logout")
    db.commit()
    return LogoutRead()


@router.post("/presence/online", response_model=EmployeeRead)
def mark_presence_online(
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Employee:
    employee = set_employee_presence(db, current_user, "online", "presence")
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee profile not found")
    db.commit()
    db.refresh(employee)
    return employee


@router.post("/presence/offline", response_model=EmployeeRead)
def mark_presence_offline(
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
) -> Employee:
    employee = set_employee_presence(db, current_user, "offline", "presence")
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee profile not found")
    db.commit()
    db.refresh(employee)
    return employee


@router.get("/me", response_model=AuthMeRead)
def me(
    current_user: User = Depends(get_current_user),
    current_company: Company = Depends(get_current_company),
) -> AuthMeRead:
    return AuthMeRead(user=current_user, company=current_company)
