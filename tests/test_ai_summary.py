import json
import re
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


def completion(content: dict) -> FakeResponse:
    return FakeResponse(
        {"choices": [{"message": {"content": json.dumps(content)}}]}
    )


def many_sections(count: int, stories_per_ticker: int = 3) -> list[dict]:
    sections: list[dict] = []
    for index in range(count):
        ticker = f"US:T{index:03d}"
        stories = [
            {
                "headline": f"Headline {index}-{story_index}",
                "summary": f"Summary {index}-{story_index}",
                "source": "Example News",
                "published_at": "1h ago",
            }
            for story_index in range(stories_per_ticker)
        ]
        sections.append({"ticker": ticker, "stories": stories})
    return sections


class AiSummaryTest(unittest.TestCase):
    @patch("stock_news.ai_summary.requests.post")
    @patch("stock_news.ai_summary.OPENROUTER_API_KEY", "test-key")
    def test_ticker_batch_and_market_request_return_shared_summary(self, post) -> None:
        post.side_effect = [
            completion(
                {
                    "batch_theme": "Technology news focused on cloud and services demand.",
                    "ticker_summaries": {
                        "US:AAPL": "Apple is expanding its services business.",
                        "US:MSFT": "Cloud demand remains a key Microsoft theme.",
                    },
                }
            ),
            completion(
                {
                    "headline": "Cloud and services demand shape today’s market",
                    "market_context": "Technology news focused on cloud and services demand.",
                }
            ),
        ]

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
        self.assertEqual(post.call_count, 2)
        ticker_request = post.call_args_list[0].kwargs["json"]
        self.assertEqual(ticker_request["max_tokens"], 1800)
        self.assertEqual(ticker_request["temperature"], 0.1)
        self.assertEqual(ticker_request["provider"], {"require_parameters": True})
        ticker_schema = ticker_request["response_format"]["json_schema"]
        self.assertTrue(ticker_schema["strict"])
        self.assertEqual(
            ticker_schema["schema"]["properties"]["ticker_summaries"]["required"],
            ["US:AAPL", "US:MSFT"],
        )
        prompt = ticker_request["messages"][1]["content"]
        self.assertIn("between 35 and 55 words", prompt)
        self.assertIn("Write for a general reader using clear, natural English", prompt)
        self.assertIn("Style example (illustrative only", prompt)
        self.assertIn("Do not connect news to a stock-price move", prompt)

        market_request = post.call_args_list[1].kwargs["json"]
        self.assertEqual(market_request["max_tokens"], 400)
        self.assertEqual(
            market_request["response_format"]["json_schema"]["name"],
            "market_news_briefing",
        )

    @patch("stock_news.ai_summary.requests.post", side_effect=requests.Timeout)
    @patch("stock_news.ai_summary.OPENROUTER_API_KEY", "test-key")
    @patch("stock_news.ai_summary.AI_SUMMARY_RETRIES", 0)
    def test_api_failure_returns_none(self, post) -> None:
        self.assertIsNone(generate_ai_summary(sample_sections()))

    @patch("stock_news.ai_summary.requests.post")
    @patch("stock_news.ai_summary.OPENROUTER_API_KEY", "test-key")
    @patch("stock_news.ai_summary.AI_SUMMARY_RETRIES", 0)
    def test_batch_with_missing_or_extra_ticker_keys_is_rejected(self, post) -> None:
        post.return_value = completion(
            {
                "batch_theme": "Technology demand remained in focus.",
                "ticker_summaries": {
                    "US:AAPL": "Apple summary.",
                    "US:UNREQUESTED": "Unrequested summary.",
                },
            }
        )

        self.assertIsNone(generate_ai_summary(sample_sections()))
        post.assert_called_once()

    @patch("stock_news.ai_summary.time.sleep")
    @patch("stock_news.ai_summary.requests.post")
    @patch("stock_news.ai_summary.OPENROUTER_API_KEY", "test-key")
    @patch("stock_news.ai_summary.AI_SUMMARY_RETRIES", 1)
    def test_transient_failure_retries_only_the_failed_request(self, post, sleep) -> None:
        post.side_effect = [
            requests.Timeout(),
            completion(
                {
                    "batch_theme": "Technology demand remained in focus.",
                    "ticker_summaries": {
                        "US:AAPL": "Apple summary.",
                        "US:MSFT": "Microsoft summary.",
                    },
                }
            ),
            completion(
                {
                    "headline": "Technology demand remains in focus",
                    "market_context": "Technology demand remained in focus.",
                }
            ),
        ]

        result = generate_ai_summary(sample_sections())

        self.assertIsNotNone(result)
        self.assertEqual(post.call_count, 3)
        sleep.assert_called_once()

    @patch("stock_news.ai_summary._generate_market_briefing")
    @patch("stock_news.ai_summary._generate_ticker_batch")
    @patch("stock_news.ai_summary.OPENROUTER_API_KEY", "test-key")
    def test_25_tickers_are_split_into_bounded_batches(
        self,
        ticker_batch,
        market_briefing,
    ) -> None:
        observed_batches: list[list[dict]] = []

        def summarize(batch: list[dict]) -> dict:
            observed_batches.append(batch)
            return {
                "batch_theme": f"Theme for {len(batch)} tickers.",
                "ticker_summaries": {
                    item["ticker"]: f"Summary for {item['ticker']}." for item in batch
                },
            }

        ticker_batch.side_effect = summarize
        market_briefing.return_value = {
            "headline": "A broad market headline",
            "market_context": "A broad market context.",
        }

        result = generate_ai_summary(many_sections(25))

        self.assertEqual(sorted(len(batch) for batch in observed_batches), [1, 12, 12])
        self.assertTrue(
            all(len(item["stories"]) == 2 for batch in observed_batches for item in batch)
        )
        self.assertEqual(len(result["ticker_summaries"]), 25)
        self.assertEqual(len(market_briefing.call_args.args[0]), 3)

    @patch("stock_news.ai_summary._generate_market_briefing")
    @patch("stock_news.ai_summary._generate_ticker_batch")
    @patch("stock_news.ai_summary.OPENROUTER_API_KEY", "test-key")
    def test_400_tickers_create_34_bounded_batches(
        self,
        ticker_batch,
        market_briefing,
    ) -> None:
        observed_sizes: list[int] = []

        def summarize(batch: list[dict]) -> dict:
            observed_sizes.append(len(batch))
            return {
                "batch_theme": "A batch theme.",
                "ticker_summaries": {
                    item["ticker"]: f"Summary for {item['ticker']}." for item in batch
                },
            }

        ticker_batch.side_effect = summarize
        market_briefing.return_value = {
            "headline": "A broad market headline",
            "market_context": "A broad market context.",
        }

        result = generate_ai_summary(many_sections(400))

        self.assertEqual(len(observed_sizes), 34)
        self.assertEqual(sum(observed_sizes), 400)
        self.assertLessEqual(max(observed_sizes), 12)
        self.assertEqual(len(result["ticker_summaries"]), 400)
        self.assertEqual(len(market_briefing.call_args.args[0]), 34)

    @patch("stock_news.ai_summary._generate_market_briefing")
    @patch("stock_news.ai_summary._generate_ticker_batch")
    @patch("stock_news.ai_summary.OPENROUTER_API_KEY", "test-key")
    def test_failed_batch_does_not_discard_successful_ticker_summaries(
        self,
        ticker_batch,
        market_briefing,
    ) -> None:
        def summarize(batch: list[dict]) -> dict | None:
            if batch[0]["ticker"] == "US:T012":
                return None
            return {
                "batch_theme": "A successful batch theme.",
                "ticker_summaries": {
                    item["ticker"]: f"Summary for {item['ticker']}." for item in batch
                },
            }

        ticker_batch.side_effect = summarize
        market_briefing.return_value = {
            "headline": "A broad market headline",
            "market_context": "A broad market context.",
        }

        result = generate_ai_summary(many_sections(13))

        self.assertEqual(len(result["ticker_summaries"]), 12)
        self.assertNotIn("US:T012", result["ticker_summaries"])

    @patch("stock_news.ai_summary.requests.post")
    @patch("stock_news.ai_summary.OPENROUTER_API_KEY", "test-key")
    @patch("stock_news.ai_summary.AI_SUMMARY_RETRIES", 0)
    def test_market_failure_uses_batch_theme_as_context(self, post) -> None:
        post.side_effect = [
            completion(
                {
                    "batch_theme": "Technology demand remained in focus.",
                    "ticker_summaries": {
                        "US:AAPL": "Apple summary.",
                        "US:MSFT": "Microsoft summary.",
                    },
                }
            ),
            requests.Timeout(),
        ]

        result = generate_ai_summary(sample_sections())

        self.assertEqual(result["headline"], "")
        self.assertEqual(result["market_context"], "Technology demand remained in focus.")

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
        self.assertIn('class="ai-panel"', html)
        self.assertIn('bgcolor="#eaf2ee"', html)
        self.assertIn("Open my full digest", html)
        self.assertIn("Your closing briefing", html)
        self.assertLess(html.index("Shared context."), html.index("Apple expands services offering"))
        self.assertNotIn("$200.00", html)
        self.assertNotIn("$200.00", text)
        self.assertIn("Apple summary.", html)
        self.assertIn("=== AI BRIEFING ===", text)
        self.assertIn("AI brief: Apple summary.", text)
        self.assertEqual(subject, "US Post-Market • Cloud and services demand shape today’s market")

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
        self.assertEqual(html.count("<strong>AI brief</strong>"), 2)
        self.assertIn("Apple summary.", html)
        self.assertIn("Microsoft summary.", html)

    def test_web_ai_briefs_use_compact_text_sizes(self) -> None:
        html = build_web_digest([], [])

        self.assertRegex(
            html,
            re.compile(r"\.ai-briefing-context\s*\{.*?font-size:\s*11px;", re.DOTALL),
        )
        self.assertRegex(
            html,
            re.compile(r"\.ticker-ai-brief\s*\{.*?font-size:\s*12px;", re.DOTALL),
        )

    def test_web_fetched_at_is_localized_in_the_browser(self) -> None:
        html = build_web_digest(
            [],
            [],
            fetched_at_label="Fetched on 3:00 AM UTC",
            fetched_at_iso="2026-08-28T03:00:00+00:00",
        )

        self.assertIn('id="fetched-at"', html)
        self.assertIn('data-fetched-at="2026-08-28T03:00:00+00:00"', html)
        self.assertIn("new Intl.DateTimeFormat", html)
        self.assertIn("hour12: true", html)
        self.assertIn('timeZoneName: "short"', html)

    def test_web_places_ticker_edit_control_with_subscribed_tickers(self) -> None:
        html = build_web_digest(
            sample_sections(),
            ["US:AAPL", "US:MSFT"],
            subscribe_enabled_override=True,
        )

        self.assertIn('<p class="movers-label">Your watchlist</p>', html)
        self.assertIn('class="movers-edit-btn"', html)
        self.assertIn('aria-label="Edit subscribed tickers"', html)
        self.assertNotIn('class="header-subscribe-btn"', html)

    def test_web_defaults_to_dark_theme_without_overriding_saved_choice(self) -> None:
        html = build_web_digest([], [])

        self.assertIn('<html lang="en" data-theme="dark">', html)
        self.assertIn('<meta name="color-scheme" content="dark light">', html)
        self.assertIn('var stored = localStorage.getItem("daily-digest-theme")', html)
        self.assertNotIn('prefers-color-scheme: dark', html)


if __name__ == "__main__":
    unittest.main()
