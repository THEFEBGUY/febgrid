from pydantic import EmailStr, Field

from app.schemas.common import FebGridModel
from app.schemas.company import CompanyRead
from app.schemas.user import UserRead


class RegisterRequest(FebGridModel):
    full_name: str = Field(min_length=1, max_length=160)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    company_name: str = Field(min_length=1, max_length=160)
    company_slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    industry: str | None = Field(default=None, max_length=120)
    size: str | None = Field(default=None, max_length=80)
    timezone: str = Field(default="UTC", max_length=80)


class LoginRequest(FebGridModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AuthSessionRead(FebGridModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
    company: CompanyRead


class AuthMeRead(FebGridModel):
    user: UserRead
    company: CompanyRead


class LogoutRead(FebGridModel):
    status: str = "ok"
