import json
import socket
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

from app.core.ai_config import AIProviderConfig
from app.services.ai_providers.base import AIProviderError, AIProviderRequest, AIProviderResult, BaseAIProvider


class GroqAIProvider(BaseAIProvider):
    provider_key = "groq"
    provider_mode = "groq"
    external_processing_used = True

    def __init__(self, config: AIProviderConfig) -> None:
        self.config = config
        self.model_name = config.groq_model

    def generate(self, request: AIProviderRequest) -> AIProviderResult:
        if not self.config.groq_api_key:
            raise AIProviderError("missing_api_key", "Groq API key is not configured.")

        body = {
            "model": self.config.groq_model,
            "messages": request.messages,
            "temperature": self.config.default_temperature,
            "max_tokens": self.config.default_max_tokens,
        }
        endpoint = f"{self.config.groq_base_url}/chat/completions"
        encoded_body = json.dumps(body).encode("utf-8")
        http_request = urllib.request.Request(
            endpoint,
            data=encoded_body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.config.groq_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

        started = time.perf_counter()
        try:
            with urllib.request.urlopen(http_request, timeout=self.config.groq_timeout_seconds) as response:
                raw_response = response.read().decode("utf-8")
        except TimeoutError as exc:
            raise AIProviderError("provider_timeout", "Groq request timed out.") from exc
        except socket.timeout as exc:
            raise AIProviderError("provider_timeout", "Groq request timed out.") from exc
        except urllib.error.HTTPError as exc:
            raise self._http_error(exc) from exc
        except urllib.error.URLError as exc:
            raise AIProviderError("provider_unavailable", "Groq provider is unavailable.") from exc
        except Exception as exc:
            raise AIProviderError("provider_unknown_error", "Groq provider failed safely.") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        try:
            parsed = json.loads(raw_response)
            content = parsed["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise AIProviderError("provider_bad_response", "Groq returned an unsupported response shape.") from exc

        output = self._parse_model_content(content)
        usage = parsed.get("usage") if isinstance(parsed, dict) else {}
        input_tokens = self._safe_int(usage.get("prompt_tokens")) if isinstance(usage, dict) else None
        output_tokens = self._safe_int(usage.get("completion_tokens")) if isinstance(usage, dict) else None
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
                "http_status": 200,
                "usage_available": bool(usage),
            },
        )

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        if isinstance(value, int):
            return value
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_model_content(content: str) -> dict[str, Any]:
        text = content.strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                output: dict[str, Any] = {}
                text_keys = [
                    "summary",
                    "executive_summary",
                    "current_status_explanation",
                    "document_type_guess",
                    "project_health",
                    "status_explanation",
                    "progress_overview",
                    "open_work_overview",
                    "work_overview",
                    "project_overview",
                    "people_overview",
                    "leave_overview",
                ]
                list_keys = [
                    "key_points",
                    "blockers_or_risks",
                    "risks_or_blockers",
                    "risks_or_concerns",
                    "suggested_next_steps",
                    "suggested_next_actions",
                    "operational_highlights",
                    "important_dates_or_numbers",
                    "attention_items",
                    "limitations",
                    "risks",
                    "next_actions",
                ]
                for key in text_keys:
                    if key in parsed and parsed.get(key) is not None:
                        output[key] = str(parsed.get(key)).strip()[:4000]
                for key in list_keys:
                    value = parsed.get(key)
                    if isinstance(value, list):
                        output[key] = [str(item).strip()[:800] for item in value[:8] if str(item).strip()]
                if "suggested_next_steps" not in output and isinstance(output.get("next_actions"), list):
                    output["suggested_next_steps"] = output["next_actions"]
                if "suggested_next_actions" not in output and isinstance(output.get("next_actions"), list):
                    output["suggested_next_actions"] = output["next_actions"]
                if "blockers_or_risks" not in output and isinstance(output.get("risks"), list):
                    output["blockers_or_risks"] = output["risks"]
                if "risks_or_blockers" not in output and isinstance(output.get("risks"), list):
                    output["risks_or_blockers"] = output["risks"]
                output["truncated"] = bool(parsed.get("truncated", False))
                unsupported_reason = parsed.get("unsupported_reason")
                output["unsupported_reason"] = str(unsupported_reason).strip()[:500] if unsupported_reason else None
                output["confidence"] = parsed.get("confidence")
                if "summary" not in output and "executive_summary" not in output:
                    output["summary"] = ""
                return output
        except json.JSONDecodeError:
            pass
        return {
            "summary": text[:4000],
            "executive_summary": text[:4000],
            "key_points": [],
            "blockers_or_risks": [],
            "risks_or_blockers": [],
            "risks_or_concerns": [],
            "suggested_next_steps": [],
            "suggested_next_actions": [],
            "operational_highlights": [],
            "important_dates_or_numbers": [],
            "attention_items": [],
            "limitations": ["Provider returned non-JSON text, so FebGrid wrapped the response safely."],
            "truncated": False,
            "unsupported_reason": None,
            "confidence": None,
        }

    @staticmethod
    def _http_error(exc: urllib.error.HTTPError) -> AIProviderError:
        status_code = exc.code
        if status_code == 429:
            return AIProviderError("provider_rate_limited", "Groq rate limit reached.", {"http_status": status_code})
        if status_code == 400:
            return AIProviderError("provider_bad_request", "Groq rejected the safe request.", {"http_status": status_code})
        if status_code in {401, 403}:
            return AIProviderError("provider_auth_failed", "Groq credentials are missing or invalid.", {"http_status": status_code})
        if status_code >= 500:
            return AIProviderError("provider_unavailable", "Groq provider is unavailable.", {"http_status": status_code})
        return AIProviderError("provider_unknown_error", "Groq provider failed safely.", {"http_status": status_code})
