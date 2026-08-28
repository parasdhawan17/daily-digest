import io
import json
import unittest
from unittest.mock import Mock, patch

import requests

from api.digest import handle_data_get
from stock_news.digest import (
    build_earnings_history,
    build_indian_earnings_history,
    collect_digest_data,
)
from stock_news.finnhub import fetch_earnings_history, fetch_upcoming_earnings
from stock_news.indianapi import fetch_earnings_history as fetch_indian_earnings_history
from stock_news.render import build_web_digest, build_web_section


def quarter(
    period: str,
    year: int,
    fiscal_quarter: int,
    actual: float | None,
    estimate: float | None,
    surprise_pct: float | None,
) -> dict:
    if surprise_pct is None:
        result = "unavailable"
    elif surprise_pct > 0:
        result = "beat"
    elif surprise_pct < 0:
        result = "miss"
    else:
        result = "inline"
    return {
        "period": period,
        "fiscal_year": year,
        "fiscal_quarter": fiscal_quarter,
        "label": f"Q{fiscal_quarter} FY{str(year)[-2:]}",
        "actual": actual,
        "estimate": estimate,
        "surprise": None,
        "surprise_pct": surprise_pct,
        "result": result,
    }


def sample_history() -> dict:
    return build_earnings_history(
        [
            quarter("2025-09-30", 2025, 4, 1.85, 1.81, 2.4),
            quarter("2025-12-31", 2026, 1, 2.84, 2.73, 4.2),
            quarter("2026-03-31", 2026, 2, 2.01, 1.99, 1.1),
            quarter("2026-06-30", 2026, 3, 1.91, 1.93, -0.9),
        ]
    )


def sample_indian_history() -> dict:
    quarters = []
    for period, period_label, label, eps, sales, net_profit, opm_pct in [
        ("2025-09-01", "Sep 2025", "Q2 FY26", 30.26, 59381, 11120, 25),
        ("2025-12-01", "Dec 2025", "Q3 FY26", 31.00, 59692, 11380, 26),
        ("2026-03-01", "Mar 2026", "Q4 FY26", 30.56, 60583, 11097, 27),
        ("2026-06-01", "Jun 2026", "Q1 FY27", 34.37, 61237, 12502, 28),
    ]:
        quarters.append({
            "mode": "reported",
            "period": period,
            "period_label": period_label,
            "label": label,
            "actual": eps,
            "sales": sales,
            "net_profit": net_profit,
            "opm_pct": opm_pct,
        })
    return build_indian_earnings_history(quarters)


def sample_section(history: dict | None = None) -> dict:
    return {
        "ticker": "US:AAPL",
        "display_symbol": "AAPL",
        "market": "US",
        "exchange": "US",
        "quote": {"price": 228.3, "change_pct": 1.18},
        "logo": None,
        "earnings_history": history,
        "upcoming_earnings": {
            "date": "2026-09-15",
            "date_label": "15 Sep 2026",
            "hour": "amc",
            "eps_estimate": 2.14,
            "eps_actual": None,
            "revenue_estimate": 102000000000,
            "revenue_actual": None,
        },
        "stories": [],
        "web_stories": [
            {
                "headline": "Apple reports quarterly results",
                "url": "https://example.com/apple",
                "source": "Example",
                "summary": "Results were released.",
            }
        ],
        "error": None,
    }


