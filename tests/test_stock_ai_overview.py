import json
import unittest
from unittest.mock import patch

from stock_news import stock_ai_overview as overview


def core_data():
    return {
        "name": "Example Ltd", "industry": "Software",
        "prices": {"NSE": 100, "BSE": 101}, "change_percent": 1.5,
        "year_low": 70, "year_high": 120,
        "snapshot": {
            "marketCap": 5000,
            "pPerEBasicExcludingExtraordinaryItemsTTM": 24,
            "sectorPriceToEarningsValueRatio": 28,
        },
        "health": {"period": "FY2026", "groups": [{"title": "Growth", "metrics": [{
            "label": "Revenue", "value": 900, "unit": "₹ cr", "period": "FY2026",
            "change_label": "+12.0% YoY",
        }]}]},
        "ownership": [], "peers": [], "ratings": [], "recommendations": [],
        "technical": None, "risk": None, "actions": {},
        "news": [{"headline": "Example wins a contract", "summary": "A new order was announced.",
                  "source": "Example News", "date": "2026-09-14"}],
        "profile": {"companyDescription": "Example makes business software."},
    }


def model_result():
    return {
        "summary": {"heading": "Profitable growth at a discount",
                    "text": "Revenue increased while valuation remains below the supplied peer benchmark.",
                    "tone": "positive",
                    "evidence_ids": ["S1", "S2"]},
        "encouraging": [{"heading": "Revenue momentum", "text": "Revenue rose year over year.",
                         "tone": "positive", "evidence_ids": ["S2"]}],
        "attention": [],
        "changes": [{"heading": "Growth accelerated", "text": "Revenue increased 12% year over year.",
                     "tone": "positive", "evidence_ids": ["S2"]}],
        "catalysts": [{"heading": "New contract", "text": "The reported contract could support future activity.",
                       "tone": "positive", "evidence_ids": ["S3"]}],
        "risks": [],
        "watch_next": [{"heading": "Revenue durability", "text": "Does revenue growth persist next period?",
                        "tone": "neutral", "evidence_ids": ["S2"]}],
    }


class EvidenceTests(unittest.TestCase):
    def test_evidence_is_compact_and_covers_visible_sections(self):
        evidence = overview.build_evidence(core_data())
        self.assertLessEqual(len(evidence), 8)
        self.assertEqual([row["id"] for row in evidence], [f"S{i}" for i in range(1, len(evidence) + 1)])
        self.assertIn("financials", {row["section"] for row in evidence})
        self.assertIn("news", {row["section"] for row in evidence})
        self.assertLess(len(json.dumps(evidence)), 10000)

    def test_past_corporate_actions_are_excluded_from_catalyst_evidence(self):
        data = core_data()
        data["actions"] = {"dividend": [{"recordDate": "2020-01-01", "remarks": "Paid"}],
                           "boardMeetings": [{"meetingDate": "2099-01-01", "remarks": "Results"}]}
        actions = next(row for row in overview.build_evidence(data)
                       if row["label"] == "Recent corporate actions")
        self.assertEqual(len(actions["data"]), 1)
        self.assertEqual(actions["data"][0]["event_date"], "2099-01-01")

    def test_parser_drops_invalid_items_and_rejects_ungrounded_summary(self):
        raw = model_result()
        raw["risks"] = [{"heading": "Unsupported", "text": "Unsupported risk.",
                         "tone": "negative", "evidence_ids": ["S99"]}]
        parsed = overview._parse(json.dumps(raw), {"S1", "S2", "S3"})
        self.assertEqual(parsed["risks"], [])
        raw["summary"]["evidence_ids"] = ["S99"]
        self.assertIsNone(overview._parse(json.dumps(raw), {"S1", "S2", "S3"}))

    def test_parser_requires_a_valid_semantic_tone(self):
        raw = model_result()
        raw["encouraging"][0]["tone"] = "bullish"
        parsed = overview._parse(json.dumps(raw), {"S1", "S2", "S3"})
        self.assertEqual(parsed["encouraging"], [])

    def test_prompt_labels_reported_actuals_and_dates_catalysts(self):
        prompt = overview._prompt("IN:EXAMPLE", overview.build_evidence(core_data()))
        self.assertIn("historical actuals", prompt)
        self.assertIn("future-dated", prompt)
        self.assertIn("summary.heading as the overall takeaway", prompt)
        self.assertIn('Avoid "Overview"', prompt)


class GenerationTests(unittest.TestCase):
    def setUp(self):
        with overview._lock:
            overview._cache.clear()
            overview._pending.clear()

    @patch.object(overview.ai_summary, "OPENROUTER_API_KEY", "test-key")
    @patch.object(overview.ai_summary, "_request_structured_json")
    def test_generation_is_one_bounded_request_and_cached(self, request):
        request.return_value = model_result()
        first, ttl = overview.get_stock_ai_overview("IN:EXAMPLE", core_data())
        second, remaining = overview.get_stock_ai_overview("IN:EXAMPLE", core_data())

        self.assertIs(first, second)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(request.call_args.kwargs["max_tokens"], 900)
        self.assertEqual(request.call_args.kwargs["retries"], 0)
        self.assertEqual(ttl, overview.TTL_SECONDS)
        self.assertLessEqual(remaining, ttl)
        self.assertEqual(first["data"]["sources"][0]["id"], "S1")
        self.assertEqual(first["schema_version"], 2)
        self.assertNotIn("data", first["data"]["sources"][0])

    @patch.object(overview.ai_summary, "OPENROUTER_API_KEY", "")
    def test_disabled_ai_does_not_generate(self):
        self.assertEqual(overview.get_stock_ai_overview("IN:EXAMPLE", core_data()), (None, 0))


if __name__ == "__main__":
    unittest.main()
