from uuid import UUID

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.common import TimestampMixin, json_dict, uuid_pk


class Attachment(TimestampMixin, Base):
    __tablename__ = "attachments"

    id: Mapped[UUID] = uuid_pk()
    company_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    uploaded_by_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
    )
    linked_entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    linked_entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str | None] = mapped_column(String(120))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    storage_url: Mapped[str] = mapped_column(Text, nullable=False)
    ai_processing_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    metadata_json = json_dict(name="metadata")

    uploader = relationship("Employee")

    __table_args__ = (
        Index("idx_attachments_company_id", "company_id"),
        Index("idx_attachments_linked_entity", "linked_entity_type", "linked_entity_id"),
    )