class FinnhubEarningsTest(unittest.TestCase):
    @patch("stock_news.finnhub.requests.get")
    def test_fetches_and_normalizes_latest_four_quarters(self, get: Mock) -> None:
        response = Mock()
        response.json.return_value = [
            {
                "period": "2026-03-31",
                "year": 2026,
                "quarter": 1,
                "actual": 1.2,
                "estimate": 1.0,
                "surprise": 0.2,
                "surprisePercent": 20.0,
            },
            {"period": "", "year": 2025, "quarter": 4},
            {
                "period": "2025-06-30",
                "year": 2025,
                "quarter": 2,
                "actual": 0,
                "estimate": 0,
                "surprise": 0,
                "surprisePercent": 0,
            },
            {
                "period": "2025-12-31",
                "year": 2025,
                "quarter": 4,
                "actual": -0.4,
                "estimate": -0.3,
                "surprise": -0.1,
                "surprisePercent": -33.3,
            },
            {
                "period": "2025-03-31",
                "year": 2025,
                "quarter": 1,
                "actual": 0.5,
                "estimate": 0.4,
                "surprisePercent": 25,
            },
            {
                "period": "2025-09-30",
                "year": 2025,
                "quarter": 3,
                "actual": 0.8,
                "estimate": None,
                "surprise": None,
                "surprisePercent": None,
            },
            "malformed",
        ]
        get.return_value = response

        result = fetch_earnings_history("AAPL", "key", limit=4)

        response.raise_for_status.assert_called_once_with()
        get.assert_called_once_with(
            "https://finnhub.io/api/v1/stock/earnings",
            params={"symbol": "AAPL", "limit": 4, "token": "key"},
            timeout=30,
        )
        self.assertEqual([item["period"] for item in result], [
            "2025-06-30",
            "2025-09-30",
            "2025-12-31",
            "2026-03-31",
        ])
        self.assertEqual(result[0]["actual"], 0.0)
        self.assertEqual(result[0]["estimate"], 0.0)
        self.assertEqual(result[0]["result"], "inline")
        self.assertEqual(result[1]["result"], "unavailable")
        self.assertEqual(result[2]["result"], "miss")
        self.assertEqual(result[3]["result"], "beat")

    @patch("stock_news.finnhub.requests.get")
    def test_non_list_response_is_unavailable(self, get: Mock) -> None:
        response = Mock()
        response.json.return_value = {"error": "not available"}
        get.return_value = response
        self.assertEqual(fetch_earnings_history("VOO", "key"), [])

    @patch("stock_news.finnhub.requests.get")
    def test_fetches_next_calendar_event_and_normalizes_values(self, get: Mock) -> None:
        response = Mock()
        response.json.return_value = {
            "earningsCalendar": [
                {"date": "2099-10-10", "hour": "amc", "epsEstimate": 3.2},
                {
                    "date": "2099-09-15",
                    "hour": "bmo",
                    "epsEstimate": 2.14,
                    "epsActual": None,
                    "revenueEstimate": 102000000000,
                    "revenueActual": None,
                },
                {"date": "not-a-date"},
            ]
        }
        get.return_value = response

        result = fetch_upcoming_earnings("AAPL", "key", lookahead_days=90)

        response.raise_for_status.assert_called_once_with()
        call_params = get.call_args.kwargs["params"]
        self.assertEqual(call_params["symbol"], "AAPL")
        self.assertEqual(call_params["token"], "key")
        self.assertEqual(result["date"], "2099-09-15")
        self.assertEqual(result["date_label"], "15 Sep 2099")
        self.assertEqual(result["eps_estimate"], 2.14)
        self.assertIsNone(result["eps_actual"])
        self.assertEqual(result["revenue_estimate"], 102000000000.0)

    @patch("stock_news.finnhub.requests.get")
    def test_calendar_without_events_is_unavailable(self, get: Mock) -> None:
        response = Mock()
        response.json.return_value = {"earningsCalendar": []}
        get.return_value = response
        self.assertIsNone(fetch_upcoming_earnings("AAPL", "key"))


class IndianApiEarningsTest(unittest.TestCase):
    @patch("stock_news.indianapi.requests.get")
    def test_fetches_and_normalizes_latest_four_reported_quarters(self, get: Mock) -> None:
        response = Mock()
        response.json.return_value = {
            "Sales": {
                "Jun 2025": "58,100",
                "Sep 2025": "59,381",
                "Dec 2025": 59692,
                "Mar 2026": 60583,
                "Jun 2026": 61237,
            },
            "Net Profit": {
                "Jun 2025": 10800,
                "Sep 2025": 11120,
                "Dec 2025": 11380,
                "Mar 2026": 11097,
                "Jun 2026": 12502,
            },
            "EPS in Rs": {
                "Jun 2025": 29.10,
                "Sep 2025": 30.26,
                "Dec 2025": 31,
                "Mar 2026": 30.56,
                "Jun 2026": 34.37,
            },
            "OPM %": {
                "Jun 2025": "24%",
                "Sep 2025": 25,
                "Dec 2025": 26,
                "Mar 2026": 27,
                "Jun 2026": 28,
            },
        }
        get.return_value = response

        result = fetch_indian_earnings_history("TCS", "key", limit=4)

        response.raise_for_status.assert_called_once_with()
        get.assert_called_once_with(
            "https://stock.indianapi.in/historical_stats",
            params={"stock_name": "TCS", "stats": "quarter_results"},
            headers={"Accept": "application/json", "x-api-key": "key"},
            timeout=30,
        )
        self.assertEqual([item["period_label"] for item in result], [
            "Sep 2025", "Dec 2025", "Mar 2026", "Jun 2026"
        ])
        self.assertEqual([item["label"] for item in result], [
            "Q2 FY26", "Q3 FY26", "Q4 FY26", "Q1 FY27"
        ])
        self.assertEqual(result[-1]["actual"], 34.37)
        self.assertEqual(result[-1]["sales"], 61237.0)
        self.assertEqual(result[-1]["net_profit"], 12502.0)
        self.assertEqual(result[-1]["opm_pct"], 28.0)


