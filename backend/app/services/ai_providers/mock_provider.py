from datetime import UTC, datetime

from app.services.ai_providers.base import AIProviderRequest, AIProviderResult, BaseAIProvider


class MockAIProvider(BaseAIProvider):
    provider_key = "mock"
    provider_mode = "mock"
    model_name = "mock-deterministic"
    external_processing_used = False

    def generate(self, request: AIProviderRequest) -> AIProviderResult:
        entity = request.input_entity_type or "company"
        output = self._summary_payload(request, entity)
        output.update(
            {
                "confidence": None,
                "provider": self.provider_key,
                "provider_key": self.provider_key,
                "provider_mode": self.provider_mode,
                "model": self.model_name,
                "model_name": self.model_name,
                "generated_at": datetime.now(UTC).isoformat(),
                "generated": False,
                "mock": True,
                "is_mock": True,
                "job_type": request.job_type,
                "input_entity_type": request.input_entity_type,
                "input_entity_id": request.input_entity_id,
                "input_payload_keys": sorted(request.input_payload.keys()),
            }
        )
        return AIProviderResult(
            output_payload=output,
            provider_key=self.provider_key,
            provider_mode=self.provider_mode,
            model_name=self.model_name,
            external_processing_used=False,
            safety_status="mock",
            metadata={"mock": True},
        )

    def _summary_payload(self, request: AIProviderRequest, entity: str) -> dict[str, object]:
        if request.job_type == "company_brief_safe":
            return {
                "executive_summary": "Mock AI company brief. Real provider not connected.",
                "operational_highlights": ["Mock mode reviewed aggregated company signals without making an external AI call."],
                "work_overview": "Work overview is mock-only until Groq is configured and explicitly enabled.",
                "project_overview": "Project overview is mock-only and uses sanitized company aggregates.",
                "people_overview": "People overview is mock-only and uses counts, not private employee profile data.",
                "leave_overview": "Leave overview is mock-only and uses safe leave counts.",
                "risks_or_blockers": ["Mock output only; no real executive risk analysis was generated."],
                "suggested_next_actions": ["Enable Groq with explicit external processing consent to generate a real company brief."],
                "attention_items": ["Mock company brief placeholder for owner/admin validation."],
            }
        if request.job_type == "project_summary_safe":
            return {
                "summary": "Mock AI project summary. Real provider not connected.",
                "project_health": "unknown",
                "status_explanation": "Mock mode reviewed the safe project fields without making an external AI call.",
                "progress_overview": "Progress review is mock-only until a real provider is enabled.",
                "open_work_overview": "Open work review is mock-only and based on stored project context.",
                "risks_or_blockers": ["Mock output only; no real risk assessment was generated."],
                "suggested_next_steps": ["Enable Groq with explicit external processing consent to generate a real project summary."],
            }
        if request.job_type == "work_object_summary_safe":
            return {
                "summary": "Mock AI work summary. Real provider not connected.",
                "current_status_explanation": "Mock mode reviewed the safe work object fields without making an external AI call.",
                "key_points": ["This is deterministic mock output for local development."],
                "blockers_or_risks": ["Mock output only; no real blocker analysis was generated."],
                "suggested_next_steps": ["Enable Groq with explicit external processing consent to generate a real work summary."],
            }
        if request.job_type == "file_summary_safe":
            return {
                "summary": "Mock AI file summary. Real provider not connected.",
                "document_type_guess": "mock text document",
                "key_points": ["Mock mode verified that the file belongs to this company and is a supported safe text file."],
                "important_dates_or_numbers": [],
                "risks_or_concerns": ["Mock output only; no real document analysis was generated."],
                "suggested_next_steps": ["Enable Groq with explicit external processing consent to generate a real file summary."],
                "limitations": ["Mock provider does not read, parse, or summarize file content externally."],
                "truncated": bool(request.entity_context.get("truncated", False)),
                "unsupported_reason": request.entity_context.get("unsupported_reason"),
            }
        if request.job_type == "document_analysis_safe":
            return {
                "document_overview": "Mock AI document analysis. Real provider not connected.",
                "document_type_guess": "mock text document",
                "key_points": ["Mock mode verified that the document belongs to this company and passed text-only safety checks."],
                "decisions_or_commitments": [],
                "action_items": ["Mock output only; no real action item extraction was generated."],
                "important_dates": [],
                "important_numbers": [],
                "risks_or_concerns": ["Mock output only; no real document risk analysis was generated."],
                "people_or_teams_mentioned": [],
                "related_work_suggestions": ["Enable Groq with explicit external processing consent to generate real document analysis suggestions."],
                "suggested_next_steps": ["Review this mock analysis and use supported text documents for real provider validation later."],
                "limitations": ["Mock provider does not send document text externally."],
                "truncated": bool(request.entity_context.get("truncated", False)),
                "unsupported_reason": request.entity_context.get("unsupported_reason"),
            }
        if request.job_type == "image_analysis_safe":
            width = request.entity_context.get("image_width")
            height = request.entity_context.get("image_height")
            dimensions = f"{width}x{height}" if width and height else "unknown dimensions"
            return {
                "image_overview": f"Mock AI image analysis. Real vision provider not connected. Image metadata passed safety checks ({dimensions}).",
                "visible_objects_or_elements": ["Mock output only; no real image understanding was generated."],
                "possible_context": ["This is a deterministic mock placeholder for validating FebGrid image-analysis flow."],
                "operational_relevance": "Mock mode verified company ownership, file type, file size, dimensions, and permissions without external processing.",
                "risks_or_concerns": ["Mock output only; no real operational visual risk assessment was generated."],
                "suggested_next_steps": ["Enable a future vision-capable provider with explicit external processing consent to generate real image analysis."],
                "limitations": [
                    "Mock provider does not inspect image pixels.",
                    "No face recognition, identity recognition, OCR, biometric, or sensitive-trait inference is performed.",
                ],
                "unsupported_reason": request.entity_context.get("unsupported_reason"),
            }
        if request.job_type == "audio_transcription_safe":
            duration = request.entity_context.get("duration_seconds")
            return {
                "transcript": "Mock transcript for this uploaded audio file. Real audio transcription provider not connected.",
                "transcript_summary": "Mock AI audio transcription. Real transcription provider not connected.",
                "key_points": ["Mock mode verified company ownership, file type, file size, and permissions without external processing."],
                "action_items": ["Enable a future audio-capable provider with explicit external processing consent to generate real transcription notes."],
                "decisions_or_commitments": [],
                "important_dates_or_numbers": [],
                "risks_or_concerns": ["Mock output only; no real audio understanding was generated."],
                "suggested_next_steps": ["Use supported audio files and an audio-capable provider when FebGrid enables real transcription."],
                "limitations": [
                    "Mock provider does not inspect or send audio bytes.",
                    "No speaker identity, biometric, emotion, or sensitive-trait inference is performed.",
                ],
                "language_detected": None,
                "duration_seconds": duration,
                "unsupported_reason": request.entity_context.get("unsupported_reason"),
            }
        return {
            "summary": f"Mock AI summary for {entity}. Real provider not connected.",
            "key_points": ["Mock placeholder output only."],
            "blockers_or_risks": [],
            "suggested_next_steps": [],
        }
