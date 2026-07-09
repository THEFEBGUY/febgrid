import unittest

from app.services.ai_output_parser import parse_ai_provider_output


class AIOutputParserTests(unittest.TestCase):
    def test_plain_json_maps_work_object_fields(self) -> None:
        parsed = parse_ai_provider_output(
            '{"summary":"Done","key_points":["A"],"blockers_or_risks":[],"suggested_next_steps":["Ship"],"confidence":null}',
            "work_object_summary_safe",
        )

        self.assertFalse(parsed.output_payload["parsing_error"])
        self.assertEqual(parsed.output_payload["summary"], "Done")
        self.assertEqual(parsed.output_payload["key_points"], ["A"])
        self.assertEqual(parsed.output_payload["suggested_next_steps"], ["Ship"])
        self.assertIsNone(parsed.output_payload["confidence"])

    def test_fenced_json_maps_project_fields(self) -> None:
        parsed = parse_ai_provider_output(
            """```json
{"summary":"Project active","project_health":"watch","progress_overview":"0%","open_work_overview":"2 open","risks_or_blockers":["Overdue"],"suggested_next_steps":["Review"]}
```""",
            "project_summary_safe",
        )

        self.assertEqual(parsed.metadata["output_parse_status"], "parsed_json")
        self.assertTrue(parsed.metadata["markdown_fence_removed"])
        self.assertEqual(parsed.output_payload["summary"], "Project active")
        self.assertEqual(parsed.output_payload["project_health"], "watch")
        self.assertEqual(parsed.output_payload["progress_overview"], "0%")
        self.assertEqual(parsed.output_payload["open_work_overview"], "2 open")
        self.assertEqual(parsed.output_payload["risks_or_blockers"], ["Overdue"])

    def test_json_surrounded_by_text_maps_company_brief_fields(self) -> None:
        parsed = parse_ai_provider_output(
            'Here is the brief: {"executive_summary":"Healthy company","operational_highlights":["7 employees"],"work_overview":"Stable","project_overview":"One active","people_overview":"5 available","leave_overview":"No pending","risks_or_blockers":["Unread notifications"],"suggested_next_actions":["Review notifications"],"attention_items":["Communication"]} Thanks.',
            "company_brief_safe",
        )

        self.assertEqual(parsed.output_payload["executive_summary"], "Healthy company")
        self.assertEqual(parsed.output_payload["operational_highlights"], ["7 employees"])
        self.assertEqual(parsed.output_payload["work_overview"], "Stable")
        self.assertEqual(parsed.output_payload["project_overview"], "One active")
        self.assertEqual(parsed.output_payload["people_overview"], "5 available")
        self.assertEqual(parsed.output_payload["leave_overview"], "No pending")
        self.assertEqual(parsed.output_payload["suggested_next_actions"], ["Review notifications"])

    def test_malformed_json_uses_clean_safe_fallback(self) -> None:
        parsed = parse_ai_provider_output(
            """```json
{"summary": "broken", "key_points": [
```""",
            "work_object_summary_safe",
        )

        self.assertTrue(parsed.output_payload["parsing_error"])
        self.assertEqual(parsed.output_payload["parsing_error_code"], "invalid_json")
        self.assertNotIn("```", parsed.output_payload["summary"])
        self.assertIn("malformed structured output", parsed.output_payload["summary"])

    def test_preserves_nested_arrays_booleans_nulls_and_objects(self) -> None:
        parsed = parse_ai_provider_output(
            '{"summary":"File summary","key_points":["one",{"nested":true}],"truncated":true,"confidence":null,"extra":{"ok":true,"value":3}}',
            "file_summary_safe",
        )

        self.assertEqual(parsed.output_payload["summary"], "File summary")
        self.assertEqual(parsed.output_payload["key_points"], ["one", {"nested": True}])
        self.assertTrue(parsed.output_payload["truncated"])
        self.assertIsNone(parsed.output_payload["confidence"])
        self.assertEqual(parsed.output_payload["extra"], {"ok": True, "value": 3})


if __name__ == "__main__":
    unittest.main()
