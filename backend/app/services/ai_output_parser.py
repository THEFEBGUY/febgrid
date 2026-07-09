import json
from dataclasses import dataclass
from typing import Any

from app.services.ai_prompt_templates import output_contract_for_job


TEXT_FALLBACK_LIMIT = 4000
TEXT_FIELD_LIMIT = 4000
LIST_ITEM_LIMIT = 800
MAX_LIST_ITEMS = 12
MAX_OBJECT_KEYS = 40
MAX_DEPTH = 5


@dataclass(frozen=True)
class ParsedAIOutput:
    output_payload: dict[str, Any]
    metadata: dict[str, Any]


def parse_ai_provider_output(content: str, job_type: str) -> ParsedAIOutput:
    normalized = normalize_model_text(content)
    parsed = first_json_object(normalized)
    if parsed is None:
        fallback = fallback_output_payload(job_type, normalized)
        return ParsedAIOutput(
            output_payload=fallback,
            metadata={
                "output_parse_status": "fallback_text",
                "output_parse_error": True,
                "output_parse_error_code": "invalid_json",
                "markdown_fence_removed": content.strip() != normalized,
            },
        )

    output = normalize_structured_output(parsed, job_type)
    return ParsedAIOutput(
        output_payload=output,
        metadata={
            "output_parse_status": "parsed_json",
            "output_parse_error": False,
            "markdown_fence_removed": content.strip() != normalized,
            "structured_json_extracted": normalized.strip() != json.dumps(parsed, default=str, separators=(",", ":")),
        },
    )


def normalize_model_text(content: str) -> str:
    text = (content or "").strip()
    text = strip_outer_code_fence(text)
    return strip_fence_marker_lines(text).strip()


def strip_outer_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if len(lines) >= 2 and lines[0].strip().lower() in {"```", "```json"} and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped


def strip_fence_marker_lines(text: str) -> str:
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        marker = line.strip().lower()
        if marker in {"```", "```json"}:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def first_json_object(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    stripped = text.strip()
    for index, char in enumerate(stripped):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(stripped[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


def normalize_structured_output(parsed: dict[str, Any], job_type: str) -> dict[str, Any]:
    output = default_output_payload(job_type)
    for key, value in parsed.items():
        safe_key = str(key).strip()[:100]
        if not safe_key:
            continue
        output[safe_key] = sanitize_json_value(value)

    if is_blank_output_value(output.get("suggested_next_steps")):
        if isinstance(output.get("next_actions"), list):
            output["suggested_next_steps"] = output["next_actions"]
    if is_blank_output_value(output.get("suggested_next_actions")):
        if isinstance(output.get("next_actions"), list):
            output["suggested_next_actions"] = output["next_actions"]
    if is_blank_output_value(output.get("blockers_or_risks")):
        if isinstance(output.get("risks"), list):
            output["blockers_or_risks"] = output["risks"]
    if is_blank_output_value(output.get("risks_or_blockers")):
        if isinstance(output.get("risks"), list):
            output["risks_or_blockers"] = output["risks"]

    output["truncated"] = bool(output.get("truncated", False))
    output.setdefault("unsupported_reason", None)
    output.setdefault("confidence", None)
    output["parsing_error"] = False
    return output


def is_blank_output_value(value: Any) -> bool:
    return value is None or value == "" or value == []


def default_output_payload(job_type: str) -> dict[str, Any]:
    contract = output_contract_for_job(job_type)
    return {key: default_for_contract_value(value) for key, value in contract.items()}


def default_for_contract_value(value: Any) -> Any:
    if isinstance(value, list):
        return []
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    return ""


def sanitize_json_value(value: Any, *, depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        return safe_string(value, max_chars=LIST_ITEM_LIMIT)
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value
    if isinstance(value, str):
        return safe_string(value)
    if isinstance(value, list):
        return [sanitize_json_value(item, depth=depth + 1) for item in value[:MAX_LIST_ITEMS]]
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for index, (key, nested) in enumerate(value.items()):
            if index >= MAX_OBJECT_KEYS:
                break
            safe_key = str(key).strip()[:100]
            if safe_key:
                cleaned[safe_key] = sanitize_json_value(nested, depth=depth + 1)
        return cleaned
    return safe_string(value)


def safe_string(value: Any, *, max_chars: int = TEXT_FIELD_LIMIT) -> str:
    return str(value).strip()[:max_chars]


def fallback_output_payload(job_type: str, text: str) -> dict[str, Any]:
    output = default_output_payload(job_type)
    summary = fallback_summary_text(text)
    primary_key = primary_text_key(job_type)
    output[primary_key] = summary
    if primary_key != "summary" and "summary" in output:
        output["summary"] = summary
    output["parsing_error"] = True
    output["parsing_error_code"] = "invalid_json"
    output["parsing_error_message"] = "Provider returned malformed structured output, so FebGrid used a safe fallback."
    output.setdefault("limitations", [])
    if isinstance(output["limitations"], list):
        output["limitations"] = [
            *output["limitations"],
            "Provider returned malformed structured output; structured fields may be incomplete.",
        ][:MAX_LIST_ITEMS]
    return output


def fallback_summary_text(text: str) -> str:
    cleaned = normalize_model_text(text)
    if looks_like_json(cleaned):
        return "The AI provider returned malformed structured output, so FebGrid could not extract a clean summary. Please regenerate the summary."
    return cleaned[:TEXT_FALLBACK_LIMIT] or "The AI provider returned an empty response."


def looks_like_json(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("{") or stripped.startswith("[") or '"summary"' in stripped or '"executive_summary"' in stripped


def primary_text_key(job_type: str) -> str:
    if job_type == "company_brief_safe":
        return "executive_summary"
    if job_type == "document_analysis_safe":
        return "document_overview"
    if job_type == "image_analysis_safe":
        return "image_overview"
    if job_type == "audio_transcription_safe":
        return "transcript_summary"
    return "summary"
