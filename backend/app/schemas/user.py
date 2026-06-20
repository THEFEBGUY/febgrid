from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.common import FebGridModel, Timestamped


class UserRead(Timestamped):
    id: UUID
    company_id: UUID
    full_name: str
    email: EmailStr
    role: str
    auth_provider: str
    is_active: bool
    last_login_at: datetime | None


class UserCreate(FebGridModel):
    company_id: UUID
    full_name: str = Field(min_length=1, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="employee", max_length=40)
