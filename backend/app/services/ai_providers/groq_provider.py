import time
from datetime import UTC, datetime
from typing import Any

from app.core.ai_config import AIProviderConfig
from app.services.ai_output_parser import parse_ai_provider_output
from app.services.ai_providers.base import AIProviderError, AIProviderRequest, AIProviderResult, BaseAIProvider

try:
    from groq import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, Groq, RateLimitError
except ImportError:  # pragma: no cover - exercised only when dependencies are not installed.
    APIConnectionError = APIStatusError = APITimeoutError = AuthenticationError = RateLimitError = None  # type: ignore[assignment]
    Groq = None  # type: ignore[assignment]


class GroqAIProvider(BaseAIProvider):
    provider_key = "groq"
    provider_mode = "groq"
    external_processing_used = True

    def __init__(self, config: AIProviderConfig) -> None:
        self.config = config
        self.model_name = config.groq_model

    def generate(self, request: AIProviderRequest) -> AIProviderResult:
        if request.job_type == "audio_transcription_safe":
            raise AIProviderError("provider_unsupported_capability", "Current AI provider/model does not support audio transcription yet.")
        if request.job_type == "image_analysis_safe":
            raise AIProviderError("provider_unsupported_capability", "Current AI provider/model does not support image analysis yet.")
        if not self.config.groq_api_key:
            raise AIProviderError("missing_api_key", "Groq API key is not configured.")
        if Groq is None:
            raise AIProviderError("provider_unavailable", "Groq SDK dependency is not installed.")

        started = time.perf_counter()
        try:
            completion = self._client().chat.completions.create(
                model=self.config.groq_model,
                messages=request.messages,
                temperature=self.config.default_temperature,
                max_tokens=self.config.default_max_tokens,
                response_format={"type": "json_object"},
            )
        except APITimeoutError as exc:
            raise AIProviderError("provider_timeout", "Groq request timed out.") from exc
        except AuthenticationError as exc:
            raise AIProviderError("provider_auth_failed", "Groq credentials are missing or invalid.", self._status_metadata(exc)) from exc
        except RateLimitError as exc:
            raise AIProviderError("provider_rate_limited", "Groq rate limit reached.", self._status_metadata(exc)) from exc
        except APIConnectionError as exc:
            raise AIProviderError("provider_unavailable", "Groq provider is unavailable.") from exc
        except APIStatusError as exc:
            raise self._api_status_error(exc) from exc
        except Exception as exc:
            raise AIProviderError("provider_unknown_error", "Groq provider failed safely.") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        try:
            content = completion.choices[0].message.content or ""
        except (AttributeError, IndexError, TypeError) as exc:
            raise AIProviderError("provider_bad_response", "Groq returned an unsupported response shape.") from exc

        parsed_output = parse_ai_provider_output(content, request.job_type)
        output = parsed_output.output_payload
        usage = getattr(completion, "usage", None)
        input_tokens = self._safe_int(getattr(usage, "prompt_tokens", None))
        output_tokens = self._safe_int(getattr(usage, "completion_tokens", None))
        output.update(
            {
                "provider": self.provider_key,
                "provider_key": self.provider_key,
                "provider_mode": self.provider_mode,
                "model": self.config.groq_model,
                "model_name": self.config.groq_model,
                "generated_at": datetime.now(UTC).isoformat(),
                "generated": True,
                "mock": False,
                "is_mock": False,
                "job_type": request.job_type,
                "input_entity_type": request.input_entity_type,
                "input_entity_id": request.input_entity_id,
            }
        )
        return AIProviderResult(
            output_payload=output,
            provider_key=self.provider_key,
            provider_mode=self.provider_mode,
            model_name=self.config.groq_model,
            external_processing_used=True,
            latency_ms=latency_ms,
            input_token_estimate=input_tokens,
            output_token_estimate=output_tokens,
            safety_status="passed",
            metadata={
                "usage_available": bool(usage),
                "custom_base_url": bool(self.config.groq_base_url),
                "sdk_max_retries": self.config.groq_max_retries,
                **parsed_output.metadata,
            },
        )

    def _client(self) -> Groq:
        kwargs: dict[str, Any] = {
            "api_key": self.config.groq_api_key,
            "timeout": float(self.config.groq_timeout_seconds),
            "max_retries": self.config.groq_max_retries,
        }
        if self.config.groq_base_url:
            kwargs["base_url"] = self.config.groq_base_url
        return Groq(**kwargs)

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        if isinstance(value, int):
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _status_metadata(exc: Any) -> dict[str, Any]:
        status_code = getattr(exc, "status_code", None)
        return {"http_status": status_code} if status_code else {}

    @classmethod
    def _api_status_error(cls, exc: Any) -> AIProviderError:
        status_code = getattr(exc, "status_code", None)
        metadata = cls._status_metadata(exc)
        if status_code == 429:
            return AIProviderError("provider_rate_limited", "Groq rate limit reached.", metadata)
        if status_code == 400:
            return AIProviderError("provider_bad_request", "Groq rejected the safe request.", metadata)
        if status_code in {401, 403}:
            return AIProviderError("provider_auth_failed", "Groq credentials are missing or invalid.", metadata)
        if isinstance(status_code, int) and status_code >= 500:
            return AIProviderError("provider_unavailable", "Groq provider is unavailable.", metadata)
        return AIProviderError("provider_unknown_error", "Groq provider failed safely.", metadata)
