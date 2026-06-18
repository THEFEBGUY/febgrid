from typing import Any


class AIService:
    """Phase 1 mock AI boundary.

    Production providers must stay behind this service so routes, jobs, and
    database models do not learn about provider-specific credentials or SDKs.
    """

    provider = "mock"

    def run_job(self, job_type: str, input_payload: dict[str, Any]) -> dict[str, Any]:
        if job_type == "work_object_summary":
            title = input_payload.get("title", "work object")
            return {
                "summary": f"Mock summary for {title}.",
                "risk_level": "unknown",
                "provider": self.provider,
            }

        if job_type == "executive_brief":
            return {
                "brief": "Mock executive brief. Real operational intelligence is deferred beyond Phase 1.",
                "provider": self.provider,
            }

        if job_type == "file_analysis":
            file_name = input_payload.get("file_name", "file")
            return {
                "analysis": f"Mock analysis queued for {file_name}.",
                "provider": self.provider,
            }

        return {
            "message": "Mock AI job completed.",
            "job_type": job_type,
            "provider": self.provider,
        }


ai_service = AIService()
