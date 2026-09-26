import json
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from stock_news import stock_section_ai as section_ai


def model_result():
    return {
        "heading": "Price sits near its low",
        "summary": "The reported price is ₹1,226, close to the 52-week low of ₹1,219.",
        "meaning": "This section places the current price inside its reported 52-week range.",
        "facts": [
            {"label": "Current price", "value": "₹1,226"},
            {"label": "52-week low", "value": "₹1,219"},
        ],
        "tone": "caution",
    }


EVIDENCE = "Price context Reported price landmarks ₹ Current price ₹1,226 52-week low ₹1,219 52-week high ₹1,611.20"


class ValidationTests(unittest.TestCase):
    def test_only_allowlisted_sections_and_cards_are_accepted(self):
        values = section_ai.validate_input("overview", "price_context", "Price context", EVIDENCE)
        self.assertEqual(values[:3], ("overview", "price_context", "Price context"))
        section_ai.validate_input("overview", "current_p_e", "Current P/E", "Current P/E 42.3×")
        section_ai.validate_input(
            "overview", "overview_price_landmarks", "Price context", EVIDENCE)
        section_ai.validate_input(
            "financials", "financial_health_growth", "Growth health", "Revenue ₹1,226")
        section_ai.validate_input(
            "news", "news_company_coverage", "Company coverage", "One reported company story")
        with self.assertRaises(ValueError):
            section_ai.validate_input("ai-overview", "summary", "Summary", EVIDENCE)
        with self.assertRaises(ValueError):
            section_ai.validate_input("overview", "unknown", "Unknown", EVIDENCE)

    def test_every_factual_dashboard_card_is_allowlisted(self):
        from stock_news.dashboard_preferences import catalog

        for category in catalog()["categories"]:
            if category["id"] == "ai":
                continue
            for card in category["cards"]:
                self.assertIn(card["id"], section_ai.CARDS[category["id"]])

    def test_evidence_is_bounded(self):
        with self.assertRaises(ValueError):
            section_ai.validate_input("overview", "price_context", "Price context", "x" * 8001)

    def test_parser_requires_complete_schema_and_rejects_invented_numbers(self):
        parsed = section_ai._parse(json.dumps(model_result()), EVIDENCE)
        self.assertEqual(parsed["facts"][0]["value"], "₹1,226")
        bad = model_result()
        bad["facts"][0]["value"] = "₹9,999"
        self.assertIsNone(section_ai._parse(json.dumps(bad), EVIDENCE))
        bad = model_result()
        bad["facts"] = []
        self.assertIsNone(section_ai._parse(json.dumps(bad), EVIDENCE))

    def test_prompt_marks_page_text_untrusted_and_forbids_advice(self):
        prompt = section_ai._prompt("IN:EXAMPLE", "overview", "Price context", EVIDENCE)
        self.assertIn("untrusted external evidence", prompt)
        self.assertIn("Never calculate, infer or invent", prompt)
        self.assertIn("investment advice", prompt)


class GenerationTests(unittest.TestCase):
    def setUp(self):
        with section_ai._lock:
            section_ai._cache.clear()
            section_ai._pending.clear()

    @patch.object(section_ai.ai_summary, "OPENROUTER_API_KEY", "test-key")
    @patch.object(section_ai.ai_summary, "_request_structured_json")
    def test_generation_is_bounded_and_cached_by_visible_content(self, request):
        request.return_value = model_result()
        first, ttl = section_ai.get_stock_section_explanation(
            "IN:EXAMPLE", "overview", "price_context", "Price context", EVIDENCE)
        second, remaining = section_ai.get_stock_section_explanation(
            "IN:EXAMPLE", "overview", "price_context", "Price context", EVIDENCE)
        self.assertIs(first, second)
        self.assertEqual(request.call_count, 1)
        self.assertEqual(request.call_args.kwargs["max_tokens"], 500)
        self.assertEqual(request.call_args.kwargs["retries"], 0)
        self.assertEqual(ttl, section_ai.TTL_SECONDS)
        self.assertLessEqual(remaining, ttl)
        self.assertEqual(first["card_id"], "price_context")
        self.assertIn("generated_at", first["data"])

        section_ai.get_stock_section_explanation(
            "IN:EXAMPLE", "overview", "price_context", "Price context", EVIDENCE + " Updated")
        self.assertEqual(request.call_count, 2)

    @patch.object(section_ai.ai_summary, "OPENROUTER_API_KEY", "test-key")
    @patch.object(section_ai.ai_summary, "_request_structured_json")
    def test_concurrent_identical_requests_are_coalesced(self, request):
        entered = threading.Event()
        release = threading.Event()

        def generate(**kwargs):
            entered.set()
            release.wait(2)
            return model_result()

        request.side_effect = generate
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(section_ai.get_stock_section_explanation,
                                "IN:EXAMPLE", "overview", "price_context", "Price context", EVIDENCE)
            self.assertTrue(entered.wait(1))
            second = pool.submit(section_ai.get_stock_section_explanation,
                                 "IN:EXAMPLE", "overview", "price_context", "Price context", EVIDENCE)
            time.sleep(.03)
            release.set()
            self.assertEqual(first.result()[0], second.result()[0])
        self.assertEqual(request.call_count, 1)

    @patch.object(section_ai.ai_summary, "OPENROUTER_API_KEY", "")
    def test_disabled_ai_returns_unavailable(self):
        self.assertEqual(section_ai.get_stock_section_explanation(
            "IN:EXAMPLE", "overview", "price_context", "Price context", EVIDENCE), (None, 0))


if __name__ == "__main__":
    unittest.main()
