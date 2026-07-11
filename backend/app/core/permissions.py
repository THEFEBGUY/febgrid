from collections.abc import Iterable
from uuid import UUID

from fastapi import HTTPException, status

from app.models.user import User

ROLE_COMPANY_OWNER = "company_owner"
ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
ROLE_EMPLOYEE = "employee"

OWNER_ADMIN_ROLES = {ROLE_COMPANY_OWNER, ROLE_ADMIN}
MANAGER_ROLES = {ROLE_COMPANY_OWNER, ROLE_ADMIN, ROLE_MANAGER}
ALL_ROLES = {ROLE_COMPANY_OWNER, ROLE_ADMIN, ROLE_MANAGER, ROLE_EMPLOYEE}

# Invite capability is intentionally centralized. The current role model grants
# it to owner/admin only; future HR or manager capabilities belong here after
# they are represented by the existing authorization model.
INVITE_CAPABLE_ROLES = OWNER_ADMIN_ROLES


def ensure_valid_role(role: str) -> str:
    if role not in ALL_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid user role")
    return role


def ensure_company_access(user: User | None, company_id: UUID) -> None:
    if user is None:
        return
    if user.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company resource not found")


def ensure_role(user: User | None, allowed_roles: Iterable[str]) -> None:
    if user is None:
        return
    if user.role not in set(allowed_roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission for this action")


def ensure_invite_capability(user: User | None) -> None:
    ensure_role(user, INVITE_CAPABLE_ROLES)
