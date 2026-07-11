import json
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.performance import (
    begin_request_performance,
    end_request_performance,
    log_request_performance,
    record_db_duration,
    record_external_duration,
)
from app.main import app


class PerformanceFoundationTests(unittest.TestCase):
    def test_health_response_exposes_safe_correlation_and_server_timing(self) -> None:
        with TestClient(app) as client:
            response = client.get("/api/v1/health", headers={"X-Request-ID": "test-request-123"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], "test-request-123")
        self.assertIn("app;dur=", response.headers["Server-Timing"])
        self.assertIn("db;dur=", response.headers["Server-Timing"])

    def test_request_metrics_aggregate_database_and_allowlisted_external_timings(self) -> None:
        metrics, token = begin_request_performance()
        try:
            record_db_duration(4.25)
            record_db_duration(2.75)
            record_external_duration("groq", 11.5)
            record_external_duration("unknown-service", 3.0)
        finally:
            end_request_performance(token)

        self.assertEqual(metrics.query_count, 2)
        self.assertEqual(metrics.db_duration_ms, 7.0)
        self.assertEqual(metrics.external_durations_ms, {"groq": 11.5, "external": 3.0})

    def test_structured_log_contains_no_url_query_or_payload(self) -> None:
        metrics, token = begin_request_performance()
        try:
            with patch("app.core.performance.performance_logger.info") as log:
                log_request_performance(
                    request_id="safe-request-id",
                    method="POST",
                    route="/api/v1/invitations",
                    status_code=201,
                    duration_ms=18.2,
                    metrics=metrics,
                )
        finally:
            end_request_performance(token)

        payload = json.loads(log.call_args.args[0])
        self.assertEqual(payload["route"], "/api/v1/invitations")
        self.assertNotIn("query", payload)
        self.assertNotIn("body", payload)
        self.assertNotIn("token", payload)
        self.assertNotIn("email", payload)


if __name__ == "__main__":
    unittest.main()
