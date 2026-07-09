import unittest
from types import SimpleNamespace
from uuid import uuid4

from app.services.work_dna_service import WorkDNAService


class WorkDNAServiceTests(unittest.TestCase):
    def test_distribution_labels_handle_linked_and_unlinked_scopes(self) -> None:
        project_id = uuid4()
        department_id = uuid4()
        team_id = uuid4()

        work_items = [
            SimpleNamespace(
                object_type="task",
                status="assigned",
                priority="high",
                project_id=project_id,
                department_id=department_id,
                team_id=team_id,
                tags=["bug", "fix"],
                due_date=None,
                completed_at=None,
            ),
            SimpleNamespace(
                object_type="task",
                status="completed",
                priority="normal",
                project_id=None,
                department_id=None,
                team_id=None,
                tags=[],
                due_date=None,
                completed_at=None,
            ),
        ]

        distributions = WorkDNAService.distributions(
            work_items,
            projects={project_id: SimpleNamespace(name="FebGuyAI")},
            departments={department_id: SimpleNamespace(name="Software Department")},
            teams={team_id: SimpleNamespace(name="Core Team")},
        )

        project_labels = {row["label"] for row in distributions["projects"]}
        department_labels = {row["label"] for row in distributions["departments"]}
        team_labels = {row["label"] for row in distributions["teams"]}

        self.assertIn("FebGuyAI", project_labels)
        self.assertIn("No linked project", project_labels)
        self.assertIn("Software Department", department_labels)
        self.assertIn("No linked department", department_labels)
        self.assertIn("Core Team", team_labels)
        self.assertIn("No linked team", team_labels)


if __name__ == "__main__":
    unittest.main()