class EarningsCollectionTest(unittest.TestCase):
    def _collect(self, ticker: str, *, include_earnings: bool = False) -> list[dict]:
        with (
            patch("stock_news.digest.fetch_quote", return_value=None),
            patch("stock_news.digest.fetch_company_logo", return_value=None),
            patch("stock_news.digest.fetch_news", return_value=[]),
            patch("stock_news.digest.fetch_earnings_history", return_value=[
                quarter("2026-06-30", 2026, 2, 0.33, 0.52, -36.4)
            ]) as earnings,
            patch("stock_news.digest.fetch_upcoming_earnings", return_value={
                "date": "2026-09-15",
                "date_label": "15 Sep 2026",
                "hour": "amc",
                "eps_estimate": 2.14,
                "eps_actual": None,
                "revenue_estimate": 102000000000,
                "revenue_actual": None,
            }) as upcoming,
        ):
            sections, _ = collect_digest_data(
                [ticker],
                finnhub_key="finnhub-key",
                indianapi_key="india-key",
                include_earnings=include_earnings,
            )
            self.earnings_mock = earnings
            self.upcoming_mock = upcoming
            return sections

    def test_default_collection_does_not_fetch_earnings(self) -> None:
        sections = self._collect("US:AAPL")
        self.earnings_mock.assert_not_called()
        self.upcoming_mock.assert_not_called()
        self.assertIsNone(sections[0]["earnings_history"])
        self.assertIsNone(sections[0]["upcoming_earnings"])

    def test_web_collection_fetches_us_earnings(self) -> None:
        sections = self._collect("US:TSLA", include_earnings=True)
        self.earnings_mock.assert_called_once_with(
            "US:TSLA",
            finnhub_key="finnhub-key",
            indianapi_key="india-key",
            limit=4,
        )
        self.upcoming_mock.assert_called_once_with(
            "US:TSLA",
            finnhub_key="finnhub-key",
            indianapi_key="india-key",
        )
        self.assertEqual(sections[0]["earnings_history"]["summary_label"], "1 miss")
        self.assertEqual(sections[0]["upcoming_earnings"]["date"], "2026-09-15")

    def test_web_collection_fetches_indian_reported_earnings(self) -> None:
        sections = self._collect("IN:RELIANCE", include_earnings=True)
        self.earnings_mock.assert_called_once_with(
            "IN:RELIANCE",
            finnhub_key="finnhub-key",
            indianapi_key="india-key",
            limit=4,
        )
        self.upcoming_mock.assert_not_called()
        self.assertEqual(sections[0]["earnings_history"]["mode"], "reported")
        self.assertEqual(sections[0]["earnings_history"]["summary_label"], "Latest EPS ₹0.33")
        self.assertIsNone(sections[0]["upcoming_earnings"])

    def test_earnings_failure_does_not_fail_the_ticker(self) -> None:
        with (
            patch("stock_news.digest.fetch_quote", return_value={"price": 10, "change_pct": 1}),
            patch("stock_news.digest.fetch_company_logo", return_value=None),
            patch("stock_news.digest.fetch_news", return_value=[]),
            patch(
                "stock_news.digest.fetch_earnings_history",
                side_effect=requests.RequestException("provider error"),
            ),
            patch(
                "stock_news.digest.fetch_upcoming_earnings",
                side_effect=requests.RequestException("provider error"),
            ),
        ):
            sections, _ = collect_digest_data(
                ["US:AAPL"],
                finnhub_key="finnhub-key",
                indianapi_key="india-key",
                include_earnings=True,
            )
        self.assertIsNone(sections[0]["earnings_history"])
        self.assertIsNone(sections[0]["upcoming_earnings"])
        self.assertIsNone(sections[0]["error"])
        self.assertEqual(sections[0]["quote"]["price"], 10)


