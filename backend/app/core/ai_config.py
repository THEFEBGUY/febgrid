from dataclasses import dataclass

from app.core.config import get_settings

SUPPORTED_AI_PROVIDER_MODES = {
    "disabled",
    "mock",
    "groq",
    "openai_future",
    "custom_openai_compatible_future",
}
REAL_AI_PROVIDER_MODES = {"groq", "openai_future", "custom_openai_compatible_future"}
OFFICIAL_GROQ_OPENAI_BASE_URL = "https://api.groq.com/openai/v1"


@dataclass(frozen=True)
class AIProviderConfig:
    provider_mode: str
    external_processing_enabled: bool
    groq_api_key: str | None
    groq_model: str
    groq_base_url: str | None
    groq_timeout_seconds: int
    groq_max_retries: int
    groq_max_input_chars: int
    default_temperature: float
    default_max_tokens: int

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key)


def normalize_provider_mode(value: str | None) -> str:
    normalized = (value or "mock").strip().lower()
    if normalized in SUPPORTED_AI_PROVIDER_MODES:
        return normalized
    return "mock"


def get_ai_provider_config() -> AIProviderConfig:
    settings = get_settings()
    provider_mode = normalize_provider_mode(settings.ai_provider_mode or settings.ai_provider)
    groq_secret = settings.groq_api_key.get_secret_value().strip() if settings.groq_api_key else ""
    groq_base_url = settings.groq_base_url.strip().rstrip("/")
    if not groq_base_url or groq_base_url == OFFICIAL_GROQ_OPENAI_BASE_URL:
        groq_base_url = ""
    return AIProviderConfig(
        provider_mode=provider_mode,
        external_processing_enabled=bool(settings.ai_external_processing_enabled),
        groq_api_key=groq_secret or None,
        groq_model=settings.groq_model.strip() or "openai/gpt-oss-120b",
        groq_base_url=groq_base_url or None,
        groq_timeout_seconds=max(1, min(int(settings.groq_timeout_seconds), 120)),
        groq_max_retries=max(0, min(int(settings.groq_max_retries), 5)),
        groq_max_input_chars=max(1_000, min(int(settings.groq_max_input_chars), 50_000)),
        default_temperature=max(0.0, min(float(settings.ai_default_temperature), 2.0)),
        default_max_tokens=max(64, min(int(settings.ai_default_max_tokens), 8_000)),
    )
