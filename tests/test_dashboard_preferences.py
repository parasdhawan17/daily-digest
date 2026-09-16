import json
import unittest
from pathlib import Path

from stock_news.dashboard_preferences import (
    allowed_cards,
    catalog,
    default_cards,
    parse_dashboard_cards,
    serialize_dashboard_cards,
)


class DashboardPreferencesTest(unittest.TestCase):
    def test_catalog_has_unique_cards_and_hierarchical_defaults(self):
        data = catalog()
        ids = [card["id"] for category in data["categories"] for card in category["cards"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(tuple(ids), allowed_cards())
        self.assertIn("overview_market_cap", default_cards())
        self.assertIn("ai_watchlist_briefing", default_cards())
        self.assertIn("news_company_coverage", default_cards())
        self.assertNotIn("ownership_current_mix", default_cards())
        for category in data["categories"]:
            self.assertTrue(set(category["recommended"]).issubset({card["id"] for card in category["cards"]}))

    def test_parser_orders_filters_and_serializes(self):
        self.assertEqual(
            parse_dashboard_cards(["news_company_coverage", "bad", "overview_market_cap"], default_if_empty=False),
            ["overview_market_cap", "news_company_coverage"],
        )
        self.assertEqual(serialize_dashboard_cards(["news_company_coverage"]), "news_company_coverage")
        self.assertEqual(parse_dashboard_cards(""), default_cards())

    def test_vercel_function_bundles_the_catalog(self):
        config = json.loads(Path("vercel.json").read_text(encoding="utf-8"))
        self.assertEqual(
            config["functions"]["api/index.py"]["includeFiles"],
            "public/dashboard-catalog.json",
        )


if __name__ == "__main__":
    unittest.main()
