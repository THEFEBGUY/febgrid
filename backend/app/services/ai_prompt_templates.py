import json
from typing import Any


def metadata_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def output_contract_for_job(job_type: str) -> dict[str, Any]:
    if job_type == "company_brief_safe":
        return {
            "executive_summary": "concise owner/admin operational brief grounded only in provided aggregated company data",
            "operational_highlights": ["up to 5 recent highlights or positive signals with evidence"],
            "work_overview": "brief summary of work status, priority, overdue, and completed work signals",
            "project_overview": "brief summary of project health, priority, risk, and progress signals",
            "people_overview": "brief summary of employee availability and staffing signals using counts only",
            "leave_overview": "brief summary of leave attention and upcoming approved leave signals",
            "risks_or_blockers": ["up to 5 risks or blockers, only when evidence exists"],
            "suggested_next_actions": ["up to 5 practical owner/admin next actions based only on provided fields"],
            "attention_items": ["up to 5 items needing attention now"],
            "confidence": None,
        }
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
    if job_type == "file_summary_safe":
        return {
            "summary": "short operational summary of the supported text document",
            "document_type_guess": "plain-language guess from filename, content type, and text, or unknown",
            "key_points": ["up to 6 concise points grounded only in the provided text"],
            "important_dates_or_numbers": ["dates, amounts, IDs, or counts that appear important, only if present"],
            "risks_or_concerns": ["up to 4 concerns, inconsistencies, or operational risks, only when evidence exists"],
            "suggested_next_steps": ["up to 4 practical next steps based only on provided fields"],
            "limitations": ["mention unsupported sections, truncation, uncertainty, or missing context"],
            "truncated": False,
            "unsupported_reason": None,
            "confidence": None,
        }
    if job_type == "document_analysis_safe":
        return {
            "document_overview": "short operational overview of the supported text document",
            "document_type_guess": "plain-language guess from filename, content type, and text, or unknown",
            "key_points": ["up to 6 concise points grounded only in the provided text"],
            "decisions_or_commitments": ["decisions, approvals, promises, or commitments only if explicitly present"],
            "action_items": ["action items with owner/date only if explicitly present"],
            "important_dates": ["dates or deadlines only if explicitly present"],
            "important_numbers": ["amounts, counts, IDs, or metrics only if explicitly present"],
            "risks_or_concerns": ["up to 5 concerns, inconsistencies, or operational risks, only when evidence exists"],
            "people_or_teams_mentioned": ["people or team names only if explicitly mentioned in the provided text"],
            "related_work_suggestions": ["non-automatic work suggestions based only on the document, phrased as suggestions"],
            "suggested_next_steps": ["up to 5 practical next steps based only on provided fields"],
            "limitations": ["mention unsupported sections, truncation, uncertainty, or missing context"],
            "truncated": False,
            "unsupported_reason": None,
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
                "For company briefs, answer what changed recently, what needs attention, what is going well, "
                "what is blocked or risky, and what owner/admin should do next. Return valid compact JSON "
                "matching the requested output contract. For file summaries, summarize only the provided text, "
                "mention when content was truncated, and avoid restating any secret-like values. For document "
                "analysis, extract operational insights only from the provided text, keep related work ideas as "
                "suggestions, and do not create tasks, projects, memories, or actions."
            ),
        },
        {"role": "user", "content": serialized},
    ]
