from uuid import UUID

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text
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
    work_object_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("work_objects.id", ondelete="CASCADE"),
    )
    project_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
    )
    uploaded_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    uploaded_by_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
    )
    linked_entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    linked_entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column("file_type", String(120))
    file_size: Mapped[int | None] = mapped_column(BigInteger)
    storage_provider: Mapped[str] = mapped_column(String(40), default="local", nullable=False)
    storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    public_url: Mapped[str | None] = mapped_column("storage_url", Text)
    description: Mapped[str | None] = mapped_column(Text)
    ai_processing_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    metadata_json = json_dict(name="metadata")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    company = relationship("Company")
    work_object = relationship("WorkObject")
    project = relationship("Project")
    uploaded_by_user = relationship("User")
    uploader = relationship("Employee")

    @property
    def file_type(self) -> str | None:
        return self.content_type

    @file_type.setter
    def file_type(self, value: str | None) -> None:
        self.content_type = value

    @property
    def storage_url(self) -> str | None:
        return self.public_url

    @storage_url.setter
    def storage_url(self, value: str | None) -> None:
        self.public_url = value

    __table_args__ = (
        Index("idx_attachments_company_id", "company_id"),
        Index("idx_attachments_company_active", "company_id", "is_active"),
        Index("idx_attachments_work_object_id", "work_object_id"),
        Index("idx_attachments_project_id", "project_id"),
        Index("idx_attachments_uploaded_by_user_id", "uploaded_by_user_id"),
        Index("idx_attachments_linked_entity", "linked_entity_type", "linked_entity_id"),
    )
