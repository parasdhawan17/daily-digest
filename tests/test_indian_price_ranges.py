import unittest
from unittest.mock import Mock, patch

from stock_news.digest import build_price_ranges, collect_digest_data
from stock_news.indianapi import fetch_all_time_high, fetch_quote
from stock_news.render import build_web_section


def indian_section() -> dict:
    return {
        "ticker": "IN:RELIANCE",
        "display_symbol": "RELIANCE",
        "market": "IN",
        "exchange": "NSE",
        "quote": {"price": 2856.40, "change_pct": -0.42, "year_high": 3217.60},
        "price_ranges": {
            "year_high": {"value": 3217.60, "distance_pct": 11.2258},
            "all_time_high": {"value": 3500.00, "distance_pct": 18.3886},
        },
        "logo": None,
        "earnings_history": None,
        "upcoming_earnings": None,
        "stories": [],
        "web_stories": [],
        "error": None,
    }


class IndianPriceProviderTest(unittest.TestCase):
    @patch("stock_news.indianapi.requests.get")
    def test_quote_preserves_52_week_high(self, get: Mock) -> None:
        response = Mock()
        response.json.return_value = {
            "currentPrice": {"NSE": 2856.40, "BSE": 2858.10},
            "percentChange": -0.42,
            "yearHigh": "3,217.60",
        }
        get.return_value = response

        result = fetch_quote("RELIANCE", "key")

        self.assertEqual(result, {
            "price": 2856.40,
            "change_pct": -0.42,
            "year_high": 3217.60,
        })

    @patch("stock_news.indianapi.requests.get")
    def test_derives_all_time_high_from_price_dataset(self, get: Mock) -> None:
        response = Mock()
        response.json.return_value = {
            "datasets": [
                {
                    "metric": "Price",
                    "label": "Price on NSE",
                    "values": [
                        ["2020-01-01", "1,410.50"],
                        ["2024-07-15", "3,217.60"],
                        ["2026-08-27", 2856.40],
                    ],
                },
                {"metric": "DMA200", "values": [["2026-08-27", 9000]]},
            ]
        }
        get.return_value = response

        result = fetch_all_time_high("RELIANCE", "key")

        self.assertEqual(result, 3217.60)
        get.assert_called_once_with(
            "https://stock.indianapi.in/historical_data",
            params={"stock_name": "RELIANCE", "period": "max", "filter": "price"},
            headers={"Accept": "application/json", "x-api-key": "key"},
            timeout=30,
        )


class IndianPriceRangeCollectionTest(unittest.TestCase):
    def test_builds_highs_and_percentage_below_for_web(self) -> None:
        with (
            patch(
                "stock_news.digest.fetch_quote",
                return_value={"price": 2856.40, "change_pct": -0.42, "year_high": 3217.60},
            ),
            patch("stock_news.digest.fetch_all_time_high", return_value=3500.00) as all_time,
            patch("stock_news.digest.fetch_company_logo", return_value=None),
            patch("stock_news.digest.fetch_news", return_value=[]),
        ):
            sections, _ = collect_digest_data(
                ["IN:RELIANCE"],
                finnhub_key="finnhub-key",
                indianapi_key="india-key",
                include_price_ranges=True,
            )

        ranges = sections[0]["price_ranges"]
        self.assertAlmostEqual(ranges["year_high"]["distance_pct"], 11.2258, places=4)
        self.assertAlmostEqual(ranges["all_time_high"]["distance_pct"], 18.3886, places=4)
        all_time.assert_called_once_with(
            "IN:RELIANCE",
            finnhub_key="finnhub-key",
            indianapi_key="india-key",
        )

    def test_does_not_fetch_ranges_for_email_or_us_stocks(self) -> None:
        with (
            patch("stock_news.digest.fetch_quote", return_value={"price": 100.0, "change_pct": 1.0}),
            patch("stock_news.digest.fetch_all_time_high") as all_time,
            patch("stock_news.digest.fetch_company_logo", return_value=None),
            patch("stock_news.digest.fetch_news", return_value=[]),
        ):
            india, _ = collect_digest_data(
                ["IN:TCS"],
                finnhub_key="finnhub-key",
                indianapi_key="india-key",
            )
            us, _ = collect_digest_data(
                ["US:AAPL"],
                finnhub_key="finnhub-key",
                indianapi_key="india-key",
                include_price_ranges=True,
            )

        all_time.assert_not_called()
        self.assertIsNone(india[0]["price_ranges"])
        self.assertIsNone(us[0]["price_ranges"])

    def test_stale_provider_highs_never_produce_negative_distance(self) -> None:
        ranges = build_price_ranges(110.0, year_high=100.0, all_time_high=105.0)
        self.assertEqual(ranges["year_high"], {"value": 110.0, "distance_pct": 0.0})
        self.assertEqual(ranges["all_time_high"], {"value": 110.0, "distance_pct": 0.0})


class IndianPriceRangeRenderTest(unittest.TestCase):
    def test_renders_compact_high_chips_for_indian_web_section(self) -> None:
        html = build_web_section(indian_section())

        self.assertIn('class="price-ranges"', html)
        self.assertIn("52W high", html)
        self.assertIn("₹3217.60", html)
        self.assertIn("11.2% below", html)
        self.assertIn("ATH", html)
        self.assertIn("₹3500.00", html)
        self.assertIn("18.4% below", html)

    def test_never_renders_high_chips_for_us_sections(self) -> None:
        section = indian_section()
        section.update({"ticker": "US:AAPL", "market": "US", "exchange": "US"})

        html = build_web_section(section)

        self.assertNotIn('class="price-ranges"', html)
        self.assertNotIn("52W high", html)


if __name__ == "__main__":
    unittest.main()
