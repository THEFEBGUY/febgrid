import inspect
import unittest
from datetime import datetime, timezone

from app.api.routes import dashboard
from app.schemas.dashboard import DashboardIntelligenceSummary


class DashboardIntelligenceSummaryTests(unittest.TestCase):
    def test_intelligence_summary_schema_preserves_layer2_counters(self) -> None:
        generated_at = datetime.now(timezone.utc)

        summary = DashboardIntelligenceSummary(
            latest_work_dna_scope="company",
            latest_work_dna_generated_at=generated_at,
            latest_work_dna_bottlenecks=2,
            latest_work_dna_recurring_patterns=3,
            latest_work_dna_template_candidates=1,
            employee_twins_recent_count=4,
            employee_twins_missing_recent_count=1,
            ai_queued_jobs=5,
            ai_running_jobs=1,
            ai_failed_jobs=2,
            ai_cancelled_jobs=0,
        )

        self.assertEqual(summary.latest_work_dna_scope, "company")
        self.assertEqual(summary.employee_twins_missing_recent_count, 1)
        self.assertEqual(summary.ai_failed_jobs, 2)
        self.assertEqual(summary.latest_work_dna_generated_at, generated_at)

    def test_dashboard_intelligence_summary_is_owner_admin_scoped(self) -> None:
        source = inspect.getsource(dashboard.get_dashboard_summary)

        self.assertIn("current_user.role in OWNER_ADMIN_ROLES", source)
        self.assertIn("EmployeeDigitalTwinSnapshot.company_id == company_id", source)
        self.assertIn("WorkDNASnapshot.company_id == company_id", source)
        self.assertIn("AIJob.company_id == company_id", source)


if __name__ == "__main__":
    unittest.main()
