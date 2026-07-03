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
        return {
            "summary": f"Mock AI summary for {entity}. Real provider not connected.",
            "key_points": ["Mock placeholder output only."],
            "blockers_or_risks": [],
            "suggested_next_steps": [],
        }
