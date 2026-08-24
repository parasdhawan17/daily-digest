import json
import unittest
from unittest.mock import patch

import requests

from stock_news.ai_summary import filter_ai_summary, generate_ai_summary
from stock_news.render import build_email_digest, build_web_digest


def sample_sections() -> list[dict]:
    return [
        {
            "ticker": "US:AAPL",
            "display_symbol": "AAPL",
            "market": "US",
            "exchange": "NASDAQ",
            "quote": {"price": 200.0, "change_pct": 1.2},
            "logo": None,
            "error": None,
            "stories": [
                {
                    "headline": "Apple expands services offering",
                    "summary": "The company announced a new services initiative.",
                    "source": "Example News",
                    "published_at": "1h ago",
                    "relative_time": "",
                    "url": "https://example.com/apple",
                    "image": None,
                }
            ],
            "web_stories": [],
        },
        {
            "ticker": "US:MSFT",
            "display_symbol": "MSFT",
            "market": "US",
            "exchange": "NASDAQ",
            "quote": {"price": 400.0, "change_pct": -0.5},
            "logo": None,
            "error": None,
            "stories": [
                {
                    "headline": "Microsoft reports cloud demand",
                    "summary": "Cloud demand remains a focus for investors.",
                    "source": "Example News",
                    "published_at": "2h ago",
                    "relative_time": "",
                    "url": "https://example.com/microsoft",
                    "image": None,
                }
            ],
            "web_stories": [],
        },
    ]


class FakeResponse:
    def __init__(self, body: dict) -> None:
        self.body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.body


class AiSummaryTest(unittest.TestCase):
    @patch("stock_news.ai_summary.requests.post")
    @patch("stock_news.ai_summary.OPENROUTER_API_KEY", "test-key")
    def test_one_batch_request_returns_shared_summary(self, post) -> None:
        post.return_value = FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "headline": "Cloud and services demand shape today’s market",
                                    "market_context": "Technology news focused on cloud and services demand.",
                                    "ticker_summaries": {
                                        "US:AAPL": "Apple is expanding its services business.",
                                        "US:MSFT": "Cloud demand remains a key Microsoft theme.",
                                        "US:UNREQUESTED": "Should be ignored.",
                                    },
                                }
                            )
                        }
                    }
                ]
            }
        )

        result = generate_ai_summary(sample_sections())

        self.assertEqual(
            result,
            {
                "headline": "Cloud and services demand shape today’s market",
                "market_context": "Technology news focused on cloud and services demand.",
                "ticker_summaries": {
                    "US:AAPL": "Apple is expanding its services business.",
                    "US:MSFT": "Cloud demand remains a key Microsoft theme.",
                },
            },
        )
        post.assert_called_once()
        request = post.call_args.kwargs["json"]
        self.assertEqual(request["max_tokens"], 700)
        self.assertEqual(request["temperature"], 0.1)
        prompt = request["messages"][1]["content"]
        self.assertIn("between 35 and 55 words", prompt)
        self.assertIn("Write for a general reader using clear, natural English", prompt)
        self.assertIn("Style example (illustrative only", prompt)
        self.assertIn("Do not connect news to a stock-price move", prompt)

    @patch("stock_news.ai_summary.requests.post", side_effect=requests.Timeout)
    @patch("stock_news.ai_summary.OPENROUTER_API_KEY", "test-key")
    def test_api_failure_returns_none(self, post) -> None:
        self.assertIsNone(generate_ai_summary(sample_sections()))

    def test_filter_keeps_only_subscriber_tickers(self) -> None:
        summary = {
            "headline": "A concise market headline",
            "market_context": "Shared context.",
            "ticker_summaries": {
                "US:AAPL": "Apple summary.",
                "US:MSFT": "Microsoft summary.",
            },
        }
        self.assertEqual(
            filter_ai_summary(summary, ["US:AAPL"]),
            {
                "headline": "A concise market headline",
                "market_context": "Shared context.",
                "ticker_summaries": {"US:AAPL": "Apple summary."},
            },
        )

    def test_render_includes_ai_summary_in_html_and_plain_text(self) -> None:
        html, text, subject = build_email_digest(
            sample_sections(),
            ["US:AAPL", "US:MSFT"],
            2,
            "post_close",
            digest_url="https://example.com/digest",
            ai_summary={
                "headline": "Cloud and services demand shape today’s market",
                "market_context": "Shared context.",
                "ticker_summaries": {"US:AAPL": "Apple summary."},
            },
        )
        self.assertIn("AI briefing", html)
        self.assertIn("background-image: none !important", html)
        self.assertIn("background-color: #312e81 !important", html)
        self.assertIn('class="email-card mobile-section" bgcolor="#ffffff"', html)
        self.assertIn('class="ai-briefing-panel"', html)
        self.assertIn('bgcolor="#f5f3ff"', html)
        self.assertNotIn("linear-gradient(135deg,#eef2ff", html)
        self.assertIn("View full digest", html)
        self.assertNotIn("AAPL moved high</h1>", html)
        self.assertIn("Apple summary.", html)
        self.assertIn("=== AI BRIEFING ===", text)
        self.assertIn("AAPL: Apple summary.", text)
        self.assertEqual(subject, "Cloud and services demand shape today’s market")

    def test_web_render_includes_session_and_ticker_ai_briefs(self) -> None:
        sections = sample_sections()
        for section in sections:
            section["web_stories"] = section["stories"]
        html = build_web_digest(
            sections,
            ["US:AAPL", "US:MSFT"],
            ai_summary={
                "market_context": "Shared context.",
                "ticker_summaries": {
                    "US:AAPL": "Apple summary.",
                    "US:MSFT": "Microsoft summary.",
                },
            },
        )
        self.assertIn('aria-label="AI briefing"', html)
        self.assertIn("Shared context.", html)
        self.assertEqual(html.count("✦ AI brief"), 2)
        self.assertIn("Apple summary.", html)
        self.assertIn("Microsoft summary.", html)


if __name__ == "__main__":
    unittest.main()