class EarningsRenderTest(unittest.TestCase):
    def test_renders_collapsed_chart_and_comparison_table(self) -> None:
        html = build_web_section(sample_section(sample_history()))

        self.assertIn('<details class="earnings-history">', html)
        self.assertIn("<span class=\"earnings-summary-title\">Earnings</span>", html)
        self.assertIn("earnings-chart-row is-upcoming", html)
        self.assertIn("earnings-result upcoming", html)
        self.assertIn("15 Sep 2026", html)
        self.assertNotIn("<th scope=\"row\">Revenue estimate</th>", html)
        self.assertNotIn("<th scope=\"row\">Revenue actual</th>", html)
        self.assertNotIn('<details class="earnings-history" open', html)
        self.assertIn("3 beats · 1 miss", html)
        self.assertIn("EPS surprise vs consensus", html)
        self.assertIn("Reported EPS", html)
        self.assertIn("Estimate", html)
        self.assertIn("Latest", html)
        self.assertIn("+4.2%", html)
        self.assertIn("-0.9%", html)
        self.assertLess(html.index("Q4 FY25"), html.index("Q3 FY26"))
        self.assertLess(html.index("ticker-head"), html.index("earnings-history"))
        self.assertLess(html.index("earnings-history"), html.index("story-list"))

    def test_hides_panel_when_history_is_unavailable(self) -> None:
        section = sample_section(None)
        section["upcoming_earnings"] = None
        html = build_web_section(section)
        self.assertNotIn("earnings-history", html)
        self.assertNotIn("Earnings history", html)
        self.assertNotIn("Upcoming earnings", html)
        self.assertNotIn("<span class=\"earnings-summary-title\">Earnings</span>", html)

    def test_progressive_shell_includes_earnings_skeleton(self) -> None:
        html = build_web_digest(
            [],
            ["US:AAPL"],
            progressive=True,
            progressive_token="token",
        )
        self.assertIn("skeleton-earnings", html)

        india_html = build_web_digest(
            [],
            ["IN:RELIANCE"],
            progressive=True,
            progressive_token="token",
        )
        self.assertIn('<div class="skeleton skeleton-earnings">', india_html)

    def test_renders_indian_reported_results_in_us_panel_design(self) -> None:
        section = sample_section(sample_indian_history())
        section.update({
            "ticker": "IN:TCS",
            "display_symbol": "TCS",
            "market": "IN",
            "exchange": "NSE",
            "upcoming_earnings": None,
        })

        html = build_web_section(section)

        self.assertIn('<details class="earnings-history">', html)
        self.assertNotIn('<details class="earnings-history" open', html)
        self.assertIn("Last 4 reported quarters", html)
        self.assertIn("Latest EPS ₹34.37", html)
        self.assertIn("Reported EPS trend", html)
        self.assertIn("Sales (₹ cr)", html)
        self.assertIn("Net profit (₹ cr)", html)
        self.assertIn("EPS (₹)", html)
        self.assertIn("OPM", html)
        self.assertIn("61,237", html)
        self.assertIn("12,502", html)
        self.assertIn("28.0%", html)
        self.assertNotIn("EPS surprise vs consensus", html)
        self.assertNotIn("Estimate", html)
        self.assertLess(html.index("Q2 FY26"), html.index("Q1 FY27"))


class FakeHandler:
    def __init__(self) -> None:
        self.path = "/api/digest-data?t=token&ticker=US%3AAAPL"
        self.headers = {}
        self.wfile = io.BytesIO()
        self.status = None
        self.response_headers: dict[str, str] = {}

    def send_response(self, status: int) -> None:
        self.status = status

    def send_header(self, name: str, value: str) -> None:
        self.response_headers[name] = value

    def end_headers(self) -> None:
        pass


class EarningsHandlerTest(unittest.TestCase):
    @patch("api.digest.build_web_section", return_value="<section>Earnings</section>")
    @patch("api.digest.collect_digest_data")
    @patch("api.digest._missing_data_keys", return_value=[])
    @patch("api.digest._verify_token", return_value=("token", ["US:AAPL"]))
    def test_digest_data_enables_web_earnings(
        self,
        _verify: Mock,
        _missing: Mock,
        collect: Mock,
        _render: Mock,
    ) -> None:
        section = sample_section(sample_history())
        collect.return_value = ([section], 1)
        handler = FakeHandler()

        handle_data_get(handler)

        self.assertEqual(handler.status, 200)
        collect.assert_called_once_with(
            ["US:AAPL"],
            finnhub_key=unittest.mock.ANY,
            indianapi_key=unittest.mock.ANY,
            include_earnings=True,
            include_price_ranges=True,
            include_indian_media=True,
        )
        payload = json.loads(handler.wfile.getvalue())
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["section"]["earnings_history"]["summary_label"], "3 beats · 1 miss")
        self.assertEqual(payload["html"], "<section>Earnings</section>")


if __name__ == "__main__":
    unittest.main()
