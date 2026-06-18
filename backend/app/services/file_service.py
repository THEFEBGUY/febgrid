from app.models.attachment import Attachment
from app.schemas.attachment import AttachmentCreate


class FileService:
    @staticmethod
    def build_attachment(payload: AttachmentCreate) -> Attachment:
        return Attachment(
            company_id=payload.company_id,
            uploaded_by_employee_id=payload.uploaded_by_employee_id,
            linked_entity_type=payload.linked_entity_type,
            linked_entity_id=payload.linked_entity_id,
            file_name=payload.file_name,
            file_type=payload.file_type,
            file_size=payload.file_size,
            storage_url=payload.storage_url,
            ai_processing_status=payload.ai_processing_status,
            metadata_json=payload.metadata,
        )
