from app.core.ai_config import AIProviderConfig
from app.services.ai_providers.base import AIProviderError, BaseAIProvider
from app.services.ai_providers.groq_provider import GroqAIProvider
from app.services.ai_providers.mock_provider import MockAIProvider


def build_ai_provider(mode: str, config: AIProviderConfig) -> BaseAIProvider:
    if mode == "mock":
        return MockAIProvider()
    if mode == "groq":
        return GroqAIProvider(config)
    if mode == "disabled":
        raise AIProviderError("provider_disabled", "AI provider mode is disabled.")
    if mode == "openai_future":
        raise AIProviderError("provider_not_implemented", "OpenAI provider is reserved for a future paid-model phase.")
    if mode == "custom_openai_compatible_future":
        raise AIProviderError("provider_not_implemented", "Custom OpenAI-compatible provider is reserved for a future phase.")
    raise AIProviderError("provider_disabled", "AI provider mode is not supported.")
