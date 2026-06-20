from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.company import Company
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def db_session() -> Generator[Session, None, None]:
    yield from get_db()


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(db_session),
) -> User | None:
    if credentials is None:
        return None

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        parsed_user_id = UUID(str(user_id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = db.get(User, parsed_user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user(current_user: User | None = Depends(get_optional_current_user)) -> User:
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def get_current_company(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session),
) -> Company:
    company = db.scalar(select(Company).where(Company.id == current_user.company_id, Company.is_active.is_(True)))
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company
