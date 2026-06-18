from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, json_dict, uuid_pk


class AIJob(TimestampMixin, Base):
    __tablename__ = "ai_jobs"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    requested_by_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
    )
    job_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="queued", nullable=False)
    input_payload = json_dict()
    output_payload = json_dict()
    error_message: Mapped[str | None] = mapped_column(Text)
    related_entity_type: Mapped[str | None] = mapped_column(String(80))
    related_entity_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))

    requester = relationship("Employee")

    __table_args__ = (
        Index("idx_ai_jobs_company_status", "company_id", "status"),
        Index("idx_ai_jobs_related_entity", "related_entity_type", "related_entity_id"),
    )
