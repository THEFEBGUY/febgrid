import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from docx import Document
from fastapi import HTTPException, UploadFile

from app.services.ai_service import AIProviderError, extract_document_text
from app.services.file_service import FileService
from app.services.storage_service import SupabaseStorageService


class SupabaseStoragePipelineTests(unittest.TestCase):
    def test_upload_uses_private_storage_endpoint_and_keeps_path_metadata(self) -> None:
        response = SimpleNamespace(status_code=200)
        with patch.object(SupabaseStorageService, "_configuration", return_value=("https://example.supabase.co", "secret", "work-files", 5.0)):
            with patch("app.services.storage_service.httpx.post", return_value=response) as post:
                result = SupabaseStorageService.upload(
                    storage_path="companies/company-id/work-objects/work-id/example.txt",
                    content=b"safe content",
                    content_type="text/plain",
                )
        self.assertEqual(result.path, "companies/company-id/work-objects/work-id/example.txt")
        self.assertEqual(result.size, 12)
        self.assertIn("/storage/v1/object/work-files/companies/company-id", post.call_args.args[0])

    def test_storage_path_rejects_traversal(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            SupabaseStorageService._safe_path("companies/../secret.txt")
        self.assertEqual(raised.exception.status_code, 404)

    def test_attachment_path_must_stay_inside_its_company_namespace(self) -> None:
        company_id = uuid4()
        with self.assertRaises(HTTPException) as raised:
            FileService.ensure_company_storage_path(
                company_id=company_id,
                storage_path=f"companies/{uuid4()}/work-objects/{uuid4()}/other-company.txt",
            )
        self.assertEqual(raised.exception.status_code, 404)

    def test_private_download_returns_storage_bytes(self) -> None:
        response = SimpleNamespace(status_code=200, content=b"private document")
        with patch.object(SupabaseStorageService, "_configuration", return_value=("https://example.supabase.co", "secret", "work-files", 5.0)):
            with patch("app.services.storage_service.httpx.get", return_value=response) as get:
                content = SupabaseStorageService.download(storage_path="companies/company-id/projects/project-id/notes.txt")
        self.assertEqual(content, b"private document")
        self.assertIn("/storage/v1/object/work-files/companies/company-id", get.call_args.args[0])

    def test_file_service_upload_never_creates_a_local_file(self) -> None:
        upload = UploadFile(filename="notes.txt", file=io.BytesIO(b"private project notes"), headers={"content-type": "text/plain"})
        with patch.object(SupabaseStorageService, "upload") as store:
            stored = FileService.save_upload(
                file=upload,
                company_id=uuid4(),
                linked_entity_type="work_object",
                linked_entity_id=uuid4(),
            )
        store.assert_called_once()
        self.assertEqual(stored.storage_provider, "supabase")
        self.assertTrue(stored.storage_path.startswith("companies/"))
        self.assertNotIn("storage/uploads", stored.storage_path)

    def test_supported_document_text_extraction(self) -> None:
        text, mode = extract_document_text(b"# Plan\nShip the storage migration.", ".md")
        self.assertEqual(mode, "utf8_text")
        self.assertIn("storage migration", text)

        document = Document()
        document.add_paragraph("Project attachment text")
        payload = io.BytesIO()
        document.save(payload)
        text, mode = extract_document_text(payload.getvalue(), ".docx")
        self.assertEqual(mode, "docx_text")
        self.assertIn("Project attachment text", text)

    def test_unreadable_pdf_returns_a_clear_extraction_error(self) -> None:
        with self.assertRaises(AIProviderError) as raised:
            extract_document_text(b"not a PDF", ".pdf")
        self.assertIn("Text could not be extracted", str(raised.exception))
