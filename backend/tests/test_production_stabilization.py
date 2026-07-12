import inspect
import unittest

from app.api.routes import dashboard, events
from app.models.event import Event
from app.services.event_service import EventService


class ProductionStabilizationTests(unittest.TestCase):
    def test_dashboard_uses_grouped_domain_counts(self) -> None:
        source = inspect.getsource(dashboard.get_dashboard_summary)
        self.assertIn("grouped_counts(", source)
        self.assertNotIn("count_rows(", source)
        self.assertIn("notification_counts_statement", source)

    def test_timeline_is_bounded_and_uses_stable_keyset_ordering(self) -> None:
        source = inspect.getsource(events.universal_timeline)
        self.assertIn("default=50", source)
        self.assertIn("before_created_at", source)
        self.assertIn("before_id", source)
        self.assertIn("Event.created_at.desc(), Event.id.desc()", source)
        self.assertIn("Event.company_id == company_id", source)

    def test_audit_enrichment_is_joined_instead_of_per_row(self) -> None:
        list_source = inspect.getsource(events.audit_log)
        serializer_source = inspect.getsource(events.serialize_audit_event)
        self.assertIn("joinedload(Event.actor_user)", list_source)
        self.assertIn("joinedload(Event.actor)", list_source)
        self.assertIn("joinedload(Event.company)", list_source)
        self.assertNotIn("db.get", serializer_source)

    def test_event_writes_batch_with_the_owning_transaction(self) -> None:
        source = inspect.getsource(EventService.record_event)
        self.assertIn("id=uuid4()", source)
        self.assertNotIn("db.flush()", source)

    def test_timeline_indexes_match_company_time_and_type_filters(self) -> None:
        index_columns = {
            index.name: tuple(column.name for column in index.columns)
            for index in Event.__table__.indexes
        }
        self.assertEqual(index_columns["idx_events_company_id_created_at"], ("company_id", "created_at"))
        self.assertEqual(index_columns["idx_events_company_type_created_at"], ("company_id", "event_type", "created_at"))


if __name__ == "__main__":
    unittest.main()
