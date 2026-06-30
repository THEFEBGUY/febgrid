from app.services.ai_providers.base import AIProviderRequest, AIProviderResult, BaseAIProvider


class MockAIProvider(BaseAIProvider):
    provider_key = "mock"
    provider_mode = "mock"
    model_name = "mock-deterministic"
    external_processing_used = False

    def generate(self, request: AIProviderRequest) -> AIProviderResult:
        entity = request.input_entity_type or "company"
        output = {
            "summary": f"Mock AI summary for {entity}. Real provider not connected.",
            "confidence": None,
            "provider": self.provider_key,
            "provider_mode": self.provider_mode,
            "model": self.model_name,
            "generated": False,
            "mock": True,
            "job_type": request.job_type,
            "input_entity_type": request.input_entity_type,
            "input_entity_id": request.input_entity_id,
            "input_payload_keys": sorted(request.input_payload.keys()),
        }
        return AIProviderResult(
            output_payload=output,
            provider_key=self.provider_key,
            provider_mode=self.provider_mode,
            model_name=self.model_name,
            external_processing_used=False,
            safety_status="mock",
            metadata={"mock": True},
        )
