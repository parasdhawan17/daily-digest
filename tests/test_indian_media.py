import base64
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

import requests

from stock_news.digest import collect_digest_data
from stock_news.indianapi import fetch_company_logo, fetch_news
from stock_news.render import build_web_section


class IndianMediaProviderTest(unittest.TestCase):
    @patch("stock_news.indianapi.requests.get")
    def test_builds_safe_data_url_from_company_logo(self, get: Mock) -> None:
        encoded = base64.b64encode(b"example-png-bytes").decode("ascii")
        response = Mock()
        response.json.return_value = {
            "content_type": "image/png",
            "base64_image": encoded,
        }
        get.return_value = response

        result = fetch_company_logo("TCS", "key")

        self.assertEqual(result, f"data:image/png;base64,{encoded}")
        get.assert_called_once_with(
            "https://stock.indianapi.in/logo",
            params={"stock_name": "TCS"},
            headers={"Accept": "application/json", "x-api-key": "key"},
            timeout=30,
        )

    @patch("stock_news.indianapi.requests.get")
    def test_rejects_unsafe_or_invalid_logo_payload(self, get: Mock) -> None:
        response = Mock()
        get.return_value = response

        response.json.return_value = {
            "content_type": "image/svg+xml",
            "base64_image": base64.b64encode(b"<svg></svg>").decode("ascii"),
        }
        self.assertIsNone(fetch_company_logo("TCS", "key"))

        response.json.return_value = {
            "content_type": "image/png",
            "base64_image": "not-valid-base64!",
        }
        self.assertIsNone(fetch_company_logo("TCS", "key"))

    @patch("stock_news.indianapi.requests.get")
    def test_preserves_documented_news_image_and_timestamp_fields(self, get: Mock) -> None:
        published = datetime.now(timezone.utc).replace(microsecond=0)
        response = Mock()
        response.json.return_value = {
            "recentNews": [
                {
                    "title": "TCS expands AI partnership",
                    "summary": "The company announced a new partnership.",
                    "url": "https://example.com/tcs-ai",
                    "image_url": "https://example.com/tcs-ai.jpg",
                    "pub_date": published.isoformat(),
                    "source": "Financial News",
                }
            ]
        }
        get.return_value = response

        result = fetch_news("TCS", "key")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["image"], "https://example.com/tcs-ai.jpg")
        self.assertEqual(result[0]["datetime"], int(published.timestamp()))
        get.assert_called_once_with(
            "https://stock.indianapi.in/company_news",
            params={"stock_name": "TCS"},
            headers={"Accept": "application/json", "x-api-key": "key"},
            timeout=30,
        )

    @patch("stock_news.indianapi.requests.get")
    def test_falls_back_to_stock_news_when_richer_endpoint_is_unavailable(self, get: Mock) -> None:
        unavailable = Mock()
        unavailable.raise_for_status.side_effect = requests.RequestException("not available")
        fallback = Mock()
        fallback.json.return_value = {
            "recentNews": [{
                "headline": "TCS reports quarterly results",
                "url": "https://example.com/tcs-results",
                "imageUrl": "https://example.com/tcs-results.jpg",
            }]
        }
        get.side_effect = [unavailable, fallback]

        result = fetch_news("TCS", "key")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["image"], "https://example.com/tcs-results.jpg")
        self.assertEqual(get.call_count, 2)


class IndianMediaCollectionTest(unittest.TestCase):
    def test_fetches_indian_logo_only_for_web_media_requests(self) -> None:
        logo = "data:image/png;base64,ZXhhbXBsZQ=="
        with (
            patch("stock_news.digest.fetch_quote", return_value=None),
            patch("stock_news.digest.fetch_news", return_value=[]),
            patch("stock_news.digest.fetch_company_logo", return_value=logo) as fetch_logo,
        ):
            email_sections, _ = collect_digest_data(
                ["IN:TCS"],
                finnhub_key="finnhub-key",
                indianapi_key="india-key",
            )
            web_sections, _ = collect_digest_data(
                ["IN:TCS"],
                finnhub_key="finnhub-key",
                indianapi_key="india-key",
                include_indian_media=True,
            )

        fetch_logo.assert_called_once_with(
            "IN:TCS",
            finnhub_key="finnhub-key",
            indianapi_key="india-key",
        )
        self.assertIsNone(email_sections[0]["logo"])
        self.assertEqual(web_sections[0]["logo"], logo)


class IndianMediaRenderTest(unittest.TestCase):
    def test_existing_web_design_renders_indian_logo_and_news_thumbnail(self) -> None:
        logo = "data:image/png;base64,ZXhhbXBsZQ=="
        section = {
            "ticker": "IN:TCS",
            "display_symbol": "TCS",
            "market": "IN",
            "exchange": "NSE",
            "quote": {"price": 3120.0, "change_pct": 0.8},
            "logo": logo,
            "earnings_history": None,
            "upcoming_earnings": None,
            "price_ranges": None,
            "stories": [],
            "web_stories": [{
                "headline": "TCS expands AI partnership",
                "summary": "The company announced a new partnership.",
                "url": "https://example.com/tcs-ai",
                "image": "https://example.com/tcs-ai.jpg",
                "source": "Financial News",
                "relative_time": "1h ago",
                "published_at": "",
            }],
            "error": None,
        }

        html = build_web_section(section)

        self.assertIn(f'<img class="ticker-logo" src="{logo}"', html)
        self.assertIn('class="story-thumb" src="https://example.com/tcs-ai.jpg"', html)
        self.assertIn("has-thumb", html)


if __name__ == "__main__":
    unittest.main()
