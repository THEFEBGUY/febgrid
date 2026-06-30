from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AIProviderRequest:
    job_type: str
    input_entity_type: str | None
    input_entity_id: str | None
    input_payload: dict[str, Any]
    entity_context: dict[str, Any]
    messages: list[dict[str, str]]
    max_input_chars: int


@dataclass(frozen=True)
class AIProviderResult:
    output_payload: dict[str, Any]
    provider_key: str
    provider_mode: str
    model_name: str | None = None
    external_processing_used: bool = False
    latency_ms: int | None = None
    input_token_estimate: int | None = None
    output_token_estimate: int | None = None
    safety_status: str = "passed"
    metadata: dict[str, Any] = field(default_factory=dict)


class AIProviderError(Exception):
    def __init__(self, code: str, safe_message: str, metadata: dict[str, Any] | None = None) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message
        self.metadata = metadata or {}


class BaseAIProvider:
    provider_key = "base"
    provider_mode = "disabled"
    model_name: str | None = None
    external_processing_used = False

    def generate(self, request: AIProviderRequest) -> AIProviderResult:
        raise NotImplementedError
