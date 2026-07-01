import json
from typing import Any


def metadata_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def output_contract_for_job(job_type: str) -> dict[str, Any]:
    if job_type == "project_summary_safe":
        return {
            "summary": "short operational summary of the project",
            "project_health": "one of: healthy, watch, at_risk, blocked, unknown",
            "status_explanation": "plain-language explanation grounded only in provided data",
            "progress_overview": "brief progress note",
            "open_work_overview": "brief note about open work counts and top open items",
            "risks_or_blockers": ["up to 4 risks or blockers, only when evidence exists"],
            "suggested_next_steps": ["up to 4 practical next steps based only on provided fields"],
            "confidence": None,
        }
    return {
        "summary": "short operational summary of the work object",
        "current_status_explanation": "plain-language explanation grounded only in provided data",
        "key_points": ["up to 5 concise points"],
        "blockers_or_risks": ["up to 3 blockers or risks, only when evidence exists"],
        "suggested_next_steps": ["up to 3 practical next steps based only on provided fields"],
        "confidence": None,
    }


def build_summary_messages(
    *,
    job_type: str,
    entity_context: dict[str, Any],
    input_payload: dict[str, Any],
    max_input_chars: int,
) -> list[dict[str, str]]:
    user_payload = {
        "job_type": job_type,
        "entity_context": metadata_dict(entity_context),
        "input_payload": metadata_dict(input_payload),
        "output_contract": output_contract_for_job(job_type),
    }
    serialized = json.dumps(user_payload, default=str)[:max_input_chars]
    return [
        {
            "role": "system",
            "content": (
                "You are FebGrid's safety-constrained business operating system assistant. "
                "Summarize only the structured data provided by the server. Do not invent facts. "
                "If information is missing, mention uncertainty briefly. Do not provide legal, financial, "
                "medical, or compliance advice. Do not request, infer, or reveal secrets, passwords, tokens, "
                "API keys, invite links, local file paths, or credentials. This is operational assistance only. "
                "Return valid compact JSON matching the requested output contract."
            ),
        },
        {"role": "user", "content": serialized},
    ]
