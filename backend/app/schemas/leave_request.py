from datetime import date
from uuid import UUID

from pydantic import Field, model_validator

from app.schemas.common import FebGridModel, Timestamped


class LeaveRequestBase(FebGridModel):
    company_id: UUID
    employee_id: UUID
    approver_employee_id: UUID | None = None
    start_date: date
    end_date: date
    leave_type: str = Field(min_length=1, max_length=80)
    reason: str | None = None
    status: str = Field(default="pending", max_length=40)
    decision_note: str | None = None

    @model_validator(mode="after")
    def validate_date_range(self) -> "LeaveRequestBase":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class LeaveRequestCreate(LeaveRequestBase):
    status: str = "pending"


class LeaveRequestUpdate(FebGridModel):
    approver_employee_id: UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    leave_type: str | None = Field(default=None, min_length=1, max_length=80)
    reason: str | None = None
    status: str | None = Field(default=None, max_length=40)
    decision_note: str | None = None


class LeaveDecision(FebGridModel):
    company_id: UUID
    approver_employee_id: UUID
    decision_note: str | None = None


class LeaveRequestRead(LeaveRequestBase, Timestamped):
    id: UUID
